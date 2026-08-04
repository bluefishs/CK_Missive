---
title: app.api.endpoints.auth.oauth
kg_entity_id: 11056
type: module
module_lines: 332
module_relations: 26
file_path: /app/app/api/endpoints/auth/oauth.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.auth.oauth

## 概述
此模組實現了 OAuth 登入端點和相關功能，包括基本的登入、Google OAuth 登入以及用戶註冊。它還支援雙因素認證（MFA），在使用者成功登入後會檢查 MFA 狀態並返回相應信息。

## 公開函數
- `login_for_access_token`
- `google_oauth_login`
- `register_user`

## 依賴關係
- `app.core.auth_service`
- `app.core.config`
- `app.core.domain_whitelist`
- `app.core.mfa_service`
- `app.core.rate_limiter`
- `app.db.database`
- `app.extended.models`
- `app.schemas.auth`
- `app.services.audit`

此模組主要用於處理認證相關的業務邏輯，包括用戶登入、Google OAuth 登入以及用戶註冊。此外，它還支援雙因素認證（MFA），在使用者成功登入後會檢查 MFA 狀態並返回相應信息。

### 主要函數細節

#### `login_for_access_token`
- **功能**: 生成存取令牌以供進一步的 API 調用。
- **依賴**: `app.core.auth_service`, `app.core.config`, `app.core.mfa_service`, `app.core.rate_limiter`, `app.db.database`, `app.extended.models`, `app.schemas.auth`, `app.services.audit`。

#### `google_oauth_login`
- **功能**: 通過 Google OAuth 獲取用戶信息並進行登入。
- **依賴**: `app.core.config`, `app.core.mfa_service`, `app.core.rate_limiter`, `app.db.database`, `app.extended.models`, `app.schemas.auth`。

#### `register_user`
- **功能**: 處理新用戶的註冊流程，包括驗證和存儲用戶信息。
- **依賴**: `app.core.config`, `app.core.mfa_service`, `app.core.rate_limiter`, `app.db.database`, `app.extended.models`, `app.schemas.auth`。

## 版本資訊
v3.2.0 - 2026-02-08
- 新增 MFA 雙因素認證支援。
- 登入成功後檢查 MFA 狀態，若啟用則返回 mfa_required +
