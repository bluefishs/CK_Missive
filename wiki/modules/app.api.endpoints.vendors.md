---
title: app.api.endpoints.vendors
kg_entity_id: 10942
type: module
module_lines: 256
module_relations: 19
file_path: /app/app/api/endpoints/vendors.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.vendors

## 概述
此 Python 模組實現了協力廠商管理的 API 端點，包括協力廠商的基本信息、財務概況等操作。該模組使用統一回應格式和異常處理機制來確保接口的一致性和可靠性。

## 公開函數
1. `list_vendors` - 列出所有協力廠商。
2. `create_vendor` - 創建新的協力廠商。
3. `get_vendor_detail` - 計算特定協力廠商的詳細信息。
4. `update_vendor` - 更新現有協力廠商的信息。
5. `delete_vendor` - 刪除指定的協力廠商。
6. `get_vendor_statistics` - 獲取協力廠商的統計數據。
7. `list_vendors_legacy` - 舊版本的協力廠商列表。
8. `get_vendor_financial_summary` - 獲取協力廠商財務概況。

## 依賴關係
1. `app.core.dependencies`
2. `app.core.exceptions`
3. `app.extended.models`
4. `app.schemas.common`
5. `app.schemas.vendor`
6. `app.schemas.erp.vendor_financial`
7. `app.services.vendor.core`
