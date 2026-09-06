---
title: app.api.endpoints.pm.cases
kg_entity_id: 15562
type: module
module_lines: 539
module_relations: 28
file_path: /app/app/api/endpoints/pm/cases.py
created: 2026-08-04
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.pm.cases

## 概述
此 Python 模塊包含了處理 PM（Project Management）案件相關 API 端點的實現，主要支持創建、查詢和更新案件等操作。這些端點均為 POST 方法。

## 公開函數
- `list_cases`: 列出所有案件。
- `create_case`: 創建新案件。
- `get_yearly_trend`: 获取年度趋势数据。
- `get_case_detail`: 获取案件详细信息。
- `update_case`: 更新案件信息。
- `update_case_by_id`: 根据 ID 更新案件信息。
- `delete_case`: 删除案件。
- `get_summary`: 获取案件概要统计信息。
- `generate_case_code`: 生成案件代码。
- `recalculate_progress`: 重新计算进度。

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.extended.models.pm`
- `app.schemas.pm`
- `app.services.pm`
- `app.services.contract.field_sync`
