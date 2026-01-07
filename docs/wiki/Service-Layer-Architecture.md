# 服務層架構 (Service Layer Architecture)

> 版本：1.0.0 | 更新日期：2026-01-06

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
| `ReminderService` | `reminder_service.py` | 提醒服務 |
| `NotificationService` | `notification_service.py` | 通知服務 |

### 匯入匯出服務

| 類別 | 檔案 | 說明 |
|------|------|------|
| `DocumentImportService` | `document_import_service.py` | 公文匯入 |
| `DocumentExportService` | `document_export_service.py` | 公文匯出 |
| `DocumentCSVProcessor` | `csv_processor.py` | CSV 處理 |

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
