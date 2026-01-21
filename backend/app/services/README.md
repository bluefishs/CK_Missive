# 服務層架構規範

> **版本**: 1.1.0
> **日期**: 2026-01-21
> **維護**: Claude Code Assistant

---

## 目錄結構

### 現有結構

```
services/
├── base_service.py              # 泛型 CRUD 基類
├── base/                        # 基礎工具類
│   ├── __init__.py
│   ├── import_base.py          # 匯入服務基類
│   ├── query_helper.py         # 查詢輔助工具
│   ├── response.py             # 統一回應結構
│   ├── unit_of_work.py         # UoW 模式
│   └── validators.py           # 共用驗證器
├── calendar/                    # 行事曆批次處理
│   ├── batch_create_events.py  # 批次建立事件
│   └── event_auto_builder.py   # 事件自動建構
├── strategies/                  # 策略模式實作
│   └── agency_matcher.py       # 機關/承攬案件匹配
│
├── [公文服務群]
│   ├── document_service.py                 # 核心公文服務
│   ├── document_query_filter_service.py    # 公文查詢篩選
│   ├── document_serial_number_service.py   # 流水序號服務
│   ├── document_import_service.py          # 公文匯入
│   ├── document_export_service.py          # 公文匯出
│   ├── document_processor.py               # 公文處理器
│   ├── document_calendar_service.py        # 公文行事曆
│   └── document_calendar_integrator.py     # 行事曆整合
│
├── [通知服務群]
│   ├── notification_service.py             # 核心通知服務
│   ├── notification_template_service.py    # 通知模板
│   ├── project_notification_service.py     # 專案通知
│   └── reminder_service.py                 # 提醒服務
│
├── [排程服務群]
│   ├── backup_scheduler.py                 # 備份排程
│   ├── google_sync_scheduler.py            # Google 同步排程
│   └── reminder_scheduler.py               # 提醒排程
│
├── [實體服務群]
│   ├── agency_service.py                   # 機關服務 (繼承 BaseService)
│   ├── vendor_service.py                   # 廠商服務 (繼承 BaseService)
│   ├── project_service.py                  # 承攬案件服務
│   └── project_agency_contact_service.py   # 專案機關聯絡人
│
├── [匯入處理群]
│   ├── csv_processor.py                    # CSV 處理器
│   └── excel_import_service.py             # Excel 匯入
│
└── [其他服務]
    ├── admin_service.py                    # 管理員服務
    ├── audit_service.py                    # 稽核服務
    ├── backup_service.py                   # 備份服務
    ├── navigation_service.py               # 導覽服務
    └── search_optimizer.py                 # 搜尋優化
```

### 新服務建議結構

新增服務時，建議移至對應子目錄：

```
services/
├── document/               # 公文相關服務
├── notification/           # 通知相關服務
├── scheduler/              # 排程相關服務
├── entity/                 # 實體 CRUD 服務
└── integration/            # 外部整合服務
```

---

## BaseService 繼承規範

### 何時應該繼承 BaseService

| 條件 | 範例 | 說明 |
|------|------|------|
| **簡單 CRUD 實體** | VendorService, AgencyService | 主要操作為增刪改查 |
| **無複雜業務邏輯** | - | 不涉及外部整合、排程、策略模式 |
| **單一資料表操作** | - | 主要操作單一資料表 |

```python
# ✅ 推薦：簡單實體繼承 BaseService
class VendorService(BaseService[PartnerVendor, VendorCreate, VendorUpdate]):
    def __init__(self):
        super().__init__(PartnerVendor, "廠商")

    # 可覆寫方法加入業務邏輯
    async def create(self, db: AsyncSession, data: VendorCreate) -> PartnerVendor:
        # 加入重複檢查
        if data.vendor_code:
            existing = await self.get_by_field(db, "vendor_code", data.vendor_code)
            if existing:
                raise ValueError(f"統一編號已存在: {data.vendor_code}")
        return await super().create(db, data)
```

### 何時不應該繼承 BaseService

| 條件 | 範例 | 說明 |
|------|------|------|
| **複雜業務邏輯** | DocumentService | 涉及行事曆整合、機關匹配 |
| **跨實體操作** | ProjectService | 需同時操作多個關聯表 |
| **外部服務整合** | CalendarService | 整合 Google Calendar |
| **策略模式** | DocumentImportService | 使用不同匯入策略 |

```python
# ✅ 推薦：複雜服務獨立實現
class DocumentService:
    def __init__(self, db: AsyncSession, auto_create_events: bool = True):
        self.db = db
        self.auto_create_events = auto_create_events
        self._agency_matcher = AgencyMatcher(db)  # 組合策略類
        self._calendar_integrator = CalendarIntegrator()  # 組合外部整合

    async def create_document(self, data: DocumentCreate) -> OfficialDocument:
        # 複雜業務邏輯
        matched_agencies = await self._agency_matcher.match(data.sender, data.receiver)
        doc = await self._create_in_db(data, matched_agencies)
        if self.auto_create_events:
            await self._calendar_integrator.create_event_for_document(doc)
        return doc
```

### 混合模式：組合而非繼承

對於有些基礎 CRUD 但也有複雜邏輯的情況，可以使用組合模式：

```python
class ProjectService:
    """承攬案件服務 - 組合 BaseService"""

    def __init__(self):
        # 使用組合而非繼承
        self._crud = BaseService(ContractProject, "承攬案件")

    async def get_by_id(self, db: AsyncSession, project_id: int):
        return await self._crud.get_by_id(db, project_id)

    async def create_project(self, db: AsyncSession, data: ProjectCreate):
        # 先執行基礎 CRUD
        project = await self._crud.create(db, data)
        # 再執行複雜業務邏輯
        await self._setup_project_associations(db, project)
        return project
```

---

## BaseService 提供的方法

| 方法 | 說明 | 參數 |
|------|------|------|
| `get_by_id` | 依 ID 取得單筆 | `db, entity_id` |
| `get_list` | 取得分頁列表 | `db, skip, limit, query` |
| `get_count` | 取得資料總數 | `db, query` |
| `get_paginated` | 取得分頁結果含總數 | `db, page, limit, query` |
| `create` | 建立新實體 | `db, data` |
| `update` | 更新實體 | `db, entity_id, data` |
| `delete` | 刪除實體 | `db, entity_id` |
| `exists` | 檢查是否存在 | `db, entity_id` |
| `get_by_field` | 依欄位值取得 | `db, field_name, field_value` |
| `bulk_delete` | 批次刪除 | `db, entity_ids` |

---

## 輔助工具類 (base/)

### QueryHelper

```python
from app.services.base import QueryHelper

helper = QueryHelper(PartnerVendor)
query = helper.apply_search(query, search, ['vendor_name', 'vendor_code'])
query = helper.apply_sorting(query, 'vendor_name', 'asc', 'vendor_name')
```

### DeleteCheckHelper

```python
from app.services.base import DeleteCheckHelper

# 檢查關聯表使用
can_delete, count = await DeleteCheckHelper.check_association_usage(
    db, project_vendor_association, 'vendor_id', vendor_id, 'project_id'
)

# 檢查多個外鍵使用
can_delete, count = await DeleteCheckHelper.check_multiple_usages(
    db, OfficialDocument,
    [('sender_agency_id', agency_id), ('receiver_agency_id', agency_id)]
)
```

### StatisticsHelper

```python
from app.services.base import StatisticsHelper

# 基本統計
basic_stats = await StatisticsHelper.get_basic_stats(db, PartnerVendor)

# 分組統計
grouped = await StatisticsHelper.get_grouped_stats(db, PartnerVendor, 'business_type')

# 平均值統計
avg_stats = await StatisticsHelper.get_average_stats(db, PartnerVendor, 'rating')
```

---

## 服務命名規範

| 類型 | 命名規則 | 範例 |
|------|---------|------|
| 實體服務 | `{Entity}Service` | `VendorService`, `AgencyService` |
| 匯入服務 | `{Entity}ImportService` | `DocumentImportService` |
| 匯出服務 | `{Entity}ExportService` | `DocumentExportService` |
| 整合服務 | `{External}IntegrationService` | `CalendarIntegrator` |
| 排程服務 | `{Function}Scheduler` | `ReminderScheduler` |

---

## 現有服務分類

### 繼承 BaseService 的服務

| 服務 | 實體 | 說明 |
|------|------|------|
| `VendorService` | PartnerVendor | 協力廠商 CRUD |
| `AgencyService` | GovernmentAgency | 機關 CRUD + 智慧匹配 |

### 獨立實現的服務

| 服務 | 說明 | 原因 |
|------|------|------|
| `DocumentService` | 公文管理 | 複雜業務邏輯、行事曆整合 |
| `ProjectService` | 承攬案件 | 跨實體操作 |
| `AdminService` | 管理員操作 | 多種管理功能 |
| `CalendarService` | 行事曆 | 外部 Google API 整合 |

---

## 向後相容

當從舊 API 遷移到 BaseService 時，保留向後相容方法並標記為 deprecated：

```python
async def get_vendor(self, db: AsyncSession, vendor_id: int):
    """
    @deprecated v2.0 (2026-01-20) 使用 get_by_id 代替
    移除計畫: v3.0 (2026-03-01)
    """
    return await self.get_by_id(db, vendor_id)
```

---

*最後更新: 2026-01-21*
