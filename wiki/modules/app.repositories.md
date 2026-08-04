---
title: app.repositories
kg_entity_id: 11738
type: module
module_lines: 127
module_relations: 29
file_path: /app/app/repositories/__init__.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.repositories

## 概述
本模組提供統一的資料存取介面，將資料庫操作從 Service 層分離。主要包含基類和特定對象的 Repositories，用於公文、專案、機關等不同領域的數據訪問。

## 主要類別
- BaseRepository: 泛型基類，提供標準 CRUD 操作
- DocumentRepository: 公文特定查詢
- ProjectRepository: 專案特定查詢
- AgencyRepository: 機關特定查詢
- Query Builders: 流暢介面查詢建構器 (v1.1.0 新增)

## 公開函數
本模組無公開函數。

## 依賴關係
- app.repositories.base_repository
- app.repositories.document_repository
- app.repositories.document_stats_repository
- app.repositories.project_repository
- app.repositories.agency_repository
- app.repositories.vendor_repository
- app.repositories.calendar_repository
- app.repositories.notification_repository
- app.repositories.user_repository
- app.repositories.configuration_repository
```

這個 Markdown 文檔概括了 `app.repositories` 模組的結構、主要類別和依賴關係。
