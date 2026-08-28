---
title: app.api.endpoints.ai.document_ai
kg_entity_id: 10964
type: module
module_lines: 505
module_relations: 19
file_path: /app/app/api/endpoints/ai/document_ai.py
created: 2026-08-24
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.document_ai

## 概述
此模組提供了公文 AI API 端點，用於生成摘要、關鍵字提取、分類建議等操作。

## 主要類別
無

## 公開函數
1. `generate_summary` - 生成公文摘要。
2. `stream_summary` - 串流生成公文摘要 (SSE) (v2.1.0 新增)。
3. `suggest_classification` - 分類建議。
4. `extract_keywords` - 關鍵字提取。
5. `natural_search_documents` - 自然語言搜尋公文。
6. `parse_search_intent` - 解析搜尋意圖。
7. `match_agency` - 匹配機構。
8. `check_ai_health` - 檢查 AI 健康狀態。
9. `get_ai_config_endpoint` - 獲取 AI 配置端點。

## 依賴關係
1. app.api.sse_utils
2. app.core.dependencies
3. app.schemas.ai.endpoints
4. app.schemas.ai.search
5. app.services.ai.core.ai_config
6. app.services.audit
7. app.services.ai.document.document_ai_service
