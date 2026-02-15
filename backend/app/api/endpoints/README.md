# API 端點組織指南

## 概述

本目錄包含所有 FastAPI 路由端點定義。遵循 POST-only 資安機制設計。

## 端點檔案結構

### 核心業務端點

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `documents_enhanced.py` | 增強版公文管理（主要使用） | `/api/documents-enhanced` |
| `documents.py` | 基礎公文端點（已簡化） | `/api/documents` |
| `projects.py` | 專案管理 | `/api/projects` |
| `agencies.py` | 機關管理 | `/api/agencies` |
| `vendors.py` | 廠商管理 | `/api/vendors` |

### 行事曆與通知

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `document_calendar.py` | 文件行事曆 | `/api/document-calendar` |
| `reminders/` | 提醒管理 (模組化) | `/api/reminder-management` |
| `system_notifications.py` | 系統通知 | `/api/notifications` |
| `project_notifications.py` | 專案通知 | `/api/project-notifications` |

### 系統管理

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `admin.py` | 管理員功能 | `/api/admin` |
| `auth.py` | 認證授權 | `/api/auth` |
| `users.py` | 使用者管理 | `/api/users` |
| `user_management.py` | 使用者進階管理 | `/api/user-management` |

### 系統監控

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `health.py` | 健康檢查 | `/api/health` |
| `system_health.py` | 系統健康狀態 | `/api/system-health` |
| `system_monitoring.py` | 系統監控 | `/api/system-monitoring` |

### 匯入匯出

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `csv_import.py` | CSV 匯入 | `/api/csv-import` |
| `files.py` | 檔案管理 | `/api/files` |

## 端點設計原則

### 1. POST-only 資安機制

所有資料變更操作必須使用 POST 方法：

```python
# ✅ 正確
@router.post("/list")
async def list_documents(request: DocumentListRequest):
    ...

# ❌ 避免
@router.get("/")
async def get_documents(skip: int = 0, limit: int = 100):
    ...
```

### 2. 統一回應格式

使用 `app.schemas.common` 中的回應結構：

```python
from app.schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    ErrorResponse,
    DeleteResponse
)

# 單一資料回應
@router.post("/get/{id}")
async def get_item(id: int) -> SuccessResponse[ItemSchema]:
    ...

# 列表回應
@router.post("/list")
async def list_items() -> PaginatedResponse[ItemSchema]:
    ...
```

### 3. 服務層委派

端點應該薄且只負責：
- 參數驗證
- 權限檢查
- 呼叫服務層
- 回應封裝

```python
@router.post("/create")
async def create_item(
    request: CreateRequest,
    db: AsyncSession = Depends(get_async_db)
) -> SuccessResponse[ItemSchema]:
    service = ItemService(db)
    result = await service.create(request)
    return SuccessResponse(data=result)
```

### 4. 錯誤處理

使用統一的異常類別：

```python
from app.core.exceptions import (
    NotFoundException,
    ValidationError,
    ConflictError
)

# 會自動轉換為適當的 HTTP 回應
if not item:
    raise NotFoundException("項目不存在")
```

## 重構建議

### 過長檔案拆分

當檔案超過 500 行時，考慮拆分：

```
documents_enhanced.py (>500 行)
├── documents_enhanced/
│   ├── __init__.py       # 匯出 router
│   ├── list_routes.py    # 列表相關端點
│   ├── crud_routes.py    # CRUD 端點
│   ├── import_routes.py  # 匯入端點
│   └── export_routes.py  # 匯出端點
```

### 子路由組織

```python
# documents_enhanced/__init__.py
from fastapi import APIRouter
from .list_routes import router as list_router
from .crud_routes import router as crud_router

router = APIRouter()
router.include_router(list_router, tags=["documents-list"])
router.include_router(crud_router, tags=["documents-crud"])
```

## 命名慣例

- 檔案名：`snake_case.py`
- 路由前綴：`kebab-case`
- 函數名：`snake_case`
- 類別名：`PascalCase`

## 版本歷史

- 2026-01-09: 建立組織指南
- 2026-01-08: POST-only 機制實施
