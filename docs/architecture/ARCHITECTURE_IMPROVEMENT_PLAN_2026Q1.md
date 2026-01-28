# CK_Missive 系統架構改進計畫 (2026 Q1)

> **版本**: 1.0.0
> **建立日期**: 2026-01-28
> **狀態**: 待審核

---

## 📊 執行摘要

本文件基於專案程式碼、規範與 Skills 的全面檢視，提出系統整體架構改進建議。重點聚焦於：
- **模組化與元件化** - 消除重複程式碼
- **服務層與 Repository 層** - 完善分層架構
- **型別管理 (SSOT)** - 強化型別一致性
- **RWD 響應式設計** - 擴大覆蓋範圍

---

## 📈 現況分析

### 程式碼規模

| 層級 | 檔案/目錄 | 行數 | 狀態 |
|------|-----------|------|------|
| **前端頁面** | 收發文建立頁面 | 1,678 | ⚠️ 95% 重複 |
| **後端 API** | taoyuan_dispatch/ | 2,766 | ⚠️ 業務邏輯外洩 |
| **後端 API** | documents/ | 2,173 | ⚠️ Fat Controller |
| **後端服務** | Calendar + Notification | 1,914 | ⚠️ 未用 Repository |
| **Repository** | 已建立 | 5 個 | ✅ 良好基礎 |
| **RWD** | useResponsive + CSS | 完整 | ✅ 但覆蓋不全 |

### 關鍵問題

1. **前端重複代碼** - ReceiveDocumentCreatePage 與 SendDocumentCreatePage 有 95% 重複
2. **後端分層不一致** - 部分端點直接使用 ORM，部分使用 Repository
3. **業務邏輯外洩** - 超過 2,400 行業務邏輯存在於 API 端點中
4. **Repository 覆蓋不完整** - Calendar、Notification、Taoyuan 模組尚未建立 Repository

---

## 🎯 Phase 規劃

### Phase 1-B: 抽取收發文建立頁面共用邏輯

**目標**: 將 1,678 行重複代碼減少至 ~400 行

#### 當前狀態分析

| 檔案 | 行數 | 重複率 |
|------|------|--------|
| ReceiveDocumentCreatePage.tsx | 853 | 95% |
| SendDocumentCreatePage.tsx | 825 | 95% |
| **合計** | **1,678** | — |

#### 重複項目清單

| 重複內容 | 行數估計 | 位置 |
|----------|----------|------|
| 狀態宣告 (agencies, cases, users, fileList, etc.) | 60 | 兩頁皆有 |
| 資料載入 (loadAgencies, loadCases, loadUsers, loadFileSettings) | 120 | 兩頁皆有 |
| 專案人員處理 (fetchProjectStaff, handleProjectChange) | 80 | 兩頁皆有 |
| 檔案上傳邏輯 (uploadFiles, validateFile) | 100 | 兩頁皆有 |
| Tab 渲染 (renderInfoTab, renderCaseStaffTab, renderAttachmentsTab) | 600 | 兩頁皆有 |
| 常數定義 (DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_MAX_FILE_SIZE_MB) | 20 | 已在 documentOperationsUtils 但未使用 |

#### 建議實作

**1. 建立 `useDocumentCreateForm.ts` Hook** (~280 行)

```typescript
// frontend/src/hooks/business/useDocumentCreateForm.ts

export interface UseDocumentCreateFormOptions {
  mode: 'receive' | 'send';
  form: FormInstance;
  onSuccess?: (document: OfficialDocument) => void;
}

export interface UseDocumentCreateFormResult {
  // 狀態
  loading: boolean;
  saving: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // 資料選項
  agencies: AgencyOption[];
  cases: ContractProject[];
  users: User[];
  projectStaffMap: Record<number, ProjectStaff[]>;
  fileSettings: FileSettings;

  // 檔案上傳
  fileList: UploadFile[];
  uploading: boolean;
  uploadProgress: Record<string, number>;
  uploadErrors: string[];

  // 事件處理
  handleProjectChange: (projectId: number | null) => Promise<void>;
  handleFileChange: (info: UploadChangeParam) => void;
  validateFile: (file: UploadFile) => boolean;
  handleSubmit: (values: DocumentFormValues) => Promise<void>;
  handleCancel: () => void;

  // 僅 Send 模式
  nextNumber?: string;
}

export function useDocumentCreateForm(options: UseDocumentCreateFormOptions): UseDocumentCreateFormResult {
  // 整合現有的 useDocumentOperations 和 useDocumentForm
  // 加入 mode 判斷處理差異
}
```

**2. 建立共用 Tab 元件**

```
frontend/src/components/document/create/
├── DocumentCreateInfoTab.tsx      (~200 行)
├── DocumentCreateStaffTab.tsx     (~100 行)
├── DocumentCreateAttachmentTab.tsx (~150 行)
└── index.ts
```

**3. 重構後的頁面結構**

```typescript
// ReceiveDocumentCreatePage.tsx (~80 行)
export function ReceiveDocumentCreatePage() {
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const formState = useDocumentCreateForm({
    mode: 'receive',
    form,
    onSuccess: () => navigate('/documents'),
  });

  const tabItems = [
    { key: 'info', children: <DocumentCreateInfoTab {...formState} mode="receive" /> },
    { key: 'staff', children: <DocumentCreateStaffTab {...formState} /> },
    { key: 'attachments', children: <DocumentCreateAttachmentTab {...formState} /> },
  ];

  return (
    <DetailPageLayout title="新增收文" tabs={tabItems} />
  );
}
```

#### 預期效益

| 指標 | 當前 | 重構後 | 改善 |
|------|------|--------|------|
| 總行數 | 1,678 | ~530 | -68% |
| 重複代碼 | 1,600 | 0 | -100% |
| 可維護性 | 低 | 高 | ⬆️ |

---

### Phase 2-A: 後端端點瘦身 - taoyuan_dispatch 業務邏輯下沉

**目標**: 將 2,400+ 行業務邏輯從 API 層移至 Service/Repository 層

#### 當前狀態分析

| 檔案 | 行數 | 違規嚴重度 | 主要問題 |
|------|------|-----------|----------|
| dispatch.py | 718 | 🔴 CRITICAL | 162 行 Excel 匯入、序號生成、文件匹配 |
| payments.py | 400 | 🔴 CRITICAL | 165 行控制報表生成 |
| projects.py | 359 | 🟠 HIGH | 97 行 CSV 匯入、查詢邏輯 |
| dispatch_document_links.py | 334 | 🟠 HIGH | N+1 查詢問題 |
| document_project_links.py | 209 | 🟡 MEDIUM | 重複 TaoyuanLinkService |
| project_dispatch_links.py | 187 | 🟡 MEDIUM | 重複 TaoyuanLinkService |
| master_control.py | 146 | 🟡 MEDIUM | 聚合邏輯 |
| statistics.py | 102 | 🟡 MEDIUM | 統計計算 |
| attachments.py | 311 | 🟢 OK | 檔案處理適當 |

**總計**: 2,766 行，其中 ~2,400 行違反分層架構

#### 建議新增服務

**1. DispatchOrderService** (~400 行)

```python
# backend/app/services/taoyuan/dispatch_order_service.py

class DispatchOrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DispatchOrderRepository(db)
        self.link_service = TaoyuanLinkService(db)

    # 從 dispatch.py 遷移
    async def generate_sequence_number(self, year: int) -> str: ...
    async def get_with_history(self, order_id: int) -> DispatchOrderWithHistory: ...
    async def match_documents(self, order_id: int) -> List[MatchedDocument]: ...

    # 從 Excel 匯入邏輯遷移
    async def import_from_excel(self, file: UploadFile) -> ImportResult: ...
```

**2. PaymentService** (~300 行)

```python
# backend/app/services/taoyuan/payment_service.py

class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 從 payments.py 遷移
    async def calculate_cumulative_payment(self, project_id: int) -> CumulativePayment: ...
    async def generate_control_report(self, project_id: int) -> ControlReport: ...
    async def get_payment_with_documents(self, dispatch_id: int) -> PaymentWithDocuments: ...
```

**3. TaoyuanStatisticsService** (~150 行)

```python
# backend/app/services/taoyuan/statistics_service.py

class TaoyuanStatisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview_stats(self, year: int = None) -> OverviewStats: ...
    async def get_project_summary(self, project_id: int) -> ProjectSummary: ...
```

#### 建議新增 Repository

**1. DispatchOrderRepository** (~350 行)

```python
# backend/app/repositories/taoyuan/dispatch_order_repository.py

class DispatchOrderRepository(BaseRepository[TaoyuanDispatchOrder]):
    # 查詢
    async def get_with_links(self, order_id: int) -> TaoyuanDispatchOrder: ...
    async def filter_orders(self, filters: DispatchFilterParams) -> Tuple[List, int]: ...
    async def get_by_project(self, project_id: int) -> List[TaoyuanDispatchOrder]: ...

    # 序號
    async def get_max_sequence(self, year: int) -> int: ...

    # 關聯
    async def get_document_links(self, order_id: int) -> List[DispatchDocumentLink]: ...
```

**2. TaoyuanProjectRepository** (~250 行)

```python
# backend/app/repositories/taoyuan/project_repository.py

class TaoyuanProjectRepository(BaseRepository[TaoyuanProject]):
    async def get_with_dispatches(self, project_id: int) -> TaoyuanProject: ...
    async def filter_projects(self, filters: ProjectFilterParams) -> Tuple[List, int]: ...
    async def get_summary(self, project_id: int) -> ProjectSummary: ...
```

#### 重構後端點範例

```python
# 重構前 (dispatch.py, 100+ 行)
@router.get("/{order_id}/detail-with-history")
async def get_detail_with_history(order_id: int, db: AsyncSession = Depends(get_async_db)):
    # 100+ 行的查詢、聚合、轉換邏輯
    ...

# 重構後 (~15 行)
@router.get("/{order_id}/detail-with-history")
async def get_detail_with_history(
    order_id: int,
    service: DispatchOrderService = Depends(get_service_with_db(DispatchOrderService))
):
    result = await service.get_with_history(order_id)
    if not result:
        raise HTTPException(404, "派工單不存在")
    return result
```

#### 預期效益

| 指標 | 當前 | 重構後 | 改善 |
|------|------|--------|------|
| API 層代碼 | 2,766 | ~900 | -67% |
| Service 層代碼 | 505 | ~1,350 | 業務邏輯集中 |
| Repository 層代碼 | 0 | ~600 | 資料存取抽象 |
| N+1 查詢風險 | 高 | 低 | ⬆️ |

---

### Phase 2-B: 後端端點瘦身 - documents/dashboard 業務邏輯下沉

**目標**: 將 2,173 行端點代碼瘦身至 ~1,400 行

#### 當前狀態分析

| 檔案 | 行數 | 問題 |
|------|------|------|
| stats.py | 456 | 🔴 原始 SQL、8 次分離查詢、複雜 WHERE 建構 |
| list.py | 550 | 🟠 N+1 優化硬編碼、重複篩選邏輯 |
| export.py | 377 | 🟠 資料轉換、Excel 樣式在 API 層 |
| audit.py | 142 | 🟠 原始 SQL text() 查詢 |
| crud.py | 451 | 🟢 已使用 DocumentService |
| import_.py | 197 | 🟢 委派給 ExcelImportService |

#### 建議改進

**1. 擴展 DocumentRepository** (+200 行)

```python
# 新增方法到 backend/app/repositories/document_repository.py

class DocumentRepository(BaseRepository[OfficialDocument]):
    # 現有方法...

    # 新增統計方法
    async def get_statistics(self) -> DocumentStatistics:
        """單一查詢取得所有統計 (取代 8 次分離查詢)"""
        query = text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE category = '發文') as send_count,
                COUNT(*) FILTER (WHERE category = '收文') as receive_count,
                COUNT(*) FILTER (WHERE delivery_method = '電子交換') as electronic_count,
                COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM doc_date) = EXTRACT(YEAR FROM CURRENT_DATE)) as current_year_count
            FROM documents
        """)
        result = await self.db.execute(query)
        row = result.fetchone()
        return DocumentStatistics.from_row(row)

    async def get_filtered_statistics(self, filters: DocumentFilter) -> FilteredStatistics: ...
    async def get_document_number_sequence(self, prefix: str, year: int) -> int: ...

    # 新增關聯載入方法
    async def get_list_with_relations(
        self,
        skip: int,
        limit: int,
        filters: DocumentFilter,
        include_projects: bool = True,
        include_staff: bool = True,
        include_attachments: bool = True,
    ) -> Tuple[List[DocumentWithRelations], int]: ...
```

**2. 新增 AgencyRepository 下拉選項方法**

```python
# backend/app/repositories/agency_repository.py

class AgencyRepository(BaseRepository[GovernmentAgency]):
    # 現有方法...

    async def get_dropdown_options(
        self,
        search: str = None,
        limit: int = 50
    ) -> List[AgencyDropdownOption]:
        """取代 stats.py 中的原始 SQL"""
        query = select(
            GovernmentAgency.id,
            GovernmentAgency.agency_name,
            GovernmentAgency.agency_code,
            GovernmentAgency.agency_short_name,
        ).where(GovernmentAgency.agency_name.isnot(None))

        if search:
            query = query.where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{search}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(GovernmentAgency.agency_name).limit(limit)
        result = await self.db.execute(query)
        return [AgencyDropdownOption.from_row(row) for row in result]
```

**3. 建立 DocumentExportService** (~200 行)

```python
# backend/app/services/document_export_service.py

class DocumentExportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRepository(db)

    async def prepare_export_data(
        self,
        documents: List[OfficialDocument],
        format: Literal['excel', 'csv'] = 'excel'
    ) -> pd.DataFrame: ...

    async def generate_summary_statistics(
        self,
        documents: List[OfficialDocument]
    ) -> ExportSummary: ...

    def create_excel_file(
        self,
        df: pd.DataFrame,
        summary: ExportSummary
    ) -> BytesIO: ...
```

**4. 建立 AuditLogRepository** (~150 行)

```python
# backend/app/repositories/audit_log_repository.py

class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_filters(
        self,
        document_id: int = None,
        user_id: int = None,
        action: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditLog], int]: ...
```

#### 預期效益

| 指標 | 當前 | 重構後 | 改善 |
|------|------|--------|------|
| API 層代碼 | 2,173 | ~1,400 | -35% |
| 原始 SQL 呼叫 | 18+ | 0 | -100% |
| N+1 查詢風險區 | 6+ | 1 | -83% |

---

### Phase 2-C: 建立 CalendarRepository 和 NotificationRepository

**目標**: 完成 Repository 層覆蓋，統一資料存取模式

#### 當前狀態

| 模組 | Service 行數 | Repository | 狀態 |
|------|-------------|------------|------|
| Calendar | 651 | ❌ 無 | 直接 ORM |
| Notification | 663 | ❌ 無 | 直接 ORM |
| EventReminder | (內嵌) | ❌ 無 | 直接 ORM |

#### 建議新增 Repository

**1. CalendarRepository** (~350 行)

```python
# backend/app/repositories/calendar_repository.py

class CalendarRepository(BaseRepository[DocumentCalendarEvent]):
    """行事曆事件 Repository"""

    # 查詢方法
    async def get_by_document(self, document_id: int) -> List[DocumentCalendarEvent]: ...
    async def get_by_user(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[DocumentCalendarEvent]: ...
    async def filter_events(self, filters: EventFilterParams) -> Tuple[List, int]: ...

    # Google 同步相關
    async def get_pending_sync_events(self, limit: int = 100) -> List[DocumentCalendarEvent]: ...
    async def mark_synced(self, event_id: int, google_event_id: str) -> None: ...
    async def mark_sync_failed(self, event_id: int, error: str) -> None: ...

    # 衝突檢測
    async def get_conflicting_events(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_id: int = None
    ) -> List[DocumentCalendarEvent]: ...

    # 統計
    async def count_by_status(self, user_id: int) -> Dict[str, int]: ...
    async def count_upcoming(self, user_id: int, days: int = 7) -> int: ...
    async def count_overdue(self, user_id: int) -> int: ...
```

**2. EventReminderRepository** (~200 行)

```python
# backend/app/repositories/event_reminder_repository.py

class EventReminderRepository(BaseRepository[EventReminder]):
    """事件提醒 Repository"""

    async def get_by_event(self, event_id: int) -> List[EventReminder]: ...
    async def get_pending_reminders(self, limit: int = 100) -> List[EventReminder]: ...
    async def get_by_recipient(
        self,
        user_id: int,
        is_sent: bool = None
    ) -> List[EventReminder]: ...

    # 狀態更新
    async def mark_sent(self, reminder_id: int) -> None: ...
    async def mark_failed(self, reminder_id: int, next_retry_at: datetime = None) -> None: ...
    async def increment_retry_count(self, reminder_id: int) -> None: ...
```

**3. NotificationRepository** (~280 行)

```python
# backend/app/repositories/notification_repository.py

class NotificationRepository(BaseRepository[SystemNotification]):
    """系統通知 Repository"""

    # 查詢
    async def get_by_user(
        self,
        user_id: int,
        is_read: bool = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[SystemNotification], int]: ...

    async def filter_notifications(
        self,
        user_id: int,
        severity: str = None,
        notification_type: str = None,
        is_read: bool = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SystemNotification], int]: ...

    # 狀態更新
    async def mark_read(self, notification_id: int) -> bool: ...
    async def mark_read_batch(self, notification_ids: List[int]) -> int: ...
    async def mark_all_read(self, user_id: int) -> int: ...
    async def get_unread_count(self, user_id: int) -> int: ...

    # 清理
    async def delete_old(self, older_than_days: int) -> int: ...
```

#### 重構服務層

```python
# backend/app/services/document_calendar_service.py (重構後)

class DocumentCalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = CalendarRepository(db)
        self.reminder_repository = EventReminderRepository(db)

    # 現有方法保持 API 不變
    # 但內部實作改用 Repository

    async def get_event(self, event_id: int) -> DocumentCalendarEvent:
        return await self.repository.get_by_id(event_id)

    async def get_pending_sync_events(self, limit: int = 100) -> List[DocumentCalendarEvent]:
        return await self.repository.get_pending_sync_events(limit)
```

#### 預期效益

| 指標 | 當前 | 重構後 | 改善 |
|------|------|--------|------|
| Repository 覆蓋 | 5 個 | 8 個 | +60% |
| 資料存取一致性 | 部分 | 完整 | ⬆️ |
| 單元測試便利性 | 中 | 高 | ⬆️ |

---

## 🎨 RWD 響應式設計建議

### 當前覆蓋情況

| 項目 | 狀態 | 說明 |
|------|------|------|
| useResponsive Hook | ✅ 完整 | 275 行，功能齊全 |
| responsive.css | ✅ 完整 | 405 行，覆蓋主要元件 |
| ResponsiveContainer | ✅ 存在 | 基本容器元件 |
| 頁面覆蓋率 | ⚠️ 部分 | 25 個檔案使用 |

### 建議改進

**1. 建立響應式表格元件**

```typescript
// frontend/src/components/common/ResponsiveTable.tsx

interface ResponsiveTableProps<T> {
  dataSource: T[];
  columns: ColumnsType<T>;
  mobileCardRender?: (record: T) => React.ReactNode;
  enableCardMode?: boolean;  // 自動在手機切換卡片模式
}

export function ResponsiveTable<T>({
  dataSource,
  columns,
  mobileCardRender,
  enableCardMode = true
}: ResponsiveTableProps<T>) {
  const { isMobile } = useResponsive();

  if (isMobile && enableCardMode && mobileCardRender) {
    return <MobileCardList items={dataSource} renderItem={mobileCardRender} />;
  }

  return <Table dataSource={dataSource} columns={columns} scroll={{ x: 'max-content' }} />;
}
```

**2. 建立響應式表單佈局**

```typescript
// frontend/src/components/common/ResponsiveForm.tsx

export function ResponsiveFormRow({ children }: { children: React.ReactNode[] }) {
  const { responsive } = useResponsive();
  const colSpan = responsive({ xs: 24, sm: 12, md: 8, lg: 6 });

  return (
    <Row gutter={[16, 16]}>
      {React.Children.map(children, (child) => (
        <Col span={colSpan}>{child}</Col>
      ))}
    </Row>
  );
}
```

**3. 頁面覆蓋擴展**

| 頁面 | 當前狀態 | 建議改進 |
|------|----------|----------|
| DocumentPage | 部分 | 新增 mobileCardRender |
| TaoyuanDispatchPage | 部分 | 新增 mobileCardRender |
| CalendarPage | 部分 | 手機版簡化檢視 |
| 建立/編輯表單頁面 | 部分 | 使用 ResponsiveFormRow |

---

## 📊 型別管理 (SSOT) 建議

### 當前遵循情況

| 層級 | SSOT 來源 | 遵循率 |
|------|-----------|--------|
| 後端 Schema | `backend/app/schemas/` | ✅ 95% |
| 前端型別 | `frontend/src/types/api.ts` | ✅ 90% |
| API 端點 | 從 schemas 匯入 | ⚠️ 85% |

### 待修正項目

1. **taoyuan_dispatch 端點** - 部分使用本地 Pydantic model
2. **stats.py** - 使用 `Dict[str, Any]` 而非定義明確 Schema
3. **前端 hooks** - 部分使用 `any` 型別

### 建議

1. 建立 `backend/app/schemas/statistics.py` - 統一統計回應型別
2. 建立 `backend/app/schemas/taoyuan/` 目錄 - 集中桃園模組 Schema
3. 前端新增 `types/taoyuan.ts` - 桃園模組型別定義

---

## 📋 實作優先順序

### 第一優先 (Phase 1-B)

| 任務 | 預估工時 | 影響範圍 |
|------|----------|----------|
| 建立 useDocumentCreateForm Hook | 4-6 小時 | 2 頁面 |
| 建立 3 個 Tab 元件 | 3-4 小時 | 2 頁面 |
| 重構收發文頁面 | 2-3 小時 | 2 頁面 |
| 單元測試 | 2-3 小時 | — |
| **合計** | **11-16 小時** | **-68% 代碼** |

### 第二優先 (Phase 2-A)

| 任務 | 預估工時 | 影響範圍 |
|------|----------|----------|
| 建立 DispatchOrderService | 4-5 小時 | dispatch.py |
| 建立 PaymentService | 3-4 小時 | payments.py |
| 建立 TaoyuanStatisticsService | 2-3 小時 | statistics.py |
| 建立 Repository 層 | 4-5 小時 | 全模組 |
| 重構端點使用服務 | 3-4 小時 | 10 檔案 |
| **合計** | **16-21 小時** | **-67% API 代碼** |

### 第三優先 (Phase 2-B)

| 任務 | 預估工時 | 影響範圍 |
|------|----------|----------|
| 擴展 DocumentRepository | 3-4 小時 | stats.py, list.py |
| 建立 DocumentExportService | 2-3 小時 | export.py |
| 建立 AuditLogRepository | 2 小時 | audit.py |
| 重構端點 | 2-3 小時 | 4 檔案 |
| **合計** | **9-12 小時** | **-35% API 代碼** |

### 第四優先 (Phase 2-C)

| 任務 | 預估工時 | 影響範圍 |
|------|----------|----------|
| 建立 CalendarRepository | 3-4 小時 | calendar 模組 |
| 建立 EventReminderRepository | 2-3 小時 | calendar 模組 |
| 建立 NotificationRepository | 2-3 小時 | notification 模組 |
| 重構服務使用 Repository | 2-3 小時 | 2 服務 |
| **合計** | **9-13 小時** | **完整 Repository 覆蓋** |

---

## 📈 總體效益預估

| 指標 | 當前 | 完成後 | 改善 |
|------|------|--------|------|
| 前端重複代碼 | ~1,600 行 | ~0 行 | -100% |
| 後端 API 層代碼 | ~5,000 行 | ~2,300 行 | -54% |
| Repository 覆蓋 | 5 個 | 10+ 個 | +100% |
| 原始 SQL 呼叫 | 20+ 處 | 0 處 | -100% |
| 型別一致性 | 85% | 98% | +15% |
| 單元測試便利性 | 中 | 高 | ⬆️ |

---

## 🔗 相關文件

- `.claude/MANDATORY_CHECKLIST.md` - 開發檢查清單
- `.claude/skills/type-management.md` - 型別管理規範
- `docs/Architecture_Optimization_Recommendations.md` - 架構優化建議
- `backend/app/repositories/README.md` - Repository 使用指南

---

*文件維護: Claude Code Assistant*
*最後更新: 2026-01-28*
