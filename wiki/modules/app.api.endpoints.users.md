---
title: app.api.endpoints.users
kg_entity_id: 10932
type: module
module_lines: 412
module_relations: 24
file_path: /app/app/api/endpoints/users.py
created: 2026-08-17
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.users

## 概述
此模組定義了使用者管理 API 端點，負責處理與使用者相關的所有操作，包括獲取、創建、更新和刪除使用者信息。該模組使用統一的回應格式和錯誤處理機制，並通過 UserRepository 進行資料存取。

## 主要類別
- 無

## 公開函數
1. `get_password_hash`
2. `get_user_repository`
3. `get_users`
4. `get_departments`
5. `get_user`
6. `create_user`
7. `update_user`
8. `delete_user`
9. `update_user_status`

## 依賴關係
- `app.core.auth_service`
- `app.core.dependencies`
- `app.core.exceptions`
- `app.db.database`
- `app.extended.models`
- `app.repositories.user_repository`
- `app.schemas.common`
- `app.schemas.user`
