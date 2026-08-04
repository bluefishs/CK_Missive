---
title: app.services.ai.agent.agent_planner
kg_entity_id: 799791
type: module
module_lines: 670
module_relations: 29
file_path: /app/app/services/ai/agent/agent_planner.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.agent.agent_planner

## 概述
該模組負責管理代理的規劃流程，包括意圖前處理、LLM 工具規劃、ReAct 循環以及自動修正。這些功能共同作用以確保代理能夠根據給定的情境有效地生成和執行任務。

## 主要類別
- **AgentWorkingMemory**: 管理代理的工作記憶。
- **AgentPlanner**: 負責規畫代理的行動策略。

## 公開函數
無公開函數，主要通過方法進行內部操作。

## 依賴關係
- `app.services.ai.tools.tool_registry`
- `app.services.ai.core.agent_utils`
- `app.services.ai.agent.agent_auto_corrector`
- `app.services.ai.agent.agent_learning_injector`
- `app.services.ai.agent.agent_plan_enricher`
- `app.services.ai.agent.agent_intent_preprocessor`
- `app.services.ai.agent.agent_roles`
- `app.services.contracts.facades.memory`
- `app.core.redis_client`
- `app.services.ai.agent.agent_critic`

### 具體流程
1. **_preprocess_question** → 4  樓意圖解析提取結構化 hints。
2. **plan_tools** → LLM Few-shot 規劃 + hints 合併 + 空計劃修復。
3. **evaluate_and_replan** → 快速路徑（規則自動修正）+ 慢路徑（LLM ReAct）。
4. **react** → LLM 觀察工具結果，決定下一步行動或生成回答。

### 版本信息
- 提取自 `agent_orchestrator.py` v1.8.0
- 更新至 v2.4.0 — ReAct
```

此Markdown文檔概括了模組的功能、主要類別和依賴關係，並詳細描述了其流程。
