---
title: app.api.endpoints.taoyuan_dispatch.dispatch
kg_entity_id: 11234
type: module
module_lines: 551
module_relations: 30
file_path: /app/app/api/endpoints/taoyuan_dispatch/dispatch.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.taoyuan_dispatch.dispatch

## 概述
本模組提供了與桃園派工系統相關的 CRUD API，用於管理派工紀錄及其相關操作。

## 主要函數
- `get_dispatch_service`
- `list_contract_projects`
- `list_dispatch_orders`
- `download_dispatch_import_template`
- `import_dispatch_orders`
- `batch_relink_documents`
- `enrich_from_excel`
- `create_document_stubs`
- `get_next_dispatch_no`
- `create_dispatch_order`

## 依賴關係
- `app.extended.models`
- `app.schemas.taoyuan.dispatch`
- `app.services.taoyuan`
- `app.services.taoyuan.dispatch_enrichment_service`
- `app.services.taoyuan.dispatch_import_service`
- `app.services.taoyuan.dispatch_response_formatter`
- `app.utils.doc_helpers`

## 包含端點
- `/dispatch/list` - 派工紀錄列表
- `/dispatch/import-template` - 下載匯入範本
- `/dispatch/import` - 匯入派工紀錄
- `/dispatch/batch-relink-documents` - 批次重新關聯公文
- `/dispatch/enrich-from-excel` - 從主表 Excel 增強匯入（價金+公文）
- `/dispatch/create-document-stubs` - 從原始文號反建公文 Stub + 自動關聯
```

請注意，`get_next_dispatch_no` 和 `create_dispatch_order` 這兩個函數在描述中沒有對應的端點，您可能需要根據實際情況進行調整。
