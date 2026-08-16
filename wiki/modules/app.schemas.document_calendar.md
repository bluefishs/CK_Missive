---
title: app.schemas.document_calendar
kg_entity_id: 12413
type: module
module_lines: 206
module_relations: 20
file_path: /app/app/schemas/document_calendar.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.document_calendar

## 概述
此模組提供了 Document Calendar Integration 的 Pydantic 型別定義，用於同步和管理日曆事件。所有查詢操作使用 POST 方法進行，符合資安要求。

## 主要類別
- SyncStatusResponse
- EventListRequest
- EventDetailRequest
- EventDeleteRequest
- EventSyncRequest
- BulkSyncRequest
- UserEventsRequest
- ReminderConfig
- DocumentCalendarEventCreate
- IntegratedEventCreate
- DocumentCalendarEventUpdate
- DocumentCalendarEventResponse
- ConflictCheckRequest
- SyncIntervalRequest
- CheckDocumentRequest
- BatchUpdateStatusRequest
- BatchDeleteRequest

## 公開函數
- normalize_priority

## 依賴關係
- app.schemas.common
