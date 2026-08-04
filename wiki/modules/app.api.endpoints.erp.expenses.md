---
title: app.api.endpoints.erp.expenses
kg_entity_id: 15485
type: module
module_lines: 256
module_relations: 22
file_path: /app/app/api/endpoints/erp/expenses.py
created: 2026-08-04
updated: 2026-08-04
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.expenses

## 概述
此模組提供了費用報銷的 CRUD 端點，包括費用列表、新增費用、修改費用、審核費用等功能。相關的 QR/OCR/匯入匯出/收據/AI 功能已拆分至 `expenses_io.py`。

## 公開函數
- `list_expenses`: 列出所有費用報銷記錄。
- `create_expense`: 新增一筆費用報銷記錄。
- `get_expense_detail`: 根據ID獲取特定費用報銷詳情。
- `update_expense`: 更新指定費用報銷的狀態或信息。
- `approve_expense`: 批准費用報銷申請。
- `reject_expense`: 拒絕費用報銷申請。
- `grouped_expense_summary`: 統計分組費用概覽。
- `financial_overview`: 財務總覽。
- `case_finance_summary`: 个案財務概覽。
- `delete_expense`: 刪除指定費用報銷記錄。

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.schemas.erp.expense`
- `app.schemas.erp.requests`
- `app.services.expense_invoice_service`
```

此Markdown文件概括了`app.api.endpoints.erp.expenses`模組的主要功能和依賴關係，方便讀者快速了解該模組的功能和結構。
