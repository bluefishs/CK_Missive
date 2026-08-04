---
title: app.api.endpoints.erp.financial_summary
kg_entity_id: 15496
type: module
module_lines: 199
module_relations: 22
file_path: /app/app/api/endpoints/erp/financial_summary.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.financial_summary

## 概述
此模組提供了跨模組財務彙總的 API 端點，僅支持 POST 方法。這些端點用於獲取項目概要、公司概述、月度趨勢等財務相關數據。

## 公開函數
- `get_project_summary`
- `get_all_projects_summary`
- `get_company_overview`
- `get_monthly_trend`
- `get_budget_ranking`
- `export_expenses`
- `export_ledger`
- `get_aging_analysis`
- `get_erp_overview`

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.extended.models.erp`
- `app.extended.models.finance`
- `app.extended.models.invoice`
- `app.schemas.erp.financial_summary`
- `app.services.finance_export_service`
- `app.extended.models.asset`
- `app.extended.models.operational`
