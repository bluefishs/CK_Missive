---
title: app.schemas.erp.quotation
kg_entity_id: 17526
type: module
module_lines: 502
module_relations: 21
file_path: /app/app/schemas/erp/quotation.py
created: 2026-08-24
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.erp.quotation

## 概述
此 Python 模組定義了與 ERP 報價和成本主檔相關的多個 Pydantic 模型，用於表示不同類型的報價數據及其操作。

## 主要類別
1. **ERPQuotationCreate**: 用於創建新的報價。
2. **ERPQuotationUpdate**: 用於更新現有報價的信息。
3. **ERPQuotationResponse**: 用於返回報價的響應信息。
4. **ERPQuotationListRequest**: 用於列出報價的請求參數。
5. **ERPProfitSummary**: 用於表示報價的成本總結。
6. **ERPProfitTrendItem**: 用於表示報價成本趨勢項目。
7. **QuotationItemIn**: 用於表示報價項目的輸入信息。
8. **QuotationIdRequest**: 用於通過報價ID獲取相關信息的請求參數。
9. **ReplaceItemsRequest**: 用於替換報價項目的請求參數。
10. **ERPQuotationLegacyImportSkipped**: 用於表示從舊版本導入時被跳過的報價信息。
11. **ERPQuotationLegacyImportResult**: 用於表示從舊版本導入報價的結果。
12. **ERPSignedImportUnmatched**: 用於表示簽名導入未匹配的報價信息。
13. **ERPSignedImportResult**: 用於表示簽名導入報價的結果。
14. **ERPQuotationLegacyImportConflict**: 用於表示從舊版本導入時發生衝突的報價信息。
15. **ERPQuotationTemplateMeta**: 用於表示報價模板元數據。
16. **ERPQuotationDocumentData**: 用於表示報價文檔數據。

## 公開函數
無

## 依賴關係
- `app.schemas.common`
- `app.schemas._text_utils`
- `app.schemas._year`
