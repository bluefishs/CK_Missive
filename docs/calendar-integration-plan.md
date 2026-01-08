# 行事曆功能整合規劃建議

## 一、現有功能架構

### 1.1 已實作功能

| 功能 | 狀態 | 說明 |
|------|------|------|
| 本地事件管理 | ✅ | CRUD 操作、多視圖模式（月曆/列表/時間軸） |
| Google Calendar 同步 | ✅ | 單向同步（Local → Google），支援 Service Account |
| 自動同步排程器 | ✅ | 每10分鐘自動同步待處理事件 |
| 衝突偵測 | ✅ | 時間重疊事件檢測 API |
| 提醒通知整合 | ✅ | 本地提醒轉換為 Google Calendar popup 通知 |
| 優先級顏色對應 | ✅ | 高/中/低優先級對應 Google Calendar 顏色 |

### 1.2 資料模型

```
DocumentCalendarEvent
├── id, title, description
├── start_date, end_date, all_day
├── event_type (deadline/meeting/review/reminder/reference)
├── priority (1-5, 1=緊急)
├── status (pending/completed/cancelled)
├── document_id (關聯公文)
├── assigned_user_id
├── google_event_id, google_sync_status
└── reminders[] (EventReminder 關聯)
```

---

## 二、公文截止提醒機制 (Event with Document)

### 2.1 建議流程

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  公文管理頁面    │ ─→ │  新增行事曆事件   │ ─→ │ Google Calendar │
│  /documents/690 │    │  (截止提醒類型)   │    │   自動同步      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 2.2 實作方案

#### 方案 A：公文頁面直接新增按鈕 (推薦)

在公文詳情頁新增「加入行事曆」按鈕：

```tsx
// DocumentDetail.tsx
<Button
  icon={<CalendarOutlined />}
  onClick={() => createCalendarEvent({
    title: `公文提醒: ${doc.subject.substring(0, 50)}...`,
    description: `公文字號: ${doc.doc_number}\n主旨: ${doc.subject}`,
    event_type: 'deadline',
    document_id: doc.id,
    start_date: doc.deadline || dayjs().add(7, 'day'), // 預設7天後
    priority: doc.urgency_level || 3
  })}
>
  加入行事曆
</Button>
```

#### 方案 B：公文新增/編輯時自動建立

在公文表單中新增「設定截止提醒」選項：

```tsx
// DocumentForm.tsx
<Form.Item label="截止提醒">
  <Space>
    <Switch
      checkedChildren="啟用"
      unCheckedChildren="關閉"
      onChange={setReminderEnabled}
    />
    {reminderEnabled && (
      <DatePicker
        placeholder="選擇截止日期"
        onChange={setDeadline}
      />
    )}
  </Space>
</Form.Item>
```

### 2.3 後端 API 建議

```python
# POST /api/documents/{id}/create-reminder
@router.post("/documents/{document_id}/create-reminder")
async def create_document_reminder(
    document_id: int,
    deadline: datetime,
    reminder_days: List[int] = [7, 3, 1],  # 提前幾天提醒
    db: AsyncSession = Depends(get_async_db)
):
    """
    從公文建立行事曆提醒
    - deadline: 截止日期
    - reminder_days: 提前提醒天數列表
    """
    document = await get_document(db, document_id)

    event = DocumentCalendarEvent(
        title=f"公文提醒: {document.subject[:50]}...",
        description=f"公文字號: {document.doc_number}",
        start_date=deadline,
        end_date=deadline,
        event_type='deadline',
        document_id=document_id,
        priority=2,  # 重要
    )

    # 建立提醒
    for days in reminder_days:
        reminder = EventReminder(
            reminder_time=deadline - timedelta(days=days),
            notification_type='system'
        )
        event.reminders.append(reminder)

    db.add(event)
    await db.commit()

    # 觸發 Google Calendar 同步
    await calendar_service.sync_event_to_google(db, event)

    return {"success": True, "event_id": event.id}
```

---

## 三、功能優化建議

### 3.1 短期優化 (1-2 週)

| 項目 | 優先級 | 說明 |
|------|--------|------|
| 公文頁面「加入行事曆」按鈕 | 高 | 一鍵建立截止提醒 |
| 批量同步狀態顯示 | 中 | 顯示待同步/已同步數量 |
| 雙向同步支援 | 中 | Google → Local 同步 |
| 週/日視圖模式 | 低 | 更精細的時間顯示 |

### 3.2 中期優化 (1-2 月)

| 項目 | 說明 |
|------|------|
| 拖曳調整事件 | 在月曆上拖曳改變日期 |
| 重複事件 | 支援週期性事件（每週/每月） |
| 多日曆支援 | 依案件/部門分類的子日曆 |
| 事件範本 | 常用事件類型快速新增 |

### 3.3 長期規劃

| 項目 | 說明 |
|------|------|
| 團隊行事曆 | 查看團隊成員行程 |
| 會議室預約 | 整合資源預約功能 |
| 外部日曆訂閱 | 支援 iCal 訂閱 |
| AI 智慧排程 | 自動建議最佳會議時間 |

---

## 四、使用者操作流程

### 4.1 從公文建立提醒

```
1. 進入公文詳情頁 (/documents/690)
2. 點擊「加入行事曆」按鈕
3. 設定截止日期和提醒時間
4. 確認後自動建立事件
5. 系統自動同步至 Google Calendar
```

### 4.2 行事曆查看關聯公文

```
1. 進入行事曆頁面 (/calendar)
2. 點擊事件檢視詳情
3. 如有關聯公文，顯示「查看關聯公文」連結
4. 點擊跳轉至公文詳情頁
```

### 4.3 批次操作

```
1. 進入列表視圖
2. 勾選多個事件
3. 點擊「批次刪除」或「批次同步」
4. 確認操作
5. 頁面自動刷新顯示最新資料
```

---

## 五、API 端點清單

### 5.1 事件管理

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/calendar/events` | 建立事件 |
| PUT | `/api/calendar/events/{id}` | 更新事件 |
| POST | `/api/calendar/events/delete` | 刪除事件 |
| POST | `/api/calendar/events/list` | 查詢事件列表 |

### 5.2 Google Calendar 同步

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/calendar/events/sync` | 單一事件同步 |
| POST | `/api/calendar/events/bulk-sync` | 批次同步 |
| GET | `/api/calendar/google-events` | 取得 Google 事件 |

### 5.3 排程器控制

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/calendar/sync-scheduler/status` | 排程器狀態 |
| POST | `/api/calendar/sync-scheduler/trigger` | 手動觸發同步 |
| POST | `/api/calendar/sync-scheduler/set-interval` | 設定同步間隔 |

### 5.4 衝突偵測

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/calendar/events/check-conflicts` | 檢查時間衝突 |

---

## 六、技術實作注意事項

### 6.1 Google Calendar 同步

- 使用 Service Account 認證（無需使用者授權）
- 同步間隔建議 5-10 分鐘
- 失敗事件自動重試（最多 3 次）
- 支援優先級顏色對應：
  - 緊急(1) → 紅色 (colorId: 11)
  - 重要(2) → 橙色 (colorId: 6)
  - 普通(3) → 藍色 (colorId: 1)
  - 低(4) → 綠色 (colorId: 10)

### 6.2 提醒通知

- 本地提醒：系統內通知中心
- Google 提醒：popup 彈窗通知
- 預設提醒時間：1天、2小時、30分鐘前
- 提醒最長可設定 4 週前 (40320 分鐘)

### 6.3 效能優化

- React Query 快取策略：5 分鐘 stale time
- 事件列表分頁載入
- 只同步狀態為 `pending` 的事件
- 避免重複同步已同步事件

---

## 七、已修復問題 (2026-01-08)

1. **批次刪除後頁面不更新** - 新增 `onRefresh` callback 觸發重新載入
2. **時間軸排序** - 改為降冪排序（最新事件在上）
3. **關聯公文導航** - 修正路徑為 `/documents/{id}` 格式
4. **Antd 靜態方法警告** - 使用 `App.useApp()` hook 取得 context aware 方法

---

*文件更新日期: 2026-01-08*
