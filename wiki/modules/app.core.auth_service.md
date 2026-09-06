---
title: app.core.auth_service
kg_entity_id: 11336
type: module
module_lines: 795
module_relations: 22
file_path: /app/app/core/auth_service.py
created: 2026-08-17
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.auth_service

## 概述
認證服務負責管理 JWT 令牌、Google OAuth 驗證和權限檢查。此模組支持多種認證方式，並提供了一系列工具方法來確保用戶的安全性和系統的穩定性。

## 主要類別
- **AuthService**: 認證服務的核心類別

## 公開函數
無公開函數

## 依賴關係
- app.core.config: 系統配置管理
- app.core.csrf: 跨站請求 forgery (CSRF) 防護機制
- app.core.dependencies: 函數和方法的依赖项
- app.core.domain_whitelist: 網域白名單檢查
- app.core.password_policy: 密碼策略驗證
- app.extended.models: 延伸模型定義
- app.schemas.auth: 認證相關模式
- app.services.audit: 审核服務

---

## 版本歷史
### v2.1 - 2026-02-07
- 新增 httpOnly cookie 認證支援
- 新增 set_auth_cookies / clear_auth_cookies 方法
- 保留 Authorization header 向後相容（過渡期）

### v2.0 - 2026-01-09
- 簡化為僅 Google OAuth 認證
- 新增網域白名單檢查
- 新增新帳號審核機制
```

此Markdown文件概括了`app.core.auth_service`模組的結構、依賴關係和版本歷史，提供了清晰且簡潔的文檔信息。
