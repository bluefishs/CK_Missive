---
title: app.api.endpoints.erp.quotations
kg_entity_id: 15516
type: module
module_lines: 374
module_relations: 28
file_path: /app/app/api/endpoints/erp/quotations.py
created: 2026-08-17
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.quotations

## 概述
此模組提供了與 ERP 系統中的報價相關的 API 端點，包括查詢、創建、更新和刪除報價等操作。此外還提供了一些報利潤總結和趨勢分析的功能。

## 主要類別
無

## 公開函數
- `list_quotations`: 列出所有報價。
- `create_quotation`: 創建新的報價。
- `get_quotation_detail`: 獲取特定報價的詳細信息。
- `update_quotation`: 更新現有報價的信息。
- `delete_quotation`: 刪除指定的報價。
- `get_profit_summary`: 獲取利潤總結。
- `get_profit_trend`: 獲取利潤趨勢分析。
- `export_quotations`: 导出報價数据。
- `generate_case_code`: 生成案例代码。
- `export_quotations_excel`: 导出报报价数据为Excel文件。

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.extended.models.erp`
- `app.schemas.erp`
- `app.services.erp`
- `app.services.erp.quotation_document`
- `app.services.erp.quotation_legacy_import`
- `app.services.erp.signed_quotation_import`
