---
title: app.api.endpoints.tender_module.subscriptions
kg_entity_id: 38594
type: module
module_lines: 352
module_relations: 35
file_path: /app/app/api/endpoints/tender_module/subscriptions.py
created: 2026-08-03
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.subscriptions

## 概述
該模組包含了與標案訂閱、書籤以及廠商關注相關的API接口，用於管理用戶對標案和書籤的操作。

## 主要類別
無

## 公開函數
1. `list_subscriptions` - 列出用戶的所有標案訂閱。
2. `create_subscription` - 創建新的標案訂閱。
3. `update_subscription` - 更新已存在的標案訂閱信息。
4. `delete_subscription` - 刪除指定的標案訂閱。
5. `list_bookmarks` - 列出用戶的所有書籤。
6. `create_bookmark` - 創建新的書籤。
7. `update_bookmark` - 更新已存在的書籤信息。
8. `delete_bookmark` - 刪除指定的書籤。
9. `check_subscriptions` - 檢查用戶是否有訂閱特定標案。
10. `list_company_bookmarks` - 列出廠商的所有書籤。

## 依賴關係
- `app.schemas.common`
- `app.schemas.tender_admin`
- `app.db.database`
- `app.core.dependencies`
- `app.extended.models`
- `app.extended.models.tender`
- `app.services.tender.search`
- `app.services.user.alias`
- `app.services.tender.subscription_scheduler`
- `app.services.tender.business_recommendation`
