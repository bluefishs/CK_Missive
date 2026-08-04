---
title: app.api.endpoints.ai.agent_evolution
kg_entity_id: 20840
type: module
module_lines: 225
module_relations: 23
file_path: /app/app/api/endpoints/ai/agent_evolution.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.agent_evolution

## 概述
該模組提供了與智能代理進化相關的API端點，包括進化狀態、日誌、工具健康狀況、能力概況以及學習模式和度量標準。這些API支持前端視覺化並提供學習健康度與畢業統計。

## 公開函數
- `evolution_status`: 獲取智能代理的進化狀態。
- `evolution_journal`: 獲取智能代理的進化日誌。
- `tool_health`: 獲取工具健康狀況。
- `capability_profile`: 獲取能力概況。
- `get_learned_patterns`: 獲取學習模式。
- `get_persistent_learnings`: 獲取持久學習內容。
- `get_evolution_metrics`: 獲取進化度量。

## 依賴關係
- `app.core.dependencies`
- `app.core.redis_client`
- `app.extended.models`
- `app.extended.models.agent_learning`
- `app.repositories.agent_learning_repository`
- `app.schemas.ai.stats`
- `app.services.ai.agent.agent_capability_tracker`
- `app.services.ai.agent.agent_evolution_scheduler`
- `app.services.ai.agent.agent_pattern_learner`
- `app.services.ai.agent.agent_tool_monitor`

## 版本信息
- Version: 2.0.0 (2026-04-29 — 領域整併，行數驅動 → 領域驅動)
```
此Markdown文檔概括了`app.api.endpoints.ai.agent_evolution`模組的結構和功能，包括公開函數及其依賴關係。
