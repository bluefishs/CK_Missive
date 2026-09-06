---
title: app.schemas.document
kg_entity_id: 12389
type: module
module_lines: 471
module_relations: 23
file_path: /app/app/schemas/document.py
created: 2026-08-17
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.document

## 概述
此 Python 模組定義了收發文功能所需的 Pydantic 資料結構，用於描述和驗證不同類型的文檔及其相關信息。模組中的資料結構涵蓋了文檔的基本信息、狀態、分類等多個方面，並使用統一的回應格式來提高系統的一致性和易用性。

## 主要類別
1. **DocumentCategory** - 文檔分類
2. **DocumentStatus** - 文檔狀態
3. **DocumentType** - 文檔類型
4. **DocumentBase** - 基本文檔信息
5. **DocumentCreate** - 新建文檔的資料結構
6. **DocumentUpdate** - 更新文檔的資料結構
7. **StaffInfo** - 工作人員信息
8. **DocumentResponse** - 文檔回應格式
9. **DocumentFilter** - 文檔篩選條件
10. **DocumentListQuery** - 文檔列表查詢條件
11. **DocumentImportData** - 文檔導入數據
12. **DocumentImportResult** - 文檔導入結果
13. **DocumentListResponse** - 文檔列表回應格式
14. **DocumentStats** - 文檔統計信息
15. **ExportRequest** - 导出请求
16. **DocumentCreateRequest** - 新建文檔請求
17. **DocumentUpdateRequest** - 更新文檔請求
18. **DocumentSearchRequest** - 搜索文檔請求
19. **NextNumberRequest** - 下一個編號請求
20. **NextNumberResponse** - 下一個編號回應

## 公開函數
無公開函數。

## 依賴關係
- **app.schemas.common**
- **app.schemas._text_utils**

此模組通過定義多個 Pydantic 資料結構來支持收發文功能的各項操作，並確保數據的一致性和有效性。
