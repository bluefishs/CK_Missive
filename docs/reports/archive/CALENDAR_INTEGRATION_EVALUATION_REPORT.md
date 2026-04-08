# CK_Missive 行事曆整合評估報告

> 評估日期: 2026-01-08
> 狀態: 完整調查報告

---

## 一、問題調查結果摘要

| 問題 | 根因分析 | 修復狀態 | 優先級 |
|------|---------|---------|--------|
| 批次刪除顯示成功但頁面點位仍存在 | 前端 API 未傳送 `confirm: true` | ✅ **已修復** | 高 |
| Google Calendar 同步問題 | `_sync_events_to_google` 未保存 `google_event_id` | ✅ **已修復** | 中 |
| Event with Document 機制說明 | 需文件化 | 📝 **本報告** | 資訊 |

---

## 二、問題詳細分析

### 2.1 批次刪除問題 (已修復)

#### 問題描述
用戶在行事曆頁面選擇多個事件後執行批次刪除，系統顯示「刪除成功」，但頁面重新載入後事件仍然存在。

#### 根因分析
**位置**: `frontend/src/api/calendarApi.ts:220-228`

```typescript
// 修復前 (有問題)
async deleteEvent(eventId: number): Promise<void> {
  await api.post('/calendar/events/delete', { event_id: eventId });
  // 缺少 confirm: true，後端不會執行實際刪除
}
```

**後端邏輯** (`backend/app/api/endpoints/document_calendar.py:319-326`):
```python
if not request.confirm:
    return {
        "success": False,
        "message": "請確認刪除操作",
        "require_confirm": True
    }
```

#### 修復方案

```typescript
// 修復後
async deleteEvent(eventId: number): Promise<void> {
  const response = await api.post('/calendar/events/delete', {
    event_id: eventId,
    confirm: true,  // 關鍵修復
  });

  if (response.data && response.data.success === false) {
    throw new Error(response.data.message || '刪除事件失敗');
  }
}
```

**檔案**: `frontend/src/api/calendarApi.ts` (已修復)

---

### 2.2 Google Calendar 同步問題

#### 問題描述
新增公文事件後，僅少數成功同步至 Google Calendar，大部分事件無法在 Google Calendar 看到。

#### 根因分析

**問題 1: `google_event_id` 未保存**

**位置**: `backend/app/services/document_calendar_integrator.py:137-165`

```python
async def _sync_events_to_google(self, events, document):
    for event in events:
        # 呼叫 create_event_from_document 但沒有保存返回的 google_event_id
        await self.calendar_service.create_event_from_document(
            document=document,
            summary=event.title,
            ...
        )
        # ❌ 缺少: event.google_event_id = result
        # ❌ 缺少: await db.commit()
```

**問題 2: 無法追蹤同步狀態**

由於 `google_event_id` 未保存回本地資料庫，導致：
- 前端無法顯示「已同步」標誌
- 批次同步會重複建立 Google 事件
- 無法判斷哪些事件需要同步

#### 已實施修復

**檔案**: `backend/app/services/document_calendar_integrator.py`

修改內容：
1. `_sync_events_to_google` 方法新增 `db: AsyncSession` 參數
2. 呼叫 Google API 後，將返回的 `google_event_id` 保存到本地事件
3. 更新 `google_sync_status` 欄位 (`synced` 或 `failed`)
4. 執行 `await db.commit()` 提交變更

```python
async def _sync_events_to_google(
    self,
    db: AsyncSession,  # 新增 db 參數
    events: List[DocumentCalendarEvent],
    document: OfficialDocument
):
    for event in events:
        google_event_id = await self.calendar_service.create_event_from_document(...)

        # 關鍵修復：保存 google_event_id 到本地事件
        if google_event_id:
            event.google_event_id = google_event_id
            event.google_sync_status = 'synced'
        else:
            event.google_sync_status = 'failed'

    await db.commit()
```

---

### 2.3 Google Calendar 服務配置狀態

| 項目 | 狀態 | 說明 |
|------|-----|------|
| Service Account 憑證 | ✅ 存在 | `backend/GoogleCalendarAPIKEY.json` |
| Calendar ID 設定 | ✅ 已設定 | `settings.GOOGLE_CALENDAR_ID = "primary"` |
| API 服務初始化 | ✅ 有邏輯 | `DocumentCalendarService._init_google_service()` |

**注意**: Service Account 需要被加入到目標 Google Calendar 才能建立事件。

---

## 三、Event with Document 機制說明

### 3.1 公文事件整合架構

```
                    ┌─────────────────────────────────────┐
                    │          OfficialDocument           │
                    │  (公文資料表)                        │
                    │  - doc_date (發文日期)               │
                    │  - receive_date (收文日期)           │
                    │  - send_date (發文截止日)            │
                    └────────────┬────────────────────────┘
                                 │
                    ┌────────────▼────────────────────────┐
                    │   DocumentCalendarIntegrator        │
                    │   parse_document_dates()            │
                    │   convert_document_to_events()      │
                    └────────────┬────────────────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     │                           │                           │
     ▼                           ▼                           ▼
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│  REFERENCE  │          │  REMINDER   │          │  DEADLINE   │
│  事件       │          │  事件       │          │  事件       │
│ (發文日期)  │          │ (收文日期)  │          │ (發文截止)  │
└──────┬──────┘          └──────┬──────┘          └──────┬──────┘
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                    ┌───────────▼───────────────────────┐
                    │   DocumentCalendarEvent 資料表    │
                    │   - document_id (關聯公文)        │
                    │   - event_type (事件類型)         │
                    │   - reminder_enabled (提醒啟用)   │
                    │   - google_event_id (Google 關聯) │
                    └───────────┬───────────────────────┘
                                │
                    ┌───────────▼───────────────────────┐
                    │   Google Calendar (雙向同步)      │
                    │   - create_google_event()         │
                    │   - update_google_event()         │
                    │   - delete_google_event()         │
                    └───────────────────────────────────┘
```

### 3.2 從公文建立行事曆事件流程

#### 自動觸發流程

當公文匯入或建立時，系統自動解析以下日期欄位：

| 公文欄位 | 產生事件類型 | 事件標題格式 |
|---------|-------------|-------------|
| `doc_date` | `reference` | `[REFERENCE] {主旨}` |
| `receive_date` | `reminder` | `[REMINDER] {主旨}` |
| `send_date` | `deadline` | `[DEADLINE] {主旨}` |

#### 手動新增流程

**目前狀態**: 需透過行事曆頁面「新增事件」功能

1. 進入行事曆頁面 (`/calendar`)
2. 點擊「新增事件」按鈕
3. 在表單中選擇「關聯公文」(若有)
4. 設定事件類型、日期、提醒時間
5. 儲存後自動同步至 Google Calendar (如已配置)

### 3.3 提醒機制

#### 多層級提醒系統

```python
# 預設提醒時間 (在事件開始前)
DEFAULT_REMINDERS = {
    'deadline': [1440, 120, 30],  # 1天、2小時、30分鐘
    'reminder': [1440, 120],       # 1天、2小時
    'meeting': [60, 15],           # 1小時、15分鐘
    'review': [1440],              # 1天
    'reference': []                # 不提醒
}
```

#### 提醒觸發方式

| 管道 | 狀態 | 說明 |
|------|-----|------|
| 系統通知 | ✅ 已實作 | `system_notifications` 表 |
| Email 通知 | ⚠️ 需配置 | 需設定 SMTP 伺服器 |
| Google Calendar 提醒 | ✅ 已整合 | 透過 Google Calendar popup |

---

## 四、建議改進事項

### 4.1 立即修復 (高優先級) - 已完成

| 項目 | 狀態 | 檔案位置 |
|------|-----|---------|
| 批次刪除 confirm 參數 | ✅ 已修復 | `frontend/src/api/calendarApi.ts` |
| Google 同步保存 event_id | ✅ 已修復 | `backend/app/services/document_calendar_integrator.py` |

### 4.2 功能增強 (中優先級)

| 項目 | 說明 |
|------|------|
| 公文詳情頁新增「加入行事曆」按鈕 | 讓用戶可從公文頁面直接建立行事曆事件 |
| 同步狀態視覺化 | 在事件卡片顯示同步成功/失敗/待同步狀態 |
| 批次同步功能優化 | 增加進度條和詳細錯誤訊息 |

### 4.3 長期規劃 (低優先級)

| 項目 | 說明 |
|------|------|
| 雙向同步 | 從 Google Calendar 同步變更回本地 |
| 共用行事曆 | 支援團隊共用行事曆功能 |
| 行動裝置推播 | 整合 Firebase Cloud Messaging |

---

## 五、API 端點參考

### 行事曆事件 API (POST-only 安全機制)

| 端點 | 說明 | 必要參數 |
|------|-----|---------|
| `POST /calendar/events/list` | 列出事件 | `start_date`, `end_date` |
| `POST /calendar/events/create` | 建立事件 | `title`, `start_date` |
| `POST /calendar/events/update` | 更新事件 | `event_id`, 更新欄位 |
| `POST /calendar/events/delete` | 刪除事件 | `event_id`, `confirm: true` ⚠️ |
| `POST /calendar/events/sync` | 單一事件同步 | `event_id` |
| `POST /calendar/events/bulk-sync` | 批次同步 | `sync_all_pending: true` |

### 公文整合 API

| 端點 | 說明 |
|------|------|
| `POST /calendar/documents/{doc_id}/events` | 為公文建立行事曆事件 |
| `GET /calendar/documents/{doc_id}/events` | 取得公文相關事件 |

---

## 六、相關檔案索引

| 檔案 | 說明 |
|------|------|
| `backend/app/services/document_calendar_service.py` | 核心行事曆服務 |
| `backend/app/services/document_calendar_integrator.py` | 公文整合器 |
| `backend/app/api/endpoints/document_calendar.py` | API 端點 |
| `frontend/src/api/calendarApi.ts` | 前端 API 封裝 |
| `frontend/src/hooks/useCalendar.ts` | React Query hooks |
| `frontend/src/pages/CalendarPage.tsx` | 行事曆頁面 |
| `frontend/src/components/calendar/EnhancedCalendarView.tsx` | 行事曆元件 |

---

*評估者: Claude Code Assistant*
*評估日期: 2026-01-08*
