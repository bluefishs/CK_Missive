---
title: app.services.ai.agent.agent_router
kg_entity_id: 799826
type: module
module_lines: 572
module_relations: 20
file_path: /app/app/services/ai/agent/agent_router.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.agent.agent_router

## 概述
Agent Router 是一個輕量級路由層，用於在LLM规划前拦截可以直接路由的查询，从而降低50%以上的查询延迟。该模块通过多种策略实现高效的查询处理和响应。

## 主要類別
- **RouteDecision**: 路由决策类。
- **AgentRouter**: 代理路由器类。

## 公開函數
- **extract_tool_and_query**: 提取工具和查询信息的函数。
- **match_learned_route**: 匹配学习到的路由路径的函数。

## 依賴關係
- `app.core.ai_connector`
- `app.core.redis_client`
- `app.db.database`
- `app.services.ai.core.agent_utils`
- `app.services.ai.agent.agent_chitchat`
- `app.services.ai.agent.agent_intelligence_state`
- `app.services.ai.agent.agent_pattern_learner`
- `app.services.ai.agent.agent_tool_monitor`

### 路由优先级
1. Chitchat 短路 — is_chitchat() (已有)
2. Pattern Match — 历史成功模式 (confidence >= threshold)
2.5. Gemma 4 语意意图分类 — 轻量LLM单次呼叫
3. Fallthrough → LLM Planning（现有流程）

### 设计原则
- 只在高信心时拦截（宁可多走LLM，不可规划错误）
- 所有路由决策记录至AgentTrace
- 降级工具自动过滤
```

此Markdown文档概述了`app.services.ai.agent.agent_router`模块的主要内容和结构。
