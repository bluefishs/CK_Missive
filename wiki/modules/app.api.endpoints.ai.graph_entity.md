---
title: app.api.endpoints.ai.graph_entity
kg_entity_id: 20917
type: module
module_lines: 229
module_relations: 19
file_path: /app/app/api/endpoints/ai/graph_entity.py
created: 2026-08-24
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.graph_entity

## 概述
知識圖譜實體查詢 API 端點，提供正規化實體的搜尋、鄰居、詳情、時間軸、排名、統計、DB Schema 等功能。此模組由 `graph_query.py` 重構而成。

## 主要類別
無

## 公開函數
1. `search_entities`
2. `get_entity_neighbors`
3. `find_shortest_path`
4. `get_entity_detail`
5. `get_entity_timeline`
6. `get_timeline_aggregate`
7. `get_top_entities`
8. `get_entity_graph`
9. `get_graph_stats`
10. `get_db_schema`

## 依賴關係
1. `app.core.dependencies`
2. `app.extended.models`
3. `app.schemas.knowledge_graph`
4. `app.services.ai.graph.graph_query_service`
5. `app.services.ai.graph.schema_reflector`
```

此 Markdown 文檔概括了模組的結構、功能和依賴關係，方便讀者快速了解其內容。
