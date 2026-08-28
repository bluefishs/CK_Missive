---
title: app.core.scheduler
kg_entity_id: 11571
type: module
module_lines: 4914
module_relations: 152
file_path: /app/app/core/scheduler.py
created: 2026-08-03
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.core.scheduler

## 概述
此模組提供了一個任務排程器，用於管理各種定時任務，包括處理待發送提醒和清理過期事件等。

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
- app.core.paths
- app.db.database
- app.services.calendar.reminder_service
- app.services.einvoice.einvoice_sync_service
- app.core.config
- app.services.ai.graph.code_graph_service
- app.core.ai_connector
- app.services.security.scanner
- app.services.ai.proactive.proactive_triggers
- app.services.ai.proactive.proactive_triggers_erp
