---
title: app.core.dependencies
kg_entity_id: 11456
type: module
module_lines: 309
module_relations: 22
file_path: /app/app/core/dependencies.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.dependencies

## 概述
`app.core.dependencies` 是一個依賴注入模組，為 FastAPI 端點提供統一的服務注入機制。通過此模組，可以方便地獲取不同類型的服務並進行方法調用。

## 主要函數
- `get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]`
- `get_project_service() -> ProjectService`
- `get_agency_service() -> AgencyService`
- `get_pagination(skip: int = 0, limit: int = 100) -> PaginationParams`
- `get_query_params(query: str | None = Query(None)) -> QueryParams`
- `require_auth(user_id: UUID) -> Callable[[AsyncSession], User]`
- `optional_auth(user_id: UUID | None = None) -> Callable[[AsyncSession], Optional[User]]`
- `require_admin() -> Callable[[AsyncSession], bool]`
- `require_permission(permission_name: str) -> Callable[[AsyncSession], bool]`
- `is_admin_user() -> Callable[[AsyncSession], bool]`

## 依賴關係
- `app.api.endpoints.auth`
- `app.core.auth_service`
- `app.core.config`
- `app.core.exceptions`
- `app.db.database`
- `app.extended.models`
- `app.schemas.common`
- `app.services.agency_service`
- `app.services.project_service`

### 工廠模式（所有服務統一使用）
Service 在建構時接收 db session，方法簽名更簡潔。

```python
def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
    def _get_service(db: AsyncSession = Depends(get_async_db)) -> T:
        return service_class(db)
    return _get_service

# 使用範例
service = get_service(ProjectService)()
```

### 具體函數說明
- `get_project_service()`: 返回一個 ProjectService 的實例。
- `get_agency_service()`: 返回一個 AgencyService 的實例。
- `get_pagination(skip: int = 0, limit: int = 100) -> PaginationParams`: 返回分頁參數。
- `get_query_params(query: str | None = Query(None)) -> QueryParams`: 返回查詢參數。
- `require_auth(user_id: UUID) -> Callable[[AsyncSession], User]`: 確認
