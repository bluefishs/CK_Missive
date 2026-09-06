---
title: app.api.endpoints.erp.operational
kg_entity_id: 25824
type: module
module_lines: 175
module_relations: 19
file_path: /app/app/api/endpoints/erp/operational.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.operational

## 概述
此模組提供了營運帳目相關的 API 端點，包括帳目的 CRUD（Create, Read, Update, Delete）操作、費用的 CRUD 操作以及統計信息獲取。

## 主要類別
無

## 公開函數
- `list_accounts`
- `create_account`
- `get_account_detail`
- `update_account`
- `delete_account`
- `get_stats`
- `list_expenses`
- `create_expense`
- `approve_expense`
- `reject_expense`

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.schemas.erp.requests`
- `app.schemas.erp.operational`
- `app.services.erp.operational_service`
