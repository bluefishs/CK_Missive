---
title: app.services.ai.agent.agent_orchestrator
kg_entity_id: 799753
type: module
module_lines: 662
module_relations: 45
file_path: /app/app/services/ai/agent/agent_orchestrator.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.agent.agent_orchestrator

## 概述
`AgentOrchestrator` 是 Agentic 文件檢索引擎的核心模組，負責協調和執行多個子系統以實現智能化的代理行為。它通過意圖預處理、LLM 規劃、工具循環和合成回答等步驟來生成最終的回答。

## 主要類別
- **AgentOrchestrator**: 主編排類別，負責協調各個子模組完成任務。

## 公開函數
無公開函數。

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

### 子模組
- **agent_post_processing.py**: 處理後期步驟，包括核實、記憶、追蹤和學習。
- **agent_streaming_helpers.py**: 提供閒聊串流及 Fallback RAG 的幫助函數。
- **agent_planner.py / agent_tools.py / agent_synthesis.py**: 分別負責規劃、工具使用和合成回答。

## 版本
2.6.0 - 模組化拆分 (post_processing + streaming_helpers)
```

此Markdown文件詳細描述了`app.services.ai.agent.agent_orchestrator`模組的結構、依賴關係以及主要類別的功能。
