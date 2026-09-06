---
title: app.api.endpoints.erp.financial_summary
kg_entity_id: 15496
type: module
module_lines: 213
module_relations: 23
file_path: /app/app/api/endpoints/erp/financial_summary.py
created: 2026-08-04
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.financial_summary

## 概述
這個 Python 模組包含一系列用於處理財務彙總的 API 端點，這些端點允許用戶獲取項目概要、公司概述、月度趨勢等信息。所有功能僅支持 POST 請求。

## 主要類別
無

## 公開函數
1. `get_project_summary`
2. `get_all_projects_summary`
3. `get_company_overview`
4. `get_monthly_trend`
5. `get_budget_ranking`
6. `export_expenses`
7. `export_ledger`
8. `get_aging_analysis`
9. `get_erp_overview`
10. `get_category_breakdown`

## 依賴關係
1. `app.core.dependencies`
2. `app.extended.models`
3. `app.schemas.common`
4. `app.extended.models.erp`
5. `app.extended.models.finance`
6. `app.extended.models.invoice`
7. `app.schemas.erp.financial_summary`
8. `app.extended.models.asset`
9. `app.extended.models.operational`
10. `app.services.erp.finance_export`
