---
title: app.api.endpoints.wiki
kg_entity_id: 800317
type: module
module_lines: 182
module_relations: 22
file_path: /app/app/api/endpoints/wiki.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.wiki

## 概述
此模組提供了與維基相關的 CRUD（創建、讀取、更新、刪除）操作、搜尋功能、lint 檢查、索引重建等，用於管理維基內容及其元數據。

## 主要類別
1. `IngestEntityRequest`
2. `IngestSourceRequest`
3. `SaveSynthesisRequest`
4. `SearchRequest`

## 公開函數
1. `ingest_entity`
2. `ingest_source`
3. `save_synthesis`
4. `search_wiki`
5. `read_page`
6. `lint_wiki`
7. `rebuild_index`
8. `wiki_stats`
9. `wiki_graph`
10. `wiki_coverage`

## 依賴關係
1. `app.core.dependencies`
2. `app.services.wiki.compiler`
3. `app.services.wiki.coverage`
4. `app.services.wiki.service`
