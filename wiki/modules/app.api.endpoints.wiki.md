---
title: app.api.endpoints.wiki
kg_entity_id: 800317
type: module
module_lines: 151
module_relations: 19
file_path: /app/app/api/endpoints/wiki.py
created: 2026-08-17
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.wiki

## 概述
此模組提供了與維基百科相關的 CRUD（創建、讀取、更新、刪除）、搜尋、lint、索引重建等操作的 API 端點。

## 主要類別
無

## 公開函數
1. `ingest_entity` - 將實體資料 ingestion 到維基系統中。
2. `ingest_source` - 將來源資料 ingestion 到維基系統中。
3. `save_synthesis` - 儲存合成的維基頁面內容。
4. `search_wiki` - 在維基百科中搜尋指定的條目。
5. `read_page` - 讀取維基百科中的特定頁面。
6. `lint_wiki` - 驗證維基百科頁面的格式和一致性。
7. `rebuild_index` - 重新構建維基百科索引。
8. `wiki_stats` - 提供維基百科相關統計數據。
9. `wiki_graph` - 統計維基百科中的圖形關係。
10. `wiki_coverage` - 分析維基百科的覆蓋範圍。

## 依賴關係
- `app.core.dependencies`
- `app.services.wiki.compiler`
- `app.services.wiki.coverage`
- `app.services.wiki.service`
- `app.schemas.wiki`
