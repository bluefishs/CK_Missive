---
title: app.api.endpoints.health
kg_entity_id: 10850
type: module
module_lines: 330
module_relations: 34
file_path: /app/app/api/endpoints/health.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.health

## 概述
此模組提供了多種健康檢查端點，用於監控應用程序的各種狀態和性能指標。這些端點涵蓋了基本的健康檢查、詳細的健康檢查、性能度量、就緒性檢查、存活性檢查以及後台任務和數據庫連接池等狀態。

## 公開函數
1. `basic_health_check`: 基本健康檢查。
2. `detailed_health_check`: 詳細的健康檢查。
3. `get_performance_metrics`: 获取性能指标。
4. `readiness_check`: 就緒性檢查。
5. `liveness_check`: 存活性檢查。
6. `connection_pool_status`: 連接池狀態。
7. `background_tasks_status`: 后台任務狀態。
8. `audit_service_status`: 审核服務狀態。
9. `backup_health_check`: 备份健康检查。
10. `health_summary`: 健康總結。

## 依賴關係
1. `app.core.ai_connector`
2. `app.core.background_tasks`
3. `app.core.db_monitor`
4. `app.core.dependencies`
5. `app.core.rate_limiter`
6. `app.core.redis_client`
7. `app.core.scheduler`
8. `app.extended.models`
9. `app.core.service_health_probe`
10. `app.services.system.health_service`
