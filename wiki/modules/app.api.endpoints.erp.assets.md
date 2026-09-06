---
title: app.api.endpoints.erp.assets
kg_entity_id: 24065
type: module
module_lines: 349
module_relations: 29
file_path: /app/app/api/endpoints/erp/assets.py
created: 2026-08-04
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.assets

## 概述
此 Python 模組包含了多個與資產管理相關的 API 端點，主要用於處理資產的列表、創建、詳細信息獲取、更新和刪除等操作。這些端點僅支持 POST 方法。

## 主要類別
無

## 公開函數
1. `list_assets` - 列出所有資產。
2. `create_asset` - 創建新的資產記錄。
3. `get_asset_detail` - 根據資產編號獲取詳細信息。
4. `get_asset_detail_full` - 與 `get_asset_detail` 相似，但提供更多詳情。
5. `update_asset` - 更新現有資產的信息。
6. `delete_asset` - 刪除指定的資產記錄。
7. `get_assets_by_invoice` - 根據發票獲取相關資產。
8. `get_asset_stats` - 獲取資產統計信息。
9. `export_assets` - 导出資產數據。
10. `import_assets` - 寫入新的資產數據。

## 依賴關係
1. `app.core.dependencies`
2. `app.extended.models`
3. `app.services.erp.asset_service`
4. `app.schemas.erp.asset`
5. `app.schemas.erp.requests`
6. `app.schemas.common`
7. `app.services.ai.core.ai_config`
