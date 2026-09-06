---
title: app.api.endpoints.health
kg_entity_id: 10850
type: module
module_lines: 443
module_relations: 39
file_path: /app/app/api/endpoints/health.py
created: 2026-08-03
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.health

## 概述
此模組提供了多種健康監控端點，用於檢查應用程序的各個方面，包括基本狀態、詳細狀態、性能指標、就緒性檢查、存活性檢查等。

## 公開函數
1. `basic_health_check` - 簡單的健康檢查。
2. `detailed_health_check` - 詳細的健康檢查。
3. `get_performance_metrics` - 取得性能指標。
4. `readiness_check` - 就緒性檢查。
5. `liveness_check` - 存活性檢查。
6. `connection_pool_status` - 連接池狀態。
7. `background_tasks_status` - 背景任務狀態。
8. `audit_service_status` - 审核服務狀態。
9. `backup_health_check` - 备份健康檢查。
10. `health_summary` - 健康總結。

## 依賴關係
- `app.core.build_info`
- `app.db.database`
- `app.core.rate_limiter`
- `app.extended.models`
- `app.core.dependencies`
- `app.services.system.health_service`
- `app.core.health_probe`
- `app.core.scheduler`
- `app.core.service_health_probe`
- `app.core.ai_connector`
