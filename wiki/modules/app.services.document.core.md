---
title: app.services.document.core
kg_entity_id: 798558
type: module
module_lines: 436
module_relations: 19
file_path: /app/app/services/document/core.py
created: 2026-08-24
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.services.document.core

## 概述
公文服務層，負責處理核心業務邏輯。該模組經過多次重構和拆分，以提高代碼的可讀性和維護性。

## 主要類別
- **DocumentService**: 公文服務的主要實現類別。

## 公開函數
無公開函數。

## 依賴關係
- `app.core.cache_manager`: 網站緩存管理器。
- `app.core.rls_filter`: 行級別權限過濾器。
- `app.extended.models`: 扩展模型類。
- `app.repositories.document_repository`: 公文數據庫存儲庫。
- `app.schemas.document`: 公文模式定義。
- `app.scripts.normalize_unicode`: Unicode 字元正規化腳本（如康熙部首轉標準中文）。
- `app.services.calendar.event_auto_builder`: 事件自動構建服務。
- `app.services.strategies.agency_matcher`: 獎勵機構匹配策略服務。
- `app.services.audit_mixin`: 审計混入類。
- `app.core.domain_events`: 域事件管理器。

## 版本歷史
v2.4 - 2026-03-23  
- 拆分 DocumentFilterService (篩選邏輯)

v2.3 - 2026-03-18  
- 拆分 DocumentDispatchLinkerService (公文-派工單自動關聯)
- 拆分 DocumentImportLogicService (公文匯入邏輯)

v2.2 - 2026-01-16  
- 新增 Unicode 字元正規化（康熙部首轉標準中文）

v2.1 - 2026-01-10  
- 新增行級別權限過濾 (Row-Level Security)
- 非管理員只能查看關聯專案的公文
```

此Markdown文件概括了模組 `app.services.document.core` 的基本信息，包括其主要類別、依賴關係和版本歷史。
