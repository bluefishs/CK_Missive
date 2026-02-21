# 行事曆模組優化整合評估報告

**評估日期**: 2026-01-08
**評估版本**: 3.0.0

---

## 一、現況分析

### 1.1 前端架構分析

| 檔案 | 行數 | 職責 | 問題 |
|------|------|------|------|
| `EnhancedCalendarView.tsx` | 847 | 主視圖、篩選、批次操作、3種視圖模式 | **過於龐大**，違反單一職責 |
| `EventFormModal.tsx` | 397 | 事件新增/編輯表單 | 尚可，但可抽離驗證邏輯 |
| `ReminderSettingsModal.tsx` | 339 | 提醒設定管理 | 合理 |
| `CalendarPage.tsx` | 324 | 頁面容器 | 合理 |

**問題識別**:
1. `EnhancedCalendarView.tsx` 包含過多邏輯（847行），應拆分
2. 事件類型配置散落在多處，未集中管理
3. 缺乏專門的 Calendar Context 管理狀態

### 1.2 後端架構分析

| 檔案 | 職責 | 問題 |
|------|------|------|
| `document_calendar_service.py` | Google API 整合、DB 操作 | **職責過重**（645行），混合關注點 |
| `document_calendar_integrator.py` | 公文轉事件邏輯 | 合理但依賴服務層過深 |
| `google_sync_scheduler.py` | 自動同步排程 | 合理 |
| `reminder_scheduler.py` | 提醒排程 | 合理 |

**問題識別**:
1. `document_calendar_service.py` 同時處理 Google API 和本地資料庫，應分離
2. 缺乏統一的錯誤處理策略
3. 部分方法缺乏型別標註

### 1.3 響應式設計評估

| 元素 | 現況 | 問題 |
|------|------|------|
| 月曆視圖 | 固定 Col span={18} | 小螢幕溢出 |
| 側邊欄 | 固定 Col span={6} | 小螢幕過窄 |
| Modal 寬度 | 固定 700px | 手機無法顯示 |
| 時間軸 | 無響應式處理 | 卡片過寬 |
| 工具列按鈕 | 並排顯示 | 小螢幕擁擠 |

---

## 二、優化建議

### 2.1 前端組件重構方案

#### A. 拆分 EnhancedCalendarView

```
components/calendar/
├── EnhancedCalendarView.tsx     # 主容器 (150行)
├── views/
│   ├── MonthView.tsx            # 月曆視圖
│   ├── ListView.tsx             # 列表視圖
│   └── TimelineView.tsx         # 時間軸視圖
├── components/
│   ├── CalendarToolbar.tsx      # 工具列
│   ├── CalendarStats.tsx        # 統計面板
│   ├── EventCard.tsx            # 事件卡片
│   ├── BatchActions.tsx         # 批次操作
│   └── FilterPanel.tsx          # 篩選面板
├── hooks/
│   ├── useCalendarFilters.ts    # 篩選邏輯
│   ├── useCalendarSelection.ts  # 選取邏輯
│   └── useCalendarNavigation.ts # 導航邏輯
└── constants/
    └── calendarConfig.ts        # 事件類型、優先級配置
```

#### B. 建立 Calendar Context

```typescript
// contexts/CalendarContext.tsx
interface CalendarContextValue {
  events: CalendarEvent[];
  filters: FilterState;
  selectedIds: number[];
  viewMode: ViewMode;
  actions: {
    setFilter: (filter: Partial<FilterState>) => void;
    selectEvent: (id: number) => void;
    batchDelete: () => Promise<void>;
    refresh: () => void;
  };
}

export const CalendarProvider: React.FC = ({ children }) => {
  // 集中管理狀態
};
```

#### C. 響應式優化

```tsx
// CalendarPage.tsx 響應式改造
<Row gutter={[16, 16]}>
  <Col xs={24} lg={18}>
    <EnhancedCalendarView />
  </Col>
  <Col xs={24} lg={6}>
    <SidePanel />
  </Col>
</Row>

// Modal 響應式
<Modal
  width={{ xs: '100%', sm: 600, md: 700 }}
  style={{ maxWidth: '95vw' }}
>
```

### 2.2 後端服務層重構方案

#### A. 分離 Google Calendar 服務

```
services/
├── calendar/
│   ├── __init__.py
│   ├── google_calendar_client.py   # Google API 封裝
│   ├── calendar_repository.py      # 資料庫操作
│   ├── calendar_service.py         # 業務邏輯協調
│   └── sync_service.py             # 同步邏輯
├── document_calendar_integrator.py
└── schedulers/
    ├── google_sync_scheduler.py
    └── reminder_scheduler.py
```

#### B. 建立 Repository 模式

```python
# calendar_repository.py
class CalendarEventRepository:
    """資料庫操作封裝"""

    async def get_by_id(self, db: AsyncSession, event_id: int) -> Optional[Event]:
        """取得單一事件（含關聯）"""

    async def get_pending_sync(self, db: AsyncSession, limit: int) -> List[Event]:
        """取得待同步事件"""

    async def create(self, db: AsyncSession, data: EventCreate) -> Event:
        """建立事件"""

    async def update(self, db: AsyncSession, event_id: int, data: EventUpdate) -> Event:
        """更新事件"""
```

#### C. 統一錯誤處理

```python
# exceptions/calendar_exceptions.py
class CalendarError(AppException):
    """行事曆基礎錯誤"""

class GoogleCalendarSyncError(CalendarError):
    """Google 同步錯誤"""

class EventNotFoundError(CalendarError):
    """事件不存在"""

class ConflictDetectionError(CalendarError):
    """衝突偵測錯誤"""
```

### 2.3 API 端點優化

#### A. 端點整合

| 現況 | 建議 |
|------|------|
| POST /events/list | 保留 |
| POST /events/update | 合併至 PUT /events/{id} |
| POST /events/delete | 合併至 DELETE /events/{id} |
| POST /events/sync | 保留 |
| POST /events/bulk-sync | 保留 |

#### B. 新增端點

```python
# 從公文建立提醒 (簡化流程)
POST /api/documents/{id}/create-reminder
{
    "deadline": "2026-01-15T00:00:00",
    "reminder_days": [7, 3, 1],
    "event_type": "deadline"
}

# 批次操作
POST /api/calendar/events/batch
{
    "action": "delete" | "complete" | "sync",
    "event_ids": [1, 2, 3]
}
```

---

## 三、響應式設計改進

### 3.1 斷點策略

```scss
// 建議斷點
$breakpoints: (
  xs: 0,      // 手機
  sm: 576px,  // 大手機
  md: 768px,  // 平板
  lg: 992px,  // 小筆電
  xl: 1200px, // 桌機
  xxl: 1600px // 大螢幕
);
```

### 3.2 組件響應式改造

#### CalendarPage 布局

```tsx
// 小螢幕時側邊欄移至底部
const { xs, sm, md } = Grid.useBreakpoint();

<Row gutter={[16, 16]}>
  <Col xs={24} md={18} lg={18}>
    <EnhancedCalendarView
      viewMode={xs ? 'list' : viewMode} // 小螢幕強制列表視圖
    />
  </Col>
  <Col xs={24} md={6} lg={6}>
    <Affix offsetTop={xs ? undefined : 80}>
      <SidePanel collapsed={xs} />
    </Affix>
  </Col>
</Row>
```

#### Modal 響應式

```tsx
const { xs } = Grid.useBreakpoint();

<Modal
  width={xs ? '100%' : 700}
  style={{
    maxWidth: '95vw',
    top: xs ? 0 : 100
  }}
  bodyStyle={{
    maxHeight: xs ? 'calc(100vh - 110px)' : 'auto',
    overflow: 'auto'
  }}
>
```

#### 工具列響應式

```tsx
// 小螢幕時隱藏部分按鈕，改用下拉選單
{!xs ? (
  <Space>
    <Button icon={<PlusOutlined />}>新增事件</Button>
    <Button icon={<FilterOutlined />}>篩選</Button>
    <Radio.Group>...</Radio.Group>
  </Space>
) : (
  <Space>
    <Button icon={<PlusOutlined />} />
    <Dropdown menu={{ items: mobileMenuItems }}>
      <Button icon={<MoreOutlined />} />
    </Dropdown>
  </Space>
)}
```

---

## 四、效能優化建議

### 4.1 前端效能

| 項目 | 現況 | 建議 |
|------|------|------|
| 事件列表渲染 | 全量渲染 | 虛擬滾動 (react-window) |
| 篩選計算 | 每次渲染 | useMemo + debounce |
| API 請求 | 每次切換頁面 | React Query 快取 (已實作) |
| 月曆事件渲染 | 全量計算 | 按可視月份懶載入 |

### 4.2 後端效能

| 項目 | 現況 | 建議 |
|------|------|------|
| 事件查詢 | 每次全表掃描 | 增加複合索引 |
| Google 同步 | 同步執行 | 背景任務 (已實作) |
| 關聯載入 | 部分 lazy load | 全面 eager load |
| 資料庫連線 | 預設連線池 | 調整連線池大小 |

```sql
-- 建議索引
CREATE INDEX idx_calendar_events_user_date
ON document_calendar_events(assigned_user_id, start_date);

CREATE INDEX idx_calendar_events_sync_status
ON document_calendar_events(google_sync_status)
WHERE google_sync_status IN ('pending', 'failed');
```

---

## 五、實施優先級

### 第一階段 (立即)

- [x] 修復批次刪除後頁面不更新
- [x] 修復時間軸排序
- [x] 修復公文導航路徑
- [x] 修復 antd 靜態方法警告
- [x] 修復 Google Calendar 同步 greenlet 錯誤

### 第二階段 (1-2週)

- [ ] 響應式布局優化 (CalendarPage, Modal)
- [ ] 拆分 EnhancedCalendarView 組件
- [ ] 建立 calendarConfig.ts 集中配置
- [ ] 新增公文頁面「加入行事曆」按鈕

### 第三階段 (2-4週)

- [ ] 後端服務層重構 (Repository 模式)
- [ ] 統一錯誤處理機制
- [ ] 建立 CalendarContext
- [ ] 效能優化 (虛擬滾動、索引)

### 第四階段 (長期)

- [ ] 拖曳調整事件
- [ ] 重複事件支援
- [ ] 團隊日曆視圖
- [ ] 週/日視圖模式

---

## 六、測試檢核清單

### API 端點測試

| 端點 | 狀態 | 備註 |
|------|------|------|
| POST /events/list | ✅ | 正常回傳事件列表 |
| POST /events | ✅ | 建立事件成功 |
| POST /events/delete | ✅ | 刪除成功 |
| POST /events/sync | ✅ | 同步成功 |
| POST /events/bulk-sync | ✅ | 批次同步成功 |
| POST /events/check-conflicts | ✅ | 衝突偵測正常 |
| GET /sync-scheduler/status | ✅ | 排程器狀態正常 |
| POST /sync-scheduler/trigger | ✅ | 手動觸發成功 |

### 功能測試

| 功能 | 狀態 | 備註 |
|------|------|------|
| Google Calendar 同步 | ✅ | 已同步 7 個事件 |
| 自動同步排程器 | ✅ | 每 10 分鐘執行 |
| 事件衝突偵測 | ✅ | 正確識別重疊事件 |
| 時間軸降冪排序 | ✅ | 最新事件在上 |
| 關聯公文導航 | ✅ | 正確跳轉至 /documents/{id} |
| 批次刪除後刷新 | ✅ | 自動重新載入 |

---

*報告產生日期: 2026-01-08*
