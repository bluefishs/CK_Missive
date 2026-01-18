# 行事曆整合領域知識 (Calendar Integration Domain)

> **觸發關鍵字**: 行事曆, calendar, Google Calendar, 事件, 截止日, event
> **適用範圍**: 行事曆事件管理、Google Calendar 同步、公文到期追蹤
> **版本**: 1.1.0
> **最後更新**: 2026-01-18

---

## 核心架構

### 三層事件來源

1. **公文事件** (DocumentCalendarEvent)
   - 從公文截止日自動產生
   - 連結至原始公文
   - 可同步至 Google Calendar

2. **手動事件** (CalendarEvent)
   - 使用者手動建立
   - 獨立存在
   - 可選擇性同步

3. **Google Calendar 事件**
   - 雙向同步
   - OAuth 2.0 認證
   - Webhook 即時更新

---

## API 端點

### 後端路由
```python
# backend/app/api/routes.py
api_router.include_router(document_calendar.router, prefix="/calendar", tags=["行事曆"])
```

### 前端端點常數
```typescript
// frontend/src/api/endpoints.ts
CALENDAR: {
  USER_EVENTS: '/calendar/users/calendar-events',
  EVENTS_UPDATE: '/calendar/events/update',
  EVENTS_DELETE: '/calendar/events/delete',
  EVENTS_SYNC: '/calendar/events/sync',
  GOOGLE_AUTH: '/calendar/google/auth',
  GOOGLE_CALLBACK: '/calendar/google/callback',
  SYNC_STATUS: '/calendar/sync-status',
}
```

**重要**: 行事曆路由前綴是 `/calendar`，不是 `/document-calendar`

---

## 資料模型

### DocumentCalendarEvent (公文行事曆事件)

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | int | 主鍵 |
| `document_id` | int | 關聯公文 ID |
| `title` | str | 事件標題 |
| `description` | str | 事件說明 |
| `start_date` | datetime | 開始時間 |
| `end_date` | datetime | 結束時間 |
| `all_day` | bool | 是否全天事件 |
| `event_type` | str | 事件類型 |
| `google_event_id` | str | Google Calendar 事件 ID |
| `sync_status` | str | 同步狀態 |

### 事件類型
```python
EVENT_TYPES = [
    'deadline',      # 截止日
    'meeting',       # 會議
    'site_visit',    # 會勘
    'reminder',      # 提醒
    'other'          # 其他
]
```

---

## Google Calendar 整合

### OAuth 流程
1. 使用者點擊「連結 Google Calendar」
2. 跳轉至 Google 授權頁面
3. 取得 authorization code
4. 交換 access_token + refresh_token
5. 儲存 Token 於資料庫

### 服務層
```
backend/app/services/
├── google_calendar_service.py       # Google API 呼叫
├── google_calendar_auth_service.py  # OAuth 認證
├── calendar_sync_service.py         # 同步邏輯
└── document_calendar_service.py     # 公文行事曆服務
```

---

## 時區處理

### 問題情境
```
前端傳送: 2026-01-08T00:00:00.000Z (UTC)
資料庫欄位: TIMESTAMP WITHOUT TIME ZONE
結果: TypeError: can't compare offset-naive and offset-aware datetimes
```

### 解決方案
後端在儲存前移除時區資訊：
```python
# backend/app/api/endpoints/document_calendar.py
start_date = event_create.start_date
if start_date.tzinfo is not None:
    start_date = start_date.replace(tzinfo=None)
```

---

## 前端組件

### 主要組件
```
frontend/src/components/calendar/
├── CalendarPage.tsx           # 行事曆頁面
├── EventModal.tsx             # 事件編輯彈窗
├── IntegratedEventModal.tsx   # 整合事件彈窗
└── CalendarToolbar.tsx        # 工具列
```

### 日曆庫
使用 FullCalendar React 組件
```typescript
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
```

---

## 常見問題

### Q: 404 Not Found - /document-calendar/events
**原因**: 路由前綴錯誤
**解法**: 使用 `/calendar/events` 而非 `/document-calendar/events`

### Q: 時區錯誤 - offset-naive and offset-aware
**解法**: 後端移除時區資訊後再儲存

### Q: Google 同步失敗
**檢查項目**:
1. Token 是否過期
2. 網路連線
3. Google Calendar API 配額

---

## 自動事件建立

### CalendarEventAutoBuilder

公文匯入時自動建立行事曆事件：

```python
# backend/app/services/calendar/event_auto_builder.py
from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

builder = CalendarEventAutoBuilder(db)
await builder.auto_create_event(document, skip_if_exists=False)
```

### 自動建立規則

| 條件 | 事件類型 | 標題格式 |
|------|---------|---------|
| 有截止日 | `deadline` | `[截止] {subject}` |
| 會議通知單 | `meeting` | `[會議] {subject}` |
| 會勘通知單 | `site_visit` | `[會勘] {subject}` |

---

## 排程服務

### 排程器管理

```python
# backend/main.py (lifespan)
from app.services.google_sync_scheduler import (
    start_google_sync_scheduler,
    stop_google_sync_scheduler,
)
from app.services.reminder_scheduler import (
    start_reminder_scheduler,
    stop_reminder_scheduler,
)
```

### 排程器狀態

| 排程器 | 說明 | 間隔 |
|--------|------|------|
| `reminder_scheduler` | 到期提醒 | 60 秒 |
| `google_sync_scheduler` | Google Calendar 同步 | 300 秒 |
| `backup_scheduler` | 資料庫備份 | 每日 02:00 |

### 健康檢查

```bash
# 查看排程器狀態
GET /health/detailed
# Response:
{
  "checks": {
    "schedulers": {
      "reminder": { "status": "running", "interval_seconds": 60 },
      "google_sync": { "status": "running", "interval_seconds": 300 },
      "backup": { "status": "running", "scheduled_time": "02:00" }
    }
  }
}
```

---

## 服務層完整結構

```
backend/app/services/
├── calendar/
│   ├── event_auto_builder.py    # 自動事件建立
│   └── ...
├── google_calendar_service.py       # Google API 呼叫
├── google_calendar_auth_service.py  # OAuth 認證
├── google_sync_scheduler.py         # Google 同步排程
├── calendar_sync_service.py         # 同步邏輯
├── document_calendar_service.py     # 公文行事曆服務
├── document_calendar_integrator.py  # 公文與事件整合
└── reminder_scheduler.py            # 提醒排程
```
