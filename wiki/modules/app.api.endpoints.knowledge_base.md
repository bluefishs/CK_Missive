---
title: app.api.endpoints.knowledge_base
kg_entity_id: 15107
type: module
module_lines: 209
module_relations: 20
file_path: /app/app/api/endpoints/knowledge_base.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.knowledge_base

## 概述
此 Python 模組提供了知識庫瀏覽器 API，用於瀏覽知識地圖、ADR、架構圖以及進行向量搜尋。

## 主要函數
- `get_knowledge_tree`: 獲取知識地圖。
- `get_file_content`: 獲取文件內容。
- `list_adrs`: 列出所有 ADRs。
- `list_diagrams`: 列出所有架構圖。
- `search_knowledge_base`: 在知識庫中進行向量搜尋。
- `trigger_kb_embedding`: 觸發知識地図嵌入。
- `get_module_wiki`: 獲取模組維基頁面。
- `get_code_wiki_overview`: 獲取代碼維基概覽。
- `summarize_knowledge_card`: 縮略知識卡片。

## 依賴關係
- `app.core.ai_connector`
- `app.core.dependencies`
- `app.db.database`
- `app.schemas.knowledge_base`
- `app.services.ai.misc.code_wiki_generator`
- `app.services.ai.misc.kb_embedding`
- `app.services.ai.agent.agent_post_processing`
- `app.services.system.knowledge_base_service`
