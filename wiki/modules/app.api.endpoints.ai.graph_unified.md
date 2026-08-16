---
title: app.api.endpoints.ai.graph_unified
kg_entity_id: 20930
type: module
module_lines: 386
module_relations: 22
file_path: /app/app/api/endpoints/ai/graph_unified.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.graph_unified

## 概述
此模組提供了跨圖譜統一搜尋的 API 端點，涵蓋了 Code Wiki、模組概覽、統一搜尋、模組映射、智慧搜尋、ERP 圖譜網路和案件流程鏈等功能。

## 主要函數
- `get_code_wiki_graph`
- `get_module_overview`
- `unified_graph_search`
- `get_module_mappings`
- `smart_graph_search`
- `get_erp_graph_network`
- `get_case_flow`

## 依賴關係
- `app.core.constants`
- `app.core.dependencies`
- `app.db.database`
- `app.extended.models`
- `app.extended.models.knowledge_graph`
- `app.repositories.navigation_repository`
- `app.schemas.knowledge_graph`
- `app.extended.models.tender_cache`
- `app.services.ai.graph.erp_graph_types`
- `app.services.ai.graph.graph_query_service`

## 版本信息
- Version: 1.1.0
- Created: 2026-03-30
- Updated: 2026-04-09 - 拆分 skills-map/skill-evolution 至 graph_skills_map.py

## 註釋
此模組是從 `graph_query.py` 文件重構而來。
