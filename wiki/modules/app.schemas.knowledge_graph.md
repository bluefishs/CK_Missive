---
title: app.schemas.knowledge_graph
kg_entity_id: 12469
type: module
module_lines: 702
module_relations: 61
file_path: /app/app/schemas/knowledge_graph.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.knowledge_graph

## 概述
此 Python 模組包含知識圖譜的 Pydantic Schema，用於管理實體查詢和知識圖譜相關操作。模組中定義了多個 Request 和 Response 的類別，以支持不同階段的功能需求。

## 主要類別
- KGEntitySearchRequest: 知識圖譜實體搜索請求。
- KGEntityItem: 知識圖譜實體項目。
- KGEntitySearchResponse: 知識圖譜實體搜索回應。
- KGNeighborsRequest: 險鄰關係請求。
- KGGraphNode: 知識圖譜節點。
- KGGraphEdge: 知識圖譜邊。
- KGNeighborsResponse: 隁鄰關係回應。
- KGShortestPathRequest: 最短路徑搜索請求。
- KGPathNode: 路徑節點。
- KGShortestPathResponse: 最短路徑搜索回應。
- KGEntityDetailRequest: 知識圖譜實體詳細信息請求。
- KGEntityDocument: 知識圖譜實體文檔。
- KGEntityRelationship: 知識圖譜實體關係。
- KGEntityDetailResponse: 知識圖譜實體詳細信息回應。
- KGTimelineRequest: 時間線搜索請求。
- KGTimelineItem: 時間線項目。
- KGTimelineResponse: 時間線回應。
- KGTimelineAggregateRequest: 時間線聚合請求。
- KGTimelineAggregateBucket: 時間線聚合桶。
- KGTimelineAggregateResponse: 時間線聚合回應。
- KGTopEntitiesRequest: 知識圖譜頂級實體搜索請求。
- KGTopEntitiesResponse: 知識圖譜頂級實體搜索回應。
- KGIngestRequest: 知識圖譜數據 ingestion 請求。
- KGIngestResponse: 知識圖譜數據 ingestion 回應。
- KGEntityGraphRequest: 知識圖譜實體圖請求。
- KGEntityGraphResponse: 知識圖譜實體圖回應。
- KGGraphStatsResponse: 知識圖譜統計信息回應。
- KGMergeEntitiesRequest: 合併知識圖譜實體請求。
- KGMergeEntitiesResponse:
