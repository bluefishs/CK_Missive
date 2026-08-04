---
title: app.services.ai.agent.agent_synthesis
kg_entity_id: 799885
type: module
module_lines: 603
module_relations: 22
file_path: /app/app/services/ai/agent/agent_synthesis.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.agent.agent_synthesis

## 概述
該模組負責實現 Agent 合成功能，包括根據工具結果生成最終回答、從 LLM 回答中提取真正答案、將工具結果建構為 LLM 上下文、生成工具結果的簡短摘要以及在無工具情況下的回退機制。

## 主要類別
- **AgentSynthesizer**

## 公開函數
該模組沒有公開函數，主要通過 `AgentSynthesizer` 類別的方法來實現其功能。

## 依賴關係
- app.db.database
- app.services.ai.core.agent_utils
- app.services.ai.core.ai_prompt_manager
- app.services.ai.core.citation_validator
- app.services.ai.core.thinking_filter
- app.services.ai.graph.graph_traversal_service
- app.services.contracts.facades.wiki
- app.services.ai.tools.tool_result_formatter
- app.services.ai.agent.agent_post_processing
- app.services.ai.agent.agent_roles
