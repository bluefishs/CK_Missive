---
title: app.api.endpoints.users
kg_entity_id: 10932
type: module
module_lines: 354
module_relations: 22
file_path: /app/app/api/endpoints/users.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.users

## 概述
此 Python 模組提供了使用者管理 API 端點，包括獲取、創建、更新和刪除使用者的功能。該模組遵循 Repository Pattern，通過 UserRepository 進行資料存取，並使用統一的回應格式和錯誤處理機制。

## 主要類別
- 無

## 公開函數
1. `get_password_hash`: 對密碼進行哈希加密。
2. `get_user_repository`: 取得使用者 Repository 以執行資料庫操作。
3. `get_users`: 獲取所有使用者列表。
4. `get_departments`: 獲取所有部門列表（可能為誤置或未使用函數）。
5. `get_user`: 根據 ID 獲取特定使用者信息。
6. `create_user`: 創建新的使用者帳戶。
7. `update_user`: 更新現有使用者的信息。
8. `delete_user`: 刪除指定的使用者帳戶。
9. `update_user_status`: 更新使用者狀態。

## 依賴關係
1. `app.core.auth_service`
2. `app.core.dependencies`
3. `app.core.exceptions`
4. `app.db.database`
5. `app.extended.models`
6. `app.repositories.user_repository`
7. `app.schemas.common`
8. `app.schemas.user`
```

此 Markdown 文檔概括了模組的主要內容和結構，包括其功能、依賴關係等信息。
