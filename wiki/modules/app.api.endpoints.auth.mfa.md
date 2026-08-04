---
title: app.api.endpoints.auth.mfa
kg_entity_id: 11050
type: module
module_lines: 327
module_relations: 24
file_path: /app/app/api/endpoints/auth/mfa.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.auth.mfa

## 概述
此模組提供多因素認證 (MFA) 的 API 端點，包括 TOTP 二步驗證的設置、驗證、停用等功能。

## 主要函數
- `mfa_setup`: 開始 MFA 設定（生成 secret + QR code）
- `mfa_verify`: 驗證 TOTP code 并啟用 MFA
- `mfa_disable`: 停用 MFA（需密碼驗證）
- `mfa_validate`: 登入時驗證 MFA code
- `mfa_status`: 查詢 MFA 狀態

## 依賴關係
- `app.core.auth_service`
- `app.core.config`
- `app.core.mfa_service`
- `app.core.rate_limiter`
- `app.db.database`
- `app.extended.models`
- `app.repositories.user_repository`
- `app.schemas.auth`
- `app.services.audit`
```

這樣就生成了模組的 Markdown 文檔，包含了概述、主要函數和依賴關係。
