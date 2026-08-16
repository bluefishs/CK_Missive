---
title: app.api.endpoints.user_permissions
kg_entity_id: 20820
type: module
module_lines: 292
module_relations: 21
file_path: /app/app/api/endpoints/user_permissions.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.user_permissions

## 概述
此模組提供了使用者權限與會話管理的 API 端點，用於處理用戶權限的獲取、更新和撤銷等操作。

## 公開函數
1. `get_user_repository` - 從存儲庫獲取用戶信息。
2. `get_user_permissions` - 設計用於獲取用戶權限的信息。
3. `update_user_permissions` - 更新用戶的權限設置。
4. `check_permission` - 檢查特定用戶是否具有某項權限。
5. `get_user_sessions` - 獲取用戶的所有會話信息。
6. `revoke_user_session` - 撤銷用戶的特定會話。
7. `admin_unlock_user` - 行政管理員解鎖被封禁的用戶。
8. `admin_bind_line` - 將用戶綁定到 LINE 帳號。
9. `admin_unbind_line` - 解除用戶與 LINE 帳號的綁定。

## 依賴關係
1. `app.api.endpoints.auth`
2. `app.core.auth_service`
3. `app.core.dependencies`
4. `app.extended.models`
5. `app.repositories.user_repository`
6. `app.schemas.admin`
7. `app.schemas.auth`
8. `app.services.audit`
```

請根據實際情況調整函數和依賴關係的描述，以確保其準確無誤。
