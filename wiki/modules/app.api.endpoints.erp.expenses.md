---
title: app.api.endpoints.erp.expenses
kg_entity_id: 15485
type: module
module_lines: 259
module_relations: 22
file_path: /app/app/api/endpoints/erp/expenses.py
created: 2026-08-04
updated: 2026-08-24
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.expenses

## 概述
此模組提供了費用報銷的 CRUD (Create, Read, Update, Delete) 端點，包括費用列表、新增費用、獲取費用詳情、修改費用、審核費用、拒絕費用等操作。

## 主要類別
無

## 公開函數
- `list_expenses`: 列出所有費用報銷。
- `create_expense`: 新增費用報銷。
- `get_expense_detail`: 根據費用編號獲取費用詳情。
- `update_expense`: 修改費用報銷信息。
- `approve_expense`: 批准費用報銷。
- `reject_expense`: 拒絕費用報銷。
- `grouped_expense_summary`: 統計分組費用總結。
- `financial_overview`: 財務概覽。
- `case_finance_summary`: 案件財務總結。
- `delete_expense`: 刪除費用報銷。

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.schemas.erp.expense`
- `app.schemas.erp.requests`
- `app.services.expense_invoice_service`

IO 相關端點 (QR/OCR/匯入匯出/收據/AI) 已拆分至 `expenses_io.py`。
```

此 Markdown 文檔概括了 `app.api.endpoints.erp.expenses` 模組的主要功能和依賴關係。
