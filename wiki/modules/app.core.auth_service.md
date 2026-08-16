---
title: app.core.auth_service
kg_entity_id: 11336
type: module
module_lines: 791
module_relations: 22
file_path: /app/app/core/auth_service.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.auth_service

## 概述
認證服務負責管理 JWT 令牌、Google OAuth 驗證以及權限檢查。此模組是應用程序中用戶身份驗證的核心部分。

## 主要類別
- **AuthService**: 負責認證相關的各種操作和邏輯。

## 公開函數
無公開函數，主要通過方法進行認證和權限管理。

## 依賴關係
- `app.core.config`: 配置信息。
- `app.core.csrf`: CSRF保護機制。
- `app.core.dependencies`: 獲取依賴項。
- `app.core.domain_whitelist`: 網域白名單檢查。
- `app.core.password_policy`: 密碼策略。
- `app.extended.models`: 扩展模型。
- `app.schemas.auth`: 認證相關的模式。
- `app.services.audit`: 审計服務。

## 版本歷史
### v2.1 - 2026-02-07
- 新增 httpOnly cookie 認證支援。
- 新增 `set_auth_cookies` / `clear_auth_cookies` 方法。
- 保留 Authorization header 向後相容（過渡期）。

### v2.0 - 2026-01-09
- 簡化為僅 Google OAuth 認證。
- 新增網域白名單檢查。
- 新增新帳號審核機制。
```

此Markdown文檔概括了`app.core.auth_service`模組的結構、依賴關係以及版本歷史。
