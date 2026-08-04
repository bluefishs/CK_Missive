---
title: app.api.endpoints.ai.agent_capability
kg_entity_id: 800449
type: module
module_lines: 432
module_relations: 40
file_path: /app/app/api/endpoints/ai/agent_capability.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.agent_capability

## 概述
此模組提供了與 AI 倉儲代理能力相關的端點，包括其自覺能力、主動提醒以及跨專案聯邦功能。這些端點允許用戶獲取代理的能力概況、鏡像報告和自我描述，並支持代理在不同領域之間進行知識貢獻和搜索。

## 主要類別
- 無

## 公開函數
1. `get_agent_capability_profile`
2. `get_agent_mirror_report`
3. `get_agent_self_profile`
4. `get_agent_proactive_alerts`
5. `federated_contribute`
6. `federated_search`
7. `cross_domain_link`
8. `cross_domain_path`
9. `federation_health`
10. `embedding_backfill`

## 依賴關係
- `app.core.dependencies`
- `app.core.service_auth`
- `app.extended.models`
- `app.schemas.knowledge_graph`
- `app.services.ai.agent.agent_capability_tracker`
- `app.core.ai_connector`
- `app.services.ai.agent.agent_mirror_feedback`
- `app.services.ai.agent.agent_self_profile`
- `app.services.ai.agent.agent_proactive_scanner`
- `app.services.ai.domain.cross_domain_contribution_service`

### 版本信息
- Version: 2.0.0
- 重命名自 `agent_nemoclaw.py` (ADR-0014/0015)
- Created: 2026-03-29
- Updated: 2026-04-16
