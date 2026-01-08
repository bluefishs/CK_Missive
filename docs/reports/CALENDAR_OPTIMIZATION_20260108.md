# 公文與行事曆對應管理機制優化報告

> 報告日期: 2026-01-08
> 版本: v2.0
> 狀態: ✅ 已完成優化

---

## 零、優化成果摘要

### 優化前後對比

| 項目 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 行事曆事件總數 | 5 | 621 | +616 |
| 關聯公文事件 | 2 | 618 | +616 |
| 事件覆蓋率 | 0.32% | 100% | +99.68% |
| 匯入自動建立事件 | ❌ | ✅ | 已啟用 |
| 提醒排程器 | ❌ | ✅ | 已啟用 |

### 事件類型分佈

| 類型 | 數量 | 說明 |
|------|------|------|
| reminder | 272 | 一般提醒 (收文) |
| reference | 154 | 參考事件 (發文) |
| meeting | 133 | 會議/會勘事件 |
| review | 58 | 審查事件 |
| deadline | 4 | 截止事件 |

---

## 一、原始狀態分析

### 1.1 優化前資料統計

| 項目 | 數量 | 說明 |
|------|------|------|
| 公文總數 | 618 | 收文+發文 |
| 行事曆事件 | 5 | 目前建立的事件 |
| 關聯公文事件 | 2 | 有連結公文的事件 |
| 獨立事件 | 3 | 無公文關聯的事件 |
| 提醒數量 | 0 | 尚未建立任何提醒 |

**當時問題**：
- 行事曆事件使用率極低（5/618 = 0.8%）
- 提醒機制尚未啟用（0 筆提醒）
- 大部分事件未關聯公文

### 1.2 現有架構

```
┌─────────────────────────────────────────────────────────────┐
│                     資料模型層                                │
├─────────────────────────────────────────────────────────────┤
│  OfficialDocument ──1:N──> DocumentCalendarEvent            │
│  DocumentCalendarEvent ──1:N──> EventReminder               │
│  User ──> assigned_user / created_by                        │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     服務層                                    │
├─────────────────────────────────────────────────────────────┤
│  DocumentCalendarService      - 基礎 CRUD + Google 同步      │
│  DocumentCalendarIntegrator   - 公文→事件轉換                 │
│  ReminderService              - 多層級提醒管理               │
│  NotificationService          - 通知發送                     │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     API 端點                                  │
├─────────────────────────────────────────────────────────────┤
│  /calendar/events/*           - 事件 CRUD (POST-only)        │
│  /calendar/stats              - 統計資料                     │
│  /calendar/categories         - 事件分類                     │
│  /calendar/status             - 服務狀態                     │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 現有事件類型

| 類型 | 名稱 | 說明 |
|------|------|------|
| `deadline` | 截止提醒 | 公文處理截止日 |
| `meeting` | 會議安排 | 會議通知 |
| `review` | 審核提醒 | 審查事項 |
| `reminder` | 一般提醒 | 通用提醒 |
| `reference` | 參考事件 | 無需提醒的記錄 |

---

## 二、發現的問題

### 2.1 自動化程度不足

| 問題 | 影響 | 嚴重度 |
|------|------|--------|
| 公文匯入時未自動建立事件 | 使用者需手動建立提醒 | 高 |
| 僅新增公文時建立事件 | 匯入的歷史資料無事件 | 高 |
| 事件類型判定邏輯簡化 | 無法精準分類 | 中 |

### 2.2 提醒機制未啟用

| 問題 | 現況 | 影響 |
|------|------|------|
| 提醒記錄為 0 | 從未發送過提醒 | 高 |
| 無排程任務處理提醒 | 提醒無法自動觸發 | 高 |
| Email 設定可能未完成 | 郵件通知無法發送 | 中 |

### 2.3 公文-事件關聯不完整

```
目前狀態：
- 618 筆公文
- 僅 2 筆有行事曆事件關聯
- 關聯率: 0.3%

問題：
1. 現有公文沒有批次建立事件的機制
2. 匯入時未觸發事件建立
3. 使用者不知道可以建立事件
```

### 2.4 前端整合不完善

| 問題 | 說明 |
|------|------|
| 公文詳情頁無行事曆入口 | 使用者看不到關聯事件 |
| 行事曆頁面與公文列表分離 | 需切換頁面才能操作 |
| 缺少快速建立事件按鈕 | 操作路徑過長 |

---

## 三、優化建議

### 3.1 高優先級 - 自動化事件建立

#### 3.1.1 匯入時自動建立事件

**現況**：僅 `DocumentService.create_document()` 會觸發事件建立

**建議**：在以下時機點自動建立事件

```python
# 建議修改位置：
# 1. ExcelImportService.process_row() - Excel 匯入
# 2. DocumentImportService - CSV 匯入

# 自動建立事件的條件：
if document.doc_type in ['開會通知單', '會勘通知單']:
    event_type = 'meeting'
elif document.receive_date:  # 收文
    event_type = 'deadline'  # 預設處理截止
elif document.send_date:     # 發文
    event_type = 'reference'
```

#### 3.1.2 批次建立歷史資料事件

**建議**：建立資料庫遷移腳本為現有公文建立事件

```sql
-- 為開會/會勘通知單建立事件
INSERT INTO document_calendar_events (
    document_id, title, start_date, event_type, all_day, created_at
)
SELECT
    id,
    CONCAT('[MEETING] ', subject),
    COALESCE(doc_date, receive_date, created_at),
    'meeting',
    TRUE,
    NOW()
FROM documents
WHERE doc_type IN ('開會通知單', '會勘通知單')
AND id NOT IN (SELECT document_id FROM document_calendar_events WHERE document_id IS NOT NULL);
```

### 3.2 高優先級 - 啟用提醒機制

#### 3.2.1 建立提醒處理排程

**建議**：使用 APScheduler 或 Celery 定時處理提醒

```python
# backend/app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5)
async def process_reminders():
    """每 5 分鐘處理待發送提醒"""
    async with async_session_maker() as db:
        reminder_service = ReminderService()
        stats = await reminder_service.process_pending_reminders(db)
        logger.info(f"提醒處理結果: {stats}")
```

#### 3.2.2 整合 Email 發送

**檢查項目**：
- [ ] SMTP 設定是否完成
- [ ] Email 範本是否建立
- [ ] 發送權限是否設定

### 3.3 中優先級 - 智慧事件類型判定

#### 3.3.1 公文類型對應事件類型

| 公文類型 | 事件類型 | 預設提醒 |
|----------|----------|----------|
| 開會通知單 | meeting | 1天前 |
| 會勘通知單 | meeting | 1天前 |
| 函 (收文) | deadline | 3天前 |
| 函 (發文) | reference | 無 |
| 公告 | reference | 無 |

#### 3.3.2 主旨關鍵字判定

```python
KEYWORD_EVENT_TYPE_MAP = {
    '截止': 'deadline',
    '期限': 'deadline',
    '審查': 'review',
    '會議': 'meeting',
    '會勘': 'meeting',
    '開會': 'meeting',
}

def determine_event_type(document: OfficialDocument) -> str:
    # 1. 根據公文類型
    if document.doc_type == '開會通知單':
        return 'meeting'

    # 2. 根據主旨關鍵字
    for keyword, event_type in KEYWORD_EVENT_TYPE_MAP.items():
        if keyword in document.subject:
            return event_type

    # 3. 預設
    return 'reminder' if document.category == '收文' else 'reference'
```

### 3.4 中優先級 - 前端整合優化

#### 3.4.1 公文詳情頁新增行事曆區塊

```tsx
// 在公文詳情頁新增
<Card title="相關行事曆事件" extra={<Button icon={<PlusOutlined />}>新增事件</Button>}>
  {document.calendar_events?.length > 0 ? (
    <Timeline>
      {document.calendar_events.map(event => (
        <Timeline.Item color={getEventColor(event.event_type)}>
          {event.title} - {formatDate(event.start_date)}
        </Timeline.Item>
      ))}
    </Timeline>
  ) : (
    <Empty description="尚無關聯事件" />
  )}
</Card>
```

#### 3.4.2 公文列表快速操作

```tsx
// 在公文列表的操作欄新增
<Tooltip title="新增行事曆事件">
  <Button
    icon={<CalendarOutlined />}
    onClick={() => createEventForDocument(record.id)}
  />
</Tooltip>
```

### 3.5 低優先級 - 進階功能

#### 3.5.1 批次事件管理

- 批次刪除過期事件
- 批次更新事件狀態
- 匯出行事曆（iCal 格式）

#### 3.5.2 統計儀表板

```typescript
// 行事曆統計面板
interface CalendarDashboard {
  upcoming_meetings: number;      // 近 7 天會議
  pending_deadlines: number;      // 待處理截止
  overdue_items: number;          // 已逾期項目
  monthly_event_count: number[];  // 月度事件趨勢
}
```

#### 3.5.3 Google Calendar 雙向同步

目前僅實作單向同步（本地→Google），建議：
- 實作 Webhook 監聽 Google 變更
- 同步刪除/更新操作
- 衝突處理機制

---

## 四、實施計畫

### 第一階段：基礎修復（建議優先實施）

| 項目 | 說明 | 複雜度 | 預估影響 |
|------|------|--------|----------|
| 批次建立歷史事件 | SQL 腳本為現有公文建立事件 | 低 | 高 |
| 啟用提醒排程 | 設定 APScheduler 處理提醒 | 中 | 高 |
| 匯入時建立事件 | 修改匯入服務觸發事件 | 中 | 高 |

### 第二階段：體驗優化

| 項目 | 說明 | 複雜度 | 預估影響 |
|------|------|--------|----------|
| 公文詳情頁整合 | 顯示關聯事件 | 中 | 中 |
| 智慧事件分類 | 根據公文類型/主旨判定 | 中 | 中 |
| 快速建立按鈕 | 公文列表快捷操作 | 低 | 中 |

### 第三階段：進階功能

| 項目 | 說明 | 複雜度 | 預估影響 |
|------|------|--------|----------|
| 統計儀表板 | 行事曆視覺化統計 | 中 | 低 |
| 批次管理工具 | 批量操作事件 | 中 | 低 |
| Google 雙向同步 | Webhook 整合 | 高 | 低 |

---

## 五、技術規格建議

### 5.1 事件自動建立邏輯

```python
class CalendarEventAutoBuilder:
    """公文事件自動建立器"""

    # 公文類型對應事件類型
    DOC_TYPE_EVENT_MAP = {
        '開會通知單': 'meeting',
        '會勘通知單': 'meeting',
    }

    # 類別預設事件類型
    CATEGORY_DEFAULT_MAP = {
        '收文': 'reminder',
        '發文': 'reference',
    }

    async def auto_create_event(
        self,
        db: AsyncSession,
        document: OfficialDocument,
        skip_if_exists: bool = True
    ) -> Optional[DocumentCalendarEvent]:
        """
        自動為公文建立行事曆事件

        Args:
            db: 資料庫連線
            document: 公文物件
            skip_if_exists: 已有事件時是否跳過

        Returns:
            建立的事件或 None
        """
        # 檢查是否已存在
        if skip_if_exists:
            existing = await db.execute(
                select(DocumentCalendarEvent)
                .where(DocumentCalendarEvent.document_id == document.id)
            )
            if existing.scalar_one_or_none():
                return None

        # 決定事件類型
        event_type = self._determine_event_type(document)

        # 決定事件日期
        event_date = self._determine_event_date(document)
        if not event_date:
            return None

        # 建立事件
        event = DocumentCalendarEvent(
            document_id=document.id,
            title=self._build_title(document, event_type),
            description=self._build_description(document),
            start_date=event_date,
            end_date=event_date + timedelta(hours=1),
            all_day=True,
            event_type=event_type,
            priority=self._determine_priority(event_type),
        )

        db.add(event)
        return event

    def _determine_event_type(self, document: OfficialDocument) -> str:
        # 1. 公文類型優先
        if document.doc_type in self.DOC_TYPE_EVENT_MAP:
            return self.DOC_TYPE_EVENT_MAP[document.doc_type]

        # 2. 主旨關鍵字
        if document.subject:
            if any(kw in document.subject for kw in ['截止', '期限']):
                return 'deadline'
            if any(kw in document.subject for kw in ['會議', '會勘', '開會']):
                return 'meeting'
            if any(kw in document.subject for kw in ['審查', '審核']):
                return 'review'

        # 3. 類別預設
        return self.CATEGORY_DEFAULT_MAP.get(document.category, 'reminder')

    def _determine_event_date(self, document: OfficialDocument) -> Optional[datetime]:
        # 優先順序：收文日期 > 公文日期 > 發文日期
        if document.receive_date:
            return datetime.combine(document.receive_date, datetime.min.time())
        if document.doc_date:
            return datetime.combine(document.doc_date, datetime.min.time())
        if document.send_date:
            return datetime.combine(document.send_date, datetime.min.time())
        return None
```

### 5.2 提醒排程設定

```python
# backend/app/core/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

async def setup_scheduler():
    """設定排程任務"""

    # 每 5 分鐘處理待發送提醒
    scheduler.add_job(
        process_pending_reminders,
        trigger=IntervalTrigger(minutes=5),
        id='process_reminders',
        replace_existing=True
    )

    # 每日清理過期事件
    scheduler.add_job(
        cleanup_expired_events,
        trigger='cron',
        hour=2,
        minute=0,
        id='cleanup_events',
        replace_existing=True
    )

    scheduler.start()

async def process_pending_reminders():
    """處理待發送提醒"""
    from app.db.database import async_session_maker
    from app.services.reminder_service import ReminderService

    async with async_session_maker() as db:
        service = ReminderService()
        stats = await service.process_pending_reminders(db)
        logger.info(f"提醒處理結果: {stats}")
```

---

## 六、相關文件

| 文件 | 路徑 |
|------|------|
| 資料模型 | `backend/app/extended/models.py` |
| 行事曆服務 | `backend/app/services/document_calendar_service.py` |
| 整合器 | `backend/app/services/document_calendar_integrator.py` |
| 提醒服務 | `backend/app/services/reminder_service.py` |
| 提醒排程器 | `backend/app/services/reminder_scheduler.py` |
| **事件自動建立器** | `backend/app/services/calendar/event_auto_builder.py` |
| **批次建立腳本** | `backend/app/services/calendar/batch_create_events.py` |
| API 端點 | `backend/app/api/endpoints/document_calendar.py` |
| 前端元件 | `frontend/src/components/calendar/` |

---

## 七、實施結果

### 7.1 已完成優化項目

| 項目 | 狀態 | 說明 |
|------|------|------|
| 批次建立歷史事件 | ✅ 完成 | 616 筆事件已建立 |
| CalendarEventAutoBuilder | ✅ 完成 | 智慧事件類型判定 |
| 匯入時自動建立事件 | ✅ 完成 | ExcelImportService、DocumentService 整合 |
| 提醒排程器啟用 | ✅ 完成 | 每 5 分鐘處理待發送提醒 |

### 7.2 新增程式碼

```
backend/app/services/calendar/
├── __init__.py              # 模組匯出
├── event_auto_builder.py    # 事件自動建立器
└── batch_create_events.py   # 批次建立腳本

backend/app/core/
└── scheduler.py             # 任務排程器 (備用)
```

### 7.3 修改程式碼

| 檔案 | 修改內容 |
|------|----------|
| `document_service.py` | 新增 CalendarEventAutoBuilder 整合 |
| `excel_import_service.py` | 新增 auto_create_events 參數 |
| `main.py` | 啟用提醒排程器 |

---

## 八、結論

公文與行事曆整合度已從 0.32% 提升至 100%：

| 原因 | 解決方案 |
|------|----------|
| 缺乏自動化 | ✅ CalendarEventAutoBuilder 自動建立事件 |
| 提醒未啟用 | ✅ ReminderScheduler 每 5 分鐘處理 |
| 匯入不觸發 | ✅ 匯入服務整合事件建立器 |

### 待實施項目 (中/低優先級)

| 優先級 | 項目 | 狀態 |
|--------|------|------|
| 中 | 公文詳情頁整合行事曆區塊 | 待實作 |
| 中 | 快速建立事件按鈕 | 待實作 |
| 低 | 統計儀表板 | 待實作 |
| 低 | Google 雙向同步 | 待實作 |

---

*報告完成時間: 2026-01-08*
*狀態: ✅ 高優先級項目已全部完成*
*版本: v2.0*
