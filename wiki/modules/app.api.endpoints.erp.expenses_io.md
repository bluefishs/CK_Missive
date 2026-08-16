---
title: app.api.endpoints.erp.expenses_io
kg_entity_id: 30652
type: module
module_lines: 335
module_relations: 22
file_path: /app/app/api/endpoints/erp/expenses_io.py
created: 2026-08-17
updated: 2026-08-17
tags: [程式模組, auto-compiled]
confidence: medium
---
# app.api.endpoints.erp.expenses_io

## 概述
該模組提供了費用報銷相關的 API 端點，包括從 QR 碼碼創建費用報銷、自動對接發票、上傳費用憑證、OCR 文字識別、智慧掃描發票、下載費用模板、費用匯入和獲取費用收據等操作。

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
- `app.services.expense_invoice_service`
- `app.services.invoice_ocr_service`
- `app.services.invoice_recognizer`
- `app.services.ai.core.ai_config`
