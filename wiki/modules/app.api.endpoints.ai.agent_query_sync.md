---
title: app.api.endpoints.ai.agent_query_sync
kg_entity_id: 10954
type: module
module_lines: 565
module_relations: 26
file_path: /app/app/api/endpoints/ai/agent_query_sync.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.agent_query_sync

## 概述
此模組實現了一個同步問答 API 端點，供外部系統（如 OpenClaw、LINE Bot、MCP 和 Telegram）透過 HTTP 呼叫。該端點返回完整的 JSON 回應，而非 SSE 串流。

## 主要類別
- 無

## 公開函數
- `agent_query_sync`

## 依賴關係
- `app.core.dependencies`
- `app.core.rate_limiter`
- `app.db.database`
- `app.schemas.ai.rag`
- `app.services.ai.core.ai_config`
- `app.services.ai.misc.missive_agent`
- `app.services.ai.tools.tool_registry`
- `app.services.ai.agent.agent_conversation_memory`
- `app.services.ai.agent.agent_trace`
- `app.services.ai.agent.shadow_helpers`

### 函數: agent_query_sync
此函數實現了同步問答 API 端點的主要邏輯。支援多種格式，包括 v0 (legacy) 和 v1 (Schema v1.0)，並在 v3.0.0 版本中加入了渠道來源追蹤功能（line/telegram）。
