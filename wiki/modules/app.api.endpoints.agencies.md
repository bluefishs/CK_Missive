---
title: app.api.endpoints.agencies
kg_entity_id: 10778
type: module
module_lines: 380
module_relations: 22
file_path: /app/app/api/endpoints/agencies.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.agencies

## 概述
此模組提供機關單位管理的 API 端點，包括列出、獲取詳細信息、創建、更新和刪除機關單位等操作。所有端點均採用 POST-only 資安機制，並統一回應格式。

## 主要函數
- `list_agencies`
- `get_agency_detail`
- `create_agency`
- `update_agency`
- `delete_agency`
- `get_agency_statistics`
- `fix_agency_parsed_names`
- `get_association_summary`
- `batch_associate_agencies`
- `suggest_agencies`

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.agency`
- `app.schemas.common`
- `app.services.agency_service`
- `app.services.agency_statistics_service`
- `app.services.agency_matching_service`

### 版本信息
v3.0 - 2026-02-06  
- 重構: AgencyService 升級為工廠模式，移除端點中的 db 參數傳遞
```

此 Markdown 文檔概括了 `app.api.endpoints.agencies` 模組的主要內容和結構。
