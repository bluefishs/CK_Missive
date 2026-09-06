---
title: app.services.ai.domain.digital_twin_service
kg_entity_id: 800013
type: module
module_lines: 478
module_relations: 20
file_path: /app/app/services/ai/domain/digital_twin_service.py
created: 2026-09-07
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.ai.domain.digital_twin_service

## 概述
該模組提供了數位分身服務層，聚合多源自覺資料，並從 `digital_twin.py` 端點提取業務邏輯。主要功能包括 Agent 拓撲圖構建、QA 影響分析和 Dashboard 聚合快照。

## 主要類別
- **DigitalTwinService**

## 公開函數
無

## 依賴關係
- app.core.ai_connector
- app.core.redis_client
- app.db.database
- app.repositories.agent_trace_repository
- app.services.ai.federation.federation_client
- app.services.ai.agent.agent_capability_tracker
- app.services.ai.agent.agent_mirror_feedback
- app.services.ai.agent.agent_roles
- app.services.ai.agent.agent_self_profile
- app.services.ai.agent.agent_tool_monitor

版本: 1.1.0 — asyncio.gather 并行化 + git 安全封装  
创建日期: 2026-03-25
```
此 Markdown 文檔概括了 `app.services.ai.domain.digital_twin_service` 模組的主要信息，包括概述、主要類別、公開函數和依賴關係。
