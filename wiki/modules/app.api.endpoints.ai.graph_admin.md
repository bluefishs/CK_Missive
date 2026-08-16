---
title: app.api.endpoints.ai.graph_admin
kg_entity_id: 20910
type: module
module_lines: 366
module_relations: 22
file_path: /app/app/api/endpoints/ai/graph_admin.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.graph_admin

## 概述
知識圖譜管理操作 API 端點，提供入圖管線、實體合併、中心性分析、Obsidian 匯出、Federation 健康、ERP 入圖等管理功能。

Code Graph 相關端點已拆分至 `graph_admin_code.py`。此模組從 `graph_query.py` 中進行了重構，版本為 1.1.0，最終更新日期為 2026-04-09。

## 主要函數
- `ingest_documents`
- `merge_entities`
- `analyze_diff_impact`
- `centrality_analysis`
- `export_obsidian_vault`
- `list_relation_types`
- `federation_health`
- `verify_entity`
- `trigger_erp_graph_ingest`

## 依賴關係
- `app.core.constants`
- `app.core.dependencies`
- `app.extended.models`
- `app.extended.models.knowledge_graph`
- `app.schemas.knowledge_graph`
- `app.services.ai.graph.canonical_entity_service`
- `app.services.ai.graph.erp_graph_ingest`
- `app.services.ai.graph.graph_ingestion_pipeline`
- `app.services.ai.graph.graph_statistics_service`
- `app.services.ai.graph.obsidian_exporter`
```

以上是根據您提供的信息生成的 Markdown 文檔。如果您有其他需求或需要進一步修改，請告訴我！
