# API 端點組織指南

## 概述

本目錄包含所有 FastAPI 路由端點定義。遵循 POST-only 資安機制設計。

## 端點檔案結構

### 核心業務端點

| 檔案/目錄 | 說明 | 路由前綴 |
|-----------|------|----------|
| `documents/` | 公文管理 (模組化: crud, list, stats, export, import_, audit) | `/api/documents-enhanced` |
| `projects/` | 專案管理 (模組化) | `/api/projects` |
| `agencies.py` | 機關管理 | `/api/agencies` |
| `vendors.py` | 廠商管理 | `/api/vendors` |
| `certifications.py` | 證照管理 | `/api/certifications` |

### 桃園派工

| 檔案/目錄 | 說明 | 路由前綴 |
|-----------|------|----------|
| `taoyuan_dispatch/` | 派工管理 (dispatch, projects, payments, attachments, workflow) | `/api/taoyuan-dispatch` |

### 人員與關聯

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `users.py` | 使用者管理 | `/api/users` |
| `user_management.py` | 使用者進階管理 | `/api/user-management` |
| `project_staff.py` | 專案人員 | `/api/project-staff` |
| `project_vendors.py` | 專案廠商 | `/api/project-vendors` |
| `project_agency_contacts.py` | 專案機關聯絡人 | `/api/project-agency-contacts` |

### 行事曆與通知

| 檔案/目錄 | 說明 | 路由前綴 |
|-----------|------|----------|
| `document_calendar/` | 文件行事曆 (模組化) | `/api/document-calendar` |
| `reminders/` | 提醒管理 (模組化) | `/api/reminder-management` |
| `system_notifications.py` | 系統通知 | `/api/notifications` |
| `project_notifications.py` | 專案通知 | `/api/project-notifications` |

### AI 功能

| 檔案/目錄 | 說明 | 路由前綴 |
|-----------|------|----------|
| `ai/` | AI 功能 (agent, rag, graph, embedding, synonyms 等) | `/api/ai` |

### 系統管理

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `admin.py` | 管理員功能 | `/api/admin` |
| `auth/` | 認證授權 (oauth, mfa) | `/api/auth` |
| `dashboard.py` | 儀表板統計 | `/api/dashboard` |
| `site_management.py` | 站台設定 | `/api/site-management` |
| `secure_site_management/` | 安全站台管理 | `/api/secure-site-management` |
| `deployment.py` | 部署管理 | `/api/deployment` |
| `backup.py` | 備份管理 | `/api/backup` |
| `knowledge_base.py` | 知識庫瀏覽器 | `/api/knowledge-base` |

### 系統監控

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `health.py` | 健康檢查 | `/api/health` |
| `system_monitoring.py` | 系統監控 | `/api/system-monitoring` |

### 匯入匯出與文件

| 檔案/目錄 | 說明 | 路由前綴 |
|-----------|------|----------|
| `csv_import.py` | CSV 匯入 | `/api/csv-import` |
| `files/` | 檔案管理 (upload, storage, management) | `/api/files` |
| `document_numbers.py` | 文號管理 | `/api/document-numbers` |

### 其他

| 檔案 | 說明 | 路由前綴 |
|------|------|----------|
| `public.py` | 公開端點 | `/api/public` |
| `debug.py` | 除錯端點 (開發用) | `/api/debug` |
| `utils/` | 共用工具 | — |

## 端點設計原則

### 1. POST-only 資安機制

所有資料操作必須使用 POST 方法：

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

```python
from app.schemas.common import SuccessResponse, PaginatedResponse

@router.post("/get/{id}")
async def get_item(id: int) -> SuccessResponse[ItemSchema]:
    ...

@router.post("/list")
async def list_items() -> PaginatedResponse[ItemSchema]:
    ...
```

### 3. 服務層委派

端點應薄且只負責：參數驗證、權限檢查、呼叫服務層、回應封裝。

### 4. 錯誤處理

```python
from app.core.exceptions import NotFoundException, ValidationError

if not item:
    raise NotFoundException("項目不存在")
```

## 命名慣例

- 檔案名：`snake_case.py`
- 路由前綴：`kebab-case`
- 函數名：`snake_case`
- 類別名：`PascalCase`
