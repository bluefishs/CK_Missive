---
title: app.api.endpoints.ai.embedding_pipeline
kg_entity_id: 10980
type: module
module_lines: 384
module_relations: 24
file_path: /app/app/api/endpoints/ai/embedding_pipeline.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.embedding_pipeline

## 概述
此 Python 模組提供了與 Embedding 批次管線相關的 API 端點，用於獲取 embedding 覆蓋率統計和執行批次嵌入任務。

## 主要類別
無

## 公開函數
1. `get_embedding_stats` - 用於獲取 embedding 的覆蓋率統計信息。
2. `run_embedding_batch` - 用於觸發 embedding 批次處理。
3. `run_entity_embedding_batch` - 用於對特定實體進行批量嵌入處理。
4. `index_attachment_content` - 用於索引附件內容。
5. `get_attachment_index_stats` - 用於獲取附件索引的統計信息。

## 依賴關係
1. `app.core.ai_connector`
2. `app.core.config`
3. `app.core.dependencies`
4. `app.db.database`
5. `app.extended.models`
6. `app.schemas.ai.graph`
7. `app.scripts.backfill_embeddings`
8. `app.services.ai.core.embedding_manager`
9. `app.services.ai.document.attachment_content_indexer`

版本: 1.0.0  
創建日期: 2026-02-24
