---
title: app.api.endpoints.health
kg_entity_id: 10850
type: module
module_lines: 332
module_relations: 36
file_path: /app/app/api/endpoints/health.py
created: 2026-08-03
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.health

## 概述
此模組包含多個健康檢查端點，用於監控應用程序的各種狀態和性能指標。這些端點提供了基本的健康檢查、詳細的健康檢查以及性能度量等。

## 公開函數
- `basic_health_check`: 基本健康檢查。
- `detailed_health_check`: 詳細健康檢查。
- `get_performance_metrics`: 获取性能指标。
- `readiness_check`: 就绪性检查。
- `liveness_check`: 活跃性检查。
- `connection_pool_status`: 连接池状态。
- `background_tasks_status`: 背景任务状态。
- `audit_service_status`: 审计服务状态。
- `backup_health_check`: 备份健康检查。
- `health_summary`: 健康概要。

## 依賴關係
- `app.core.build_info`
- `app.core.rate_limiter`
- `app.extended.models`
- `app.core.dependencies`
- `app.services.system.health_service`
- `app.core.scheduler`
- `app.core.service_health_probe`
- `app.core.ai_connector`
- `app.core.redis_client`
- `app.core.db_monitor`

此模組在 v3.0 版本（2026-02-24）中將業務邏輯遷移至 `SystemHealthService`。
