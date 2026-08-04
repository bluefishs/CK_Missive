---
title: app.core.scheduler
kg_entity_id: 11571
type: module
module_lines: 4191
module_relations: 148
file_path: /app/app/core/scheduler.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.scheduler

## 概述
此模組提供定時任務排程功能，用於處理待發送提醒、清理過期事件以及其他定時任務。v2.0.0 版本新增了排程執行追蹤 (SchedulerTracker)。

## 主要類別
- SchedulerTracker

## 公開函數
- tracked_job
- get_scheduler
- process_pending_reminders_job
- cleanup_expired_events_job
- einvoice_sync_job
- erp_graph_ingest_job
- code_graph_incremental_job
- code_graph_reconcile_job
- code_dup_triage_job
- db_schema_refresh_job

## 依賴關係
- app.db.database
- app.services.calendar.reminder_service
- app.services.einvoice.einvoice_sync_service
- app.core.config
- app.services.ai.graph.code_graph_service
- app.core.paths
- app.core.ai_connector
- app.services.security_scanner
- app.services.ai.proactive.proactive_triggers
- app.services.ai.proactive.proactive_triggers_erp
