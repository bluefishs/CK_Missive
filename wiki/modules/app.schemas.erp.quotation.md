---
title: app.schemas.erp.quotation
kg_entity_id: 17526
type: module
module_lines: 400
module_relations: 19
file_path: /app/app/schemas/erp/quotation.py
created: 2026-08-24
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.schemas.erp.quotation

## 概述
此 Python 模塊定義了與 ERP 報價/成本主檔相關的多個 Pydantic 模型，用於在系統之間進行數據傳輸和驗證。

## 主要類別
1. **ERPQuotationCreate** - 用於創建新的報價。
2. **ERPQuotationUpdate** - 用於更新現有報價的信息。
3. **ERPQuotationResponse** - 用於返回報價的響應信息。
4. **ERPQuotationListRequest** - 用於列出報價的請求參數。
5. **ERPProfitSummary** - 用於計算和展示報價的成本總結。
6. **ERPProfitTrendItem** - 用於表示報價成本趨勢項目。
7. **QuotationItemIn** - 用於包含報價項目的信息。
8. **QuotationIdRequest** - 用於通過報價ID進行請求。
9. **ReplaceItemsRequest** - 用於請求替換報價中的項目。
10. **ERPQuotationLegacyImportSkipped** - 用於記錄報價遺留導入中被跳過的條目。
11. **ERPQuotationLegacyImportResult** - 用於返回報價遺留導入的結果。
12. **ERPSignedImportUnmatched** - 用於處理簽名導入中的不匹配條目。
13. **ERPSignedImportResult** - 用於返回簽名導入的最終結果。
14. **ERPQuotationLegacyImportConflict** - 用於記錄報價遺留導入中遇到的衝突。

## 公開函數
無公開函數。

## 依賴關係
- `app.schemas.common`
- `app.schemas._text_utils`
- `app.schemas._year`
