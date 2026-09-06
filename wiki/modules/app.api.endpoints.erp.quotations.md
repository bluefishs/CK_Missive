---
title: app.api.endpoints.erp.quotations
kg_entity_id: 15516
type: module
module_lines: 530
module_relations: 41
file_path: /app/app/api/endpoints/erp/quotations.py
created: 2026-08-17
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.quotations

## 概述
該模組提供了與 ERP 系統中報價相關的 API 端點，支持創建、查詢和更新報價等操作。這些端點均為 POST 方法。

## 主要類別
無

## 公開函數
- `list_quotations`: 列出所有報價。
- `create_quotation`: 創建新的報價。
- `get_quotation_detail`: 根據 ID 查詢單個報價的詳細信息。
- `update_quotation`: 更新現有報價的信息。
- `delete_quotation`: 刪除指定的報價。
- `get_profit_summary`: 獲取報價總結，包括利潤摘要等數據。
- `get_client_options`: 獲取客戶選項。
- `get_profit_trend`: 獲取報價利潤趨勢。
- `export_quotations`: 导出報價数据。
- `export_quotations_excel`: 将报报价导出为 Excel 文件。

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.services.erp`
- `app.schemas.erp.quotation`
- `app.schemas.erp`
- `app.schemas.common`
- `app.core.auth_service`
- `app.core.rls_filter`
- `app.services.erp.quotation_legacy_import`
- `app.extended.models.erp`
