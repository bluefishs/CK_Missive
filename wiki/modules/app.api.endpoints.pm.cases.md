---
title: app.api.endpoints.pm.cases
kg_entity_id: 15562
type: module
module_lines: 490
module_relations: 28
file_path: /app/app/api/endpoints/pm/cases.py
created: 2026-08-04
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.pm.cases

## 概述
此 Python 模組包含了處理 PM（項目管理）案件相關 API 端點的實現，主要負責提供創建、查詢和更新案件的功能。這些端點僅支持 POST 方法。

## 主要類別
無

## 公開函數
- `list_cases`: 列出所有案件。
- `create_case`: 創建新的案件。
- `get_yearly_trend`: 獲取年度趨勢數據。
- `get_case_detail`: 獲取特定案件的詳細信息。
- `update_case`: 更新現有案件的信息。
- `update_case_by_id`: 根據 ID 更新案件。
- `delete_case`: 刪除指定的案件。
- `get_summary`: 獲取案件概要數據。
- `generate_case_code`: 生成新的案件編碼。
- `recalculate_progress`: 計算並更新案件進度。

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.extended.models.pm`
- `app.schemas.pm`
- `app.services.pm`
- `app.services.case_field_sync_service`
