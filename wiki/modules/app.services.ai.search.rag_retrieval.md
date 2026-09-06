---
title: app.services.ai.search.rag_retrieval
kg_entity_id: 800148
type: module
module_lines: 381
module_relations: 19
file_path: /app/app/services/ai/search/rag_retrieval.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.search.rag_retrieval

## 概述
此模組負責知識圖譜查詢擴展、段落級/文件級向量檢索、Hybrid Reranking（向量 + BM25 + 關鍵字覆蓋度）、LLM 上下文建構以及查詢詞提取。該模組從 `rag_query_service.py` 中拆分出來，用於實現高效的知識增強型搜索和上下文生成。

## 主要函數
- **expand_query_with_kg**: 知識圖譜查詢擴展。
- **retrieve_documents**: 段落級/文件級向量檢索。
- **retrieve_chunks**: 檢索片段。
- **build_context**: 建構上下文。
- **extract_query_terms**: 提取查詢詞。

## 依賴關係
- `app.extended.models`
- `app.repositories.query_builders.document_query_builder`
- `app.services.ai.core.ai_config`
- `app.services.wiki.service`
- `app.services.ai.search.reranker`
- `app.services.ai.search.search_entity_expander`
- `app.core.hnsw_config`

## 版本信息
版本: 1.0.0  
创建日期: 2026-03-26 (提取自 `rag_query_service.py` v2.4.0)
