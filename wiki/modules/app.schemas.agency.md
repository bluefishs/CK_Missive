---
title: app.schemas.agency
kg_entity_id: 12246
type: module
module_lines: 196
module_relations: 22
file_path: /app/app/schemas/agency.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.agency

## 概述
此模組包含 Pydantic 基本模型，用於定義政府機構的相關數據結構。這些模型涵蓋了機構的基本信息、更新信息、統計信息以及與其相關的操作請求和響應。

## 主要類別
1. **AgencyBase**: 代表機構的基本信息。
2. **AgencyCreate**: 用於創建新機構的數據模型。
3. **AgencyUpdate**: 用於更新現有機構信息的數據模型。
4. **Agency**: 包含機構的完整信息。
5. **AgencyWithStats**: 包含機構及其統計信息的數據模型。
6. **CategoryStat**: 表示某一類別的統計信息。
7. **AgencyStatistics**: 代表機構的統計數據模型。
8. **AgenciesResponse**: 用於返回多個機構的信息列表。
9. **SortOrder**: 定義排序順序的枚舉值。
10. **AgencyListQuery**: 包含查詢機構列表所需的參數。
11. **AgencyListResponse**: 返回機構列表的響應模型。
12. **AgencySuggestRequest**: 用於建議機構名稱的請求模型。
13. **AgencySuggestResponse**: 傳回機構名稱建議的響應模型。
14. **AssociationSummary**: 表示機構之間的關係概要。
15. **BatchAssociateRequest**: 用於批量建立機構關聯的請求模型。
16. **BatchAssociateResponse**: 返回批量關聯操作結果的響應模型。
17. **FixAgenciesRequest**: 用於修正機構信息的請求模型。
18. **FixAgenciesResponse**: 返回機構修正操作結果的響應模型。
19. **DataQualityStat**: 表示數據質量的統計信息。

## 公開函數
此模組中無公開函數。

## 依賴關係
- `app.schemas.common`: 提供常規的數據模型和工具函數。
- `app.schemas._text_utils`: 包含文本處理相關的功能。
