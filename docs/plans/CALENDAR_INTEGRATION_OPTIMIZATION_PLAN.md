# 行事曆整合優化規劃

## 目標

優化公文系統與行事曆的整合體驗，減少重複操作，強化通知機制。

---

## 步驟 1: 公文記錄整合事件+提醒 UI

### 現狀問題
- 目前在公文記錄新增行事曆事件後，需要到行事曆頁面才能設定提醒
- 造成使用者重複操作，流程不順暢

### 優化方案

#### 1.1 整合式事件建立模態框

修改 `DocumentCalendarEventModal` 或建立新元件 `IntegratedEventModal`：

```
公文 → 新增事件 → 整合模態框
┌──────────────────────────────────────┐
│  新增行事曆事件                       │
├──────────────────────────────────────┤
│  [基本資訊]                          │
│  ├─ 事件標題: ___________________   │
│  ├─ 開始時間: [日期選擇器]          │
│  ├─ 結束時間: [日期選擇器]          │
│  ├─ 事件類型: [截止/會議/審核/提醒] │
│  ├─ 優先級:   [緊急/重要/普通/低]   │
│  └─ 地點:     ___________________   │
├──────────────────────────────────────┤
│  [提醒設定] ✓ 啟用提醒              │
│  ├─ ➕ 新增提醒                      │
│  │   ├─ 時間: [1小時前 ▼]          │
│  │   └─ 類型: [系統通知 ▼]          │
│  └─ 現有提醒:                       │
│      ├─ 🔔 30分鐘前 (系統) [刪除]  │
│      └─ 📧 1天前 (郵件) [刪除]      │
├──────────────────────────────────────┤
│  [同步設定]                          │
│  └─ ✓ 同步至 Google Calendar        │
├──────────────────────────────────────┤
│        [取消]          [儲存]        │
└──────────────────────────────────────┘
```

#### 1.2 實作重點

**前端修改:**
- `frontend/src/components/document/DocumentCalendarIntegration.tsx` - 整合提醒設定
- 複用 `ReminderSettingsModal` 的邏輯，但整合到事件建立流程中

**後端修改:**
- `backend/app/api/endpoints/document_calendar.py` - 事件建立 API 支援同時建立提醒
- 擴展 `DocumentCalendarEventCreate` schema：

```python
class DocumentCalendarEventCreate(BaseModel):
    title: str
    start_date: datetime
    # ... 現有欄位

    # 新增: 提醒設定
    reminders: Optional[List[ReminderConfig]] = None
    sync_to_google: bool = False

class ReminderConfig(BaseModel):
    minutes_before: int
    notification_type: str  # 'email' | 'system'
```

---

## 步驟 2: 強化事件通知機制

### 2.1 專案同仁通知

**目標:** 當事件建立時，自動通知相關專案成員

**實作:**

```python
# backend/app/services/event_notification_service.py

class EventNotificationService:
    async def notify_project_members(
        self,
        event: DocumentCalendarEvent,
        project_id: int
    ):
        """通知專案所有相關成員"""
        # 1. 取得專案成員列表
        members = await self.get_project_members(project_id)

        # 2. 建立通知紀錄
        for member in members:
            await self.create_notification(
                user_id=member.id,
                title=f"新事件: {event.title}",
                content=f"專案有新的行事曆事件",
                event_id=event.id
            )

        # 3. 發送即時通知 (WebSocket/SSE)
        await self.push_realtime_notification(members, event)
```

### 2.2 Google Calendar 雙向同步

**目標:**
- 本地事件 → Google Calendar (已實作)
- Google Calendar 提醒 → 本地系統整合

**優化項目:**

1. **自動同步設定**
   - 在事件建立時提供「同步至 Google」選項
   - 系統級設定：預設是否自動同步

2. **同步狀態顯示**
   - 在事件卡片顯示同步狀態圖示
   - 失敗時提供重試按鈕

3. **Google 提醒整合**
   ```python
   # 同步時將本地提醒設定傳給 Google
   google_event = {
       "summary": event.title,
       "start": {...},
       "reminders": {
           "useDefault": False,
           "overrides": [
               {"method": "email", "minutes": 60},
               {"method": "popup", "minutes": 30}
           ]
       }
   }
   ```

---

## 步驟 3: 權限管控機制 (未來)

### 3.1 事件可見性控制

**目標:** 用戶 A 只能在行事曆看到與 A 相關的事件

**權限模型:**

```
事件可見性 =
  (event.created_by == current_user) OR
  (event.assigned_user_id == current_user) OR
  (current_user IN event.project.members) OR
  (current_user.is_admin)
```

**後端實作:**

```python
# backend/app/api/endpoints/document_calendar.py

@router.post("/events/list")
async def list_events(
    request: EventListRequest,
    current_user: User = Depends(get_current_user)
):
    # 基礎查詢
    query = select(DocumentCalendarEvent)

    # 權限過濾
    if not current_user.is_admin:
        query = query.where(
            or_(
                DocumentCalendarEvent.created_by == current_user.id,
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.document_id.in_(
                    select(ProjectDocument.document_id).where(
                        ProjectDocument.project_id.in_(
                            select(ProjectMember.project_id).where(
                                ProjectMember.user_id == current_user.id
                            )
                        )
                    )
                )
            )
        )

    # 執行查詢
    ...
```

### 3.2 共享事件機制

**目標:** 允許特定事件共享給指定用戶或群組

**資料模型擴展:**

```sql
CREATE TABLE event_shares (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES document_calendar_events(id),
    shared_with_user_id INTEGER REFERENCES users(id),
    shared_with_group_id INTEGER REFERENCES user_groups(id),
    permission_level VARCHAR(20),  -- 'view', 'edit'
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 現有行事曆管理機制保留

### 保留功能

1. **行事曆頁面** (`/calendar`)
   - 月/週/日/列表檢視
   - 篩選與搜尋
   - 批次操作

2. **事件編輯**
   - 獨立事件編輯模態框
   - 提醒設定管理
   - Google 同步控制

3. **公文日曆事件維護**
   - 從行事曆檢視公文相關事件
   - 快速跳轉到關聯公文

---

## 實施優先順序

| 階段 | 項目 | 預計影響 |
|------|------|----------|
| **Phase 1** | 整合式事件建立 UI | 減少 50% 操作步驟 |
| **Phase 2** | 專案成員通知 | 提升協作效率 |
| **Phase 3** | Google 雙向同步優化 | 提升同步成功率 |
| **Phase 4** | 權限管控 | 資訊安全與隱私 |

---

## 相關檔案

### 前端
- `frontend/src/components/calendar/EventFormModal.tsx`
- `frontend/src/components/calendar/ReminderSettingsModal.tsx`
- `frontend/src/components/document/DocumentCalendarIntegration.tsx`
- `frontend/src/api/calendarApi.ts`

### 後端
- `backend/app/api/endpoints/document_calendar.py`
- `backend/app/api/endpoints/reminder_management.py`
- `backend/app/services/document_calendar_service.py`
- `backend/app/services/reminder_service.py`

### Schema
- `backend/app/schemas/document_calendar.py`
- `backend/app/extended/models.py`

---

## 本次修復摘要

### 已修復問題

1. **編輯事件 API** - `calendarApi.ts` 從 PUT 改為 POST，符合資安規範
2. **Google 同步 API** - `bulk-sync` 端點改用 Request Body 而非 Query 參數
3. **提醒 API 回應** - 統一字段名稱 (`reminder_type`, `is_sent`, `retry_count`)
4. **側欄事件計數** - 確認功能正常 (01/08 無事件故顯示 0)

### 修改檔案

```
frontend/src/api/calendarApi.ts
  - updateEvent: PUT -> POST /calendar/events/update
  - 新增 location, document_id 到更新資料
  - CalendarEvent 介面新增 location 欄位

backend/app/schemas/document_calendar.py
  - 新增 BulkSyncRequest schema

backend/app/api/endpoints/document_calendar.py
  - bulk-sync 端點使用 BulkSyncRequest body

backend/app/api/endpoints/reminder_management.py
  - 回應新增 reminder_type, is_sent, retry_count 欄位
```
