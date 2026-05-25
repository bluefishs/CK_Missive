# 服務層架構 (Service Layer Architecture)

> 版本：2.0.0 | 更新日期：2026-01-08

## 概述

CK_Missive 系統採用分層架構，服務層負責封裝業務邏輯，與資料存取層和 API 層分離。

## 架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                     API Endpoints                            │
│   /api/documents  /api/projects  /api/agencies  ...         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     Services Layer                           │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ DocumentService │  │ProjectService│  │ AgencyService  │  │
│  └─────────────────┘  └──────────────┘  └────────────────┘  │
│           │                   │                  │           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    UnitOfWork                           │ │
│  │   統一管理交易與服務實例                                │ │
│  └────────────────────────────────────────────────────────┘ │
│           │                   │                  │           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    Strategies                           │ │
│  │   AgencyMatcher  │  ProjectMatcher  │  ...              │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     SQLAlchemy ORM                           │
│                     (AsyncSession)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## ImportBaseService 繼承架構

### 類別繼承圖

```
ImportBaseService (抽象基類)
│   ├── clean_string()          # 字串清理
│   ├── parse_date()            # 日期解析
│   ├── validate_doc_type()     # 公文類型驗證
│   ├── validate_category()     # 類別驗證
│   ├── generate_auto_serial()  # 流水號生成
│   ├── match_agency()          # 智慧機關匹配
│   ├── match_project()         # 智慧案件匹配
│   └── [abstract] import_from_file()
│   └── [abstract] process_row()
│
├── ExcelImportService
│   └── 手動公文匯入（支援新增/更新）
│
└── DocumentImportService
    └── 電子公文 CSV 匯入
```

### 使用範例

```python
from app.services.base.import_base import ImportBaseService
from app.services.base.response import ImportResult, ImportRowResult

class NewImportService(ImportBaseService):
    async def import_from_file(self, file_content: bytes, filename: str) -> ImportResult:
        # 使用繼承的方法
        self.reset_serial_counters()

        for row in data:
            clean_value = self.clean_string(row['field'])
            doc_type = self.validate_doc_type(row['doc_type'])
            agency_id = await self.match_agency(row['agency'])

        return ImportResult(success=True, filename=filename, ...)

    async def process_row(self, row_num: int, row_data: dict) -> ImportRowResult:
        return ImportRowResult(row=row_num, status='inserted', message='成功')
```

---

## UnitOfWork 模式

### 設計目的

1. **交易管理**：確保多個操作在同一交易中執行
2. **服務注入**：延遲初始化服務實例
3. **資源管理**：自動處理 session 生命週期

### 實作位置

`backend/app/services/base/unit_of_work.py`

### 使用方式

```python
from app.services import UnitOfWork, get_uow

# 方式一：使用 get_uow() 工廠函數
async with get_uow() as uow:
    # 取得公文
    document = await uow.documents.get_document_by_id(doc_id)

    # 更新公文
    document.status = "已處理"

    # 提交交易
    await uow.commit()

# 方式二：依賴注入
async def my_endpoint(uow: UnitOfWork = Depends(get_uow)):
    doc = await uow.documents.create_document(data)
    await uow.commit()
    return doc
```

### UnitOfWork 屬性

| 屬性 | 服務類別 | 說明 |
|------|----------|------|
| `documents` | DocumentService | 公文服務 |
| `projects` | ProjectService | 案件服務 |
| `agencies` | AgencyService | 機關服務 |
| `vendors` | VendorService | 廠商服務 |
| `calendar` | DocumentCalendarService | 行事曆服務 |

---

## 策略模式 (Strategy Pattern)

### 設計目的

1. **可重用性**：將通用邏輯抽取為獨立策略類別
2. **可測試性**：策略類別可獨立測試
3. **可擴展性**：新增策略不影響現有程式碼

### 實作位置

`backend/app/services/strategies/`

### AgencyMatcher (機關名稱匹配器)

智慧機關名稱匹配，支援多層級匹配策略：

```python
from app.services.strategies import AgencyMatcher

matcher = AgencyMatcher(db_session)

# 匹配或建立機關
agency_id = await matcher.match_or_create("台北市政府")

# 僅匹配（不自動建立）
agency_id = await matcher.match_only("台北市政府")

# 批次匹配
results = await matcher.batch_match_or_create([
    "台北市政府",
    "新北市政府",
    "桃園市政府"
])
```

#### 匹配策略順序

1. **精確匹配** `agency_name`
2. **精確匹配** `agency_short_name` (簡稱)
3. **模糊匹配** (包含關係)
4. **自動新增** (若啟用)

### ProjectMatcher (案件名稱匹配器)

```python
from app.services.strategies import ProjectMatcher

matcher = ProjectMatcher(db_session)

# 匹配或建立案件
project_id = await matcher.match_or_create("公共工程案")
```

---

## N+1 查詢優化

### 問題描述

N+1 查詢問題：查詢 N 筆資料時，對每筆資料的關聯查詢導致 N+1 次資料庫請求。

### 解決方案

使用 SQLAlchemy 的 `selectinload` 預載入關聯資料：

```python
from sqlalchemy.orm import selectinload, joinedload

async def get_documents(self, include_relations: bool = True):
    query = select(Document)

    if include_relations:
        query = query.options(
            selectinload(Document.contract_project),
            selectinload(Document.sender_agency),
            selectinload(Document.receiver_agency),
        )

    result = await self.db.execute(query)
    return result.scalars().all()
```

### selectinload vs joinedload

| 策略 | SQL 行為 | 適用場景 |
|------|----------|----------|
| `selectinload` | 分批 SELECT IN | 一對多關聯 |
| `joinedload` | JOIN 單次查詢 | 一對一/多對一 |

---

## 快取策略

### 快取裝飾器

`backend/app/core/cache_manager.py`

```python
from app.core.cache_manager import cache_dropdown_data, cache_statistics

# 下拉選單資料快取 (TTL: 5 分鐘)
@cache_dropdown_data(ttl=300)
async def get_agency_options():
    ...

# 統計資料快取 (TTL: 1 分鐘)
@cache_statistics(ttl=60)
async def get_document_statistics():
    ...
```

### 快取失效

```python
from app.core.cache_manager import invalidate_cache

# 建立/更新資料後清除快取
async def create_agency(self, data):
    agency = await self._create(data)
    invalidate_cache('dropdown')  # 清除下拉選單快取
    return agency
```

---

## 服務類別清單

### 核心業務服務

| 類別 | 檔案 | 說明 |
|------|------|------|
| `DocumentService` | `document_service.py` | 公文 CRUD |
| `ProjectService` | `project_service.py` | 案件管理 |
| `AgencyService` | `agency_service.py` | 機關管理 |
| `VendorService` | `vendor_service.py` | 廠商管理 |

### 關聯管理服務

| 類別 | 檔案 | 說明 |
|------|------|------|
| `ProjectAgencyContactService` | `project_agency_contact_service.py` | 案件聯絡人 |

### 行事曆與提醒服務

| 類別 | 檔案 | 說明 |
|------|------|------|
| `DocumentCalendarService` | `document_calendar_service.py` | 行事曆事件 |
| `DocumentCalendarIntegrator` | `document_calendar_integrator.py` | 公文→日曆整合 |
| `CalendarEventAutoBuilder` | `calendar/event_auto_builder.py` | **事件自動建立器** |
| `ReminderService` | `reminder_service.py` | 提醒服務 |
| `ReminderScheduler` | `reminder_scheduler.py` | **提醒排程器** |
| `NotificationService` | `notification_service.py` | 通知服務 |

### 匯入匯出服務

| 類別 | 檔案 | 說明 |
|------|------|------|
| `ImportBaseService` | `base/import_base.py` | 匯入服務基類 (抽象) |
| `DocumentImportService` | `document_import_service.py` | CSV 公文匯入 (繼承 ImportBaseService) |
| `ExcelImportService` | `excel_import_service.py` | Excel 公文匯入 (繼承 ImportBaseService) |
| `DocumentExportService` | `document_export_service.py` | 公文匯出 |
| `DocumentCSVProcessor` | `csv_processor.py` | CSV 處理 |

### 統一回應結構

| 類別 | 檔案 | 說明 |
|------|------|------|
| `ServiceResponse` | `base/response.py` | 統一服務回應結構 |
| `ImportResult` | `base/response.py` | 匯入結果結構 |
| `ImportRowResult` | `base/response.py` | 單筆匯入結果 |

### 共用驗證器

| 類別 | 檔案 | 說明 |
|------|------|------|
| `DocumentValidators` | `base/validators.py` | 公文資料驗證 |
| `StringCleaners` | `base/validators.py` | 字串清理工具 |
| `DateParsers` | `base/validators.py` | 日期解析工具 |

---

## 最佳實踐

### 1. 使用 UnitOfWork 管理交易

```python
# ✅ 推薦
async with get_uow() as uow:
    await uow.documents.create_document(data)
    await uow.commit()

# ❌ 避免
db = await get_db()
service = DocumentService(db)
await service.create_document(data)
await db.commit()
```

### 2. 使用策略類別處理匹配邏輯

```python
# ✅ 推薦
matcher = AgencyMatcher(db)
agency_id = await matcher.match_or_create(name)

# ❌ 避免：在服務類別中重複實作匹配邏輯
```

### 3. 預載入關聯資料

```python
# ✅ 推薦
query = select(Document).options(
    selectinload(Document.contract_project)
)

# ❌ 避免
for doc in documents:
    print(doc.contract_project.name)  # N+1 查詢
```

### 4. 使用快取減少資料庫查詢

```python
# ✅ 推薦：靜態資料使用快取
@cache_dropdown_data(ttl=300)
async def get_status_options():
    ...

# ❌ 避免：頻繁變動的資料使用快取
```

---

## 相關文件

- [CODEWIKI 主頁](./CODEWIKI.md)
- [資料庫結構](./Database-Models.md)
- [後端 API 概覽](./Backend-API-Overview.md)
- [統一開發規範總綱](../DEVELOPMENT_STANDARDS.md)
- [錯誤處理指南](../ERROR_HANDLING_GUIDE.md)
