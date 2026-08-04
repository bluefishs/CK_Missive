---
title: app.api.endpoints.erp.assets
kg_entity_id: 24065
type: module
module_lines: 347
module_relations: 29
file_path: /app/app/api/endpoints/erp/assets.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.assets

## 概述
此 Python 模組包含一系列與資產管理相關的 API 端點，這些端點允許用戶進行資產列表查詢、創建新資產、獲取單個資產詳情、更新資產信息以及刪除資產等操作。所有功能均通過 POST 方法訪問。

## 主要類別
無

## 公開函數
- `list_assets`
- `create_asset`
- `get_asset_detail`
- `get_asset_detail_full`
- `update_asset`
- `delete_asset`
- `get_assets_by_invoice`
- `get_asset_stats`
- `export_assets`
- `import_assets`

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.services.erp.asset_service`
- `app.schemas.erp.asset`
- `app.schemas.erp.requests`
- `app.schemas.common`
- `app.services.ai.core.ai_config`
