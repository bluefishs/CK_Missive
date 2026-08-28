---
title: app.schemas.agency
kg_entity_id: 12246
type: module
module_lines: 203
module_relations: 23
file_path: /app/app/schemas/agency.py
created: 2026-08-04
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.agency

## 概述
此模組包含 Pydantic schemas，用於定義政府機構相關的數據模型。這些模型涵蓋了從基本信息到統計數據的各種字段。

## 主要類別
- **AgencyBase**: 基本的政府機構信息。
- **AgencyCreate**: 用于創建新政府機構的數據模型。
- **AgencyUpdate**: 用于更新現有政府機構信息的數據模型。
- **Agency**: 完整的政府機構信息模型。
- **AgencyWithStats**: 包含統計數據的政府機構信息模型。
- **CategoryStat**: 分類統計數據模型。
- **AgencyStatistics**: 政府機構相關的統計數據模型。
- **AgenciesResponse**: 返回多個政府機構信息的響應模型。
- **SortOrder**: 排序順序定義。
- **AgencyListQuery**: 查詢政府機構列表的查詢條件模型。
- **AgencyListResponse**: 返回政府機構列表的響應模型。
- **AgencySuggestRequest**: 提供建議請求的數據模型。
- **AgencySuggestResponse**: 返回建議結果的響應模型。
- **AssociationSummary**: 聯系總結信息模型。
- **BatchAssociateRequest**: 批量聯系請求的數據模型。
- **BatchAssociateResponse**: 批量聯系響應的數據模型。
- **FixAgenciesRequest**: 修正政府機構信息的請求數據模型。
- **FixAgenciesResponse**: 修正政府機構信息的響應數據模型。
- **DataQualityStat**: 資料質量統計數據模型。

## 公開函數
無

## 依賴關係
- `app.schemas.common`
- `app.schemas._text_utils`
```

此 Markdown 文檔概括了 `app.schemas.agency` 模組的結構和主要類別，以及其依賴關係。
