---
title: app.api.endpoints.ai.memory
kg_entity_id: 800503
type: module
module_lines: 725
module_relations: 45
file_path: /app/app/api/endpoints/ai/memory.py
created: 2026-08-03
updated: 2026-08-03
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.memory

## 概述
此模組實現了 Memory Wiki 的後端 API 端點，主要用於處理與記憶日記、預言、結晶等相關的操作。這些操作包括讀取、審批、拒絕和回滾等。

## 主要類別
- DiaryQueryReq
- ListReq
- ApproveReq
- RejectReq
- RollbackReq
- NebulaReq
- AutoApplyModeReq

## 公開函數
- memory_diary_by_date
- memory_diary_recent
- memory_anti_echo_recent
- memory_patterns_list
- memory_failures_list
- memory_proposals_list
- memory_proposals_approve
- memory_proposals_reject
- memory_crystals_list
- memory_crystals_rollback

## 依賴關係
- app.core.dependencies
- app.core.paths
- app.services.memory.diary_service
- app.services.memory.crystal_applier
- app.core.scheduler
- app.services.memory.crystallizer
- app.core.memory_wiki_metrics
- app.services.memory.soul_loader
```

此 Markdown 文檔概括了 `app.api.endpoints.ai.memory` 模組的結構和功能，包括主要類別、公開函數及其依賴關係。
