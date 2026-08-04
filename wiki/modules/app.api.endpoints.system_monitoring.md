---
title: app.api.endpoints.system_monitoring
kg_entity_id: 10904
type: module
module_lines: 148
module_relations: 26
file_path: /app/app/api/endpoints/system_monitoring.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.system_monitoring

## 概述
此 Python 模組包含一系列 API 端點，用於系統監控和錯誤日誌管理。這些端點需要管理員認證才能訪問。

## 主要類別
無

## 公開函數
1. `get_detailed_health_check` - 取得詳細的健康檢查結果。
2. `get_error_summary` - 取得錯誤摘要。
3. `get_recent_errors` - 取得最近的錯誤記錄。
4. `clear_error_stats` - 清除錯誤統計數據。
5. `get_log_files_status` - 取得日誌文件狀態。
6. `test_logging` - 測試日誌功能。
7. `get_error_logs` - 取得特定錯誤的日誌記錄。
8. `get_system_metrics` - 取得系統指標。
9. `get_review_dashboard` - 取得覆盤儀表板。

## 依賴關係
1. `app.core.dependencies`
2. `app.core.logging_manager`
3. `app.db.database`
4. `app.extended.models`
5. `app.services.system.health_service`
6. `app.services.system.system_monitoring_service`
