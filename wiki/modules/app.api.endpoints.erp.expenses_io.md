---
title: app.api.endpoints.erp.expenses_io
kg_entity_id: 30652
type: module
module_lines: 335
module_relations: 23
file_path: /app/app/api/endpoints/erp/expenses_io.py
created: 2026-08-17
updated: 2026-09-07
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.expenses_io

## 概述
此模組包含與費用報銷相關的各種端點，支持通過 QR 碼、OCR 認識、智慧掃描等方式進行費用收據的自動化處理和管理。此外還提供匯入和導出費用報銷數據的功能。

## 公開函數
- `create_from_qr`
- `auto_link_einvoice`
- `upload_expense_receipt`
- `ocr_parse_invoice`
- `smart_scan_invoice`
- `download_expense_template`
- `import_expenses`
- `get_receipt_image`
- `suggest_category`

## 依賴關係
- `app.core.dependencies`
- `app.extended.models`
- `app.schemas.common`
- `app.schemas.erp.expense`
- `app.schemas.erp.requests`
- `app.services.ai.core.ai_config`
- `app.services.erp.expense_invoice`
- `app.services.erp.invoice_ocr_service`
- `app.services.erp.invoice_recognizer`
