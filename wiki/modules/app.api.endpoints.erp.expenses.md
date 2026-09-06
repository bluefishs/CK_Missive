---
title: app.api.endpoints.erp.expenses
kg_entity_id: 15485
type: module
module_lines: 270
module_relations: 23
file_path: /app/app/api/endpoints/erp/expenses.py
created: 2026-08-04
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.expenses

## 概述
該模組提供了費用報銷的 CRUD 端點，包括費用列表、新增費用、修改費用、審核費用等功能。

## 主要函數
- `list_expenses`
- `create_expense`
- `get_expense_detail`
- `update_expense`
- `approve_expense`
- `reject_expense`
- `grouped_expense_summary`
- `financial_overview`
- `case_finance_summary`
- `delete_expense`

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.schemas.erp.expense`
- `app.schemas.erp.requests`
- `app.services.erp.expense_invoice`
```

此 Markdown 文檔概括了模組的功能和依賴關係，方便讀者快速了解該模組的主要內容。
