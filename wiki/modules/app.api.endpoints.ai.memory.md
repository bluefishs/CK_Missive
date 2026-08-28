---
title: app.api.endpoints.ai.memory
kg_entity_id: 800503
type: module
module_lines: 693
module_relations: 39
file_path: /app/app/api/endpoints/ai/memory.py
created: 2026-08-03
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.ai.memory

## 概述
此 Python 模組實現了 Memory Wiki 的後端 API 端點，主要用於管理記憶體日誌、預言、結晶等相關操作。

## 主要類別
無

## 公開函數
1. `memory_diary_by_date`: 根據指定日期讀取記憶體日誌。
2. `memory_diary_recent`: 開取最近的記憶體日誌。
3. `memory_anti_echo_recent`: 管理反饋機制，獲取最新的反饋信息。
4. `memory_patterns_list`: 列出記憶模式列表及其詳細信息。
5. `memory_failures_list`: 列出失敗記錄及其詳細信息。
6. `memory_proposals_list`: 列出預言列表及其詳細信息。
7. `memory_proposals_approve`: 批准預言。
8. `memory_proposals_reject`: 拒絕預言。
9. `memory_crystals_list`: 列出結晶列表及其詳細信息。
10. `memory_crystals_rollback`: 回滾結晶。

## 依賴關係
- `app.core.dependencies`
- `app.core.paths`
- `app.schemas.ai.memory`
- `app.services.memory.diary_service`
- `app.services.memory.crystal_applier`
- `app.core.scheduler`
- `app.services.memory.crystallizer`
- `app.core.memory_wiki_metrics`
- `app.services.memory.soul_loader`

## 端點分類
1. **Diary**: 閱讀今日/指定日期的記憶體日誌。
2. **Patterns/Failures**: 列表 + 詳情。
3. **Proposals**: 列表 + approve/reject。
4. **Crystals**: 列表 + rollback。
5. **Autobiography**: 最新 + 历史。
6. **Nebula**: 技能星雲 graph 資料。
7. **Stats**: Memory 總覽。

全部 POST 操作需要身份驗證（require_auth），以確保操作的安全性。
```

以上是為 `app.api.endpoints.ai.memory` 生成的 Markdown 文檔。
