---
title: app.api.endpoints.ai.digital_twin
kg_entity_id: 15238
type: module
module_lines: 387
module_relations: 39
file_path: /app/app/api/endpoints/ai/digital_twin.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.digital_twin

## 概述
該模組提供了與本地 Agent 的交互端點，支持實時數據查詢、任務管理、代理狀態監控等操作。主要功能包括數字雙胞胎的健康檢查和影響分析。

## 主要類別
- 無

## 公開函數
1. `digital_twin_query_stream`
2. `approve_task`
3. `reject_task`
4. `get_task_status`
5. `live_activity_stream`
6. `agent_topology`
7. `qa_impact_analysis`
8. `digital_twin_health`
9. `delegate_auto_proxy`
10. `dashboard_snapshot`

## 依賴關係
- `app.api.sse_utils`
- `app.core.dependencies`
- `app.extended.models`
- `app.repositories.document_repository`
- `app.repositories.taoyuan.dispatch_order_repository`
- `app.services.taoyuan.dispatch_response_formatter`
- `app.schemas.ai.digital_twin`
- `app.services.ai.federation.federation_client`
- `app.services.ai.agent.agent_introspection`
- `app.services.ai.agent.agent_orchestrator`

### 版本信息
- Version: 4.0.0
- Created: 2026-03-22
- Updated: 2026-04-16 — v4.0 移除 OpenClaw/NemoClaw 依賴 (ADR-0014/0015)

### 說明
- **digital_twin_query_stream**: 通過 SSE 協議實時查詢數字雙胞胎的數據。
- **approve_task**: 批准任務。
- **reject_task**: 拒絕任務。
- **get_task_status**: 查詢任務狀態。
- **live_activity_stream**: 監控實時活動流。
- **agent_topology**: 获取代理拓扑结构信息。
- **qa_impact_analysis**: 质量影响分析。
- **digital_twin_health**: 数字双胞胎健康检查。
- **delegate_auto_proxy**: 自动委托代理。
- **dashboard_snapshot**: 生成仪表板快照。
