---
title: app.services.ai.agent.agent_orchestrator
kg_entity_id: 799753
type: module
module_lines: 674
module_relations: 47
file_path: /app/app/services/ai/agent/agent_orchestrator.py
created: 2026-08-03
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.agent.agent_orchestrator

## 概述
`AgentOrchestrator` 是 Agentic 文件檢索引擎的核心模組，負責統籌和協調各個子模組進行任務處理。該模組通過多步驟流程實現從意圖預處理到最終合成回答的全過程。

## 主要類別
- **AgentOrchestrator**: 主編排類

## 公開函數
無公開函數，主要通過內部方法和子模組進行協作完成任務。

## 依賴關係
- `app.core.ai_connector`
- `app.services.ai.core.ai_config`
- `app.services.ai.core.embedding_manager`
- `app.services.ai.agent.agent_tools`
- `app.services.ai.agent.agent_planner`
- `app.services.ai.agent.agent_synthesis`
- `app.services.ai.tools.tool_result_formatter`
- `app.services.ai.agent.agent_tool_loop`
- `app.services.ai.agent.agent_roles`
- `app.services.ai.agent.agent_trace`

## 流程
1. **意圖預處理**: 通過 `AgentOrchestrator` 的初始化和配置，對用戶的輸入進行解析和理解。
2. **LLM 規劃**: 使用大語言模型（LLM）根據預處理後的意圖生成具體任務或規划。
3. **Tool Loop**: 執行工具循環，調用相應的工具來獲取信息或執行操作。
4. **合成回答 (SSE 串流)**: 將工具結果和規劃內容合成為最終的回答，並以 SSE（Server-Sent Events）方式逐步返回給用戶。

## 子模組
- `agent_post_processing.py`: 處理後處理步驟，包括核實、記憶管理、追蹤和學習。
- `agent_streaming_helpers.py`: 提供閒聊串流功能及 Fallback RAG（Retrieval-Augmented Generation）支持。
- `agent_planner.py`, `agent_tools.py`, `agent_synthesis.py`: 分別負責規劃生成、工具調用和合成回答。

## 版本信息
版本: 2.6.0 - 模組化拆分 (post_processing + streaming_he)
```

此Markdown文件詳細描述了`app.services.ai.agent.agent_orchestrator`模組的功能、類別、依賴
