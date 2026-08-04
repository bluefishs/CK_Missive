---
title: app.api.endpoints.tender_module.subscriptions
kg_entity_id: 38594
type: module
module_lines: 356
module_relations: 36
file_path: /app/app/api/endpoints/tender_module/subscriptions.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.tender_module.subscriptions

## 概述
此模塊提供了一組 API 結合功能，用於管理標案訂閱和書籤。這些 API 包括創建、更新和刪除標案訂閱以及書籤，並支持查詢相關信息。

## 主要類別
- `KeywordRulesRequest`

## 公開函數
- `list_subscriptions`
- `create_subscription`
- `update_subscription`
- `delete_subscription`
- `list_bookmarks`
- `create_bookmark`
- `update_bookmark`
- `delete_bookmark`
- `check_subscriptions`
- `list_company_bookmarks`

## 依賴關係
- `app.core.dependencies`
- `app.db.database`
- `app.extended.models`
- `app.schemas.common`
- `app.extended.models.tender`
- `app.core.domain_events`
- `app.core.event_bus`
- `app.schemas.tender_admin`
- `app.services.user.alias`
- `app.services.tender.business_recommendation`
