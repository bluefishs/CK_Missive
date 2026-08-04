---
title: app.services.ai.search.document_natural_search
kg_entity_id: 800114
type: module
module_lines: 363
module_relations: 23
file_path: /app/app/services/ai/search/document_natural_search.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.search.document_natural_search

## 概述
此模組實現了一個基於自然語言的公文搜尋服務，從 `document_ai_service.py` 提取並處理了完整的搜尋流程，包括意圖解析、知識圖譜實體擴展、查詢建構、附件/專案取得以及結果組裝和搜索歷史寫入。

## 公開函數
- **execute_natural_search**: 處理自然語言公文搜尋的主流程。

## 依賴關係
- `app.extended.models`
- `app.repositories.query_builders.document_query_builder`
- `app.schemas.ai.search`
- `app.services.ai.core.ai_config`
- `app.services.ai.core.embedding_manager`
- `app.services.ai.document.document_search_helpers`
- `app.services.ai.search.search_entity_expander`
- `app.services.ai.search.synonym_expander`
