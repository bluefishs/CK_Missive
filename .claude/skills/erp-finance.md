---
name: erp-finance
description: ERP 財務模組開發規範 — 報價/開票/請款/帳本/費用報銷/資產管理
version: 1.0.0
category: domain
triggers:
  - ERP
  - 報價
  - 開票
  - 請款
  - 帳本
  - 費用
  - 資產
  - quotation
  - invoice
  - billing
  - ledger
  - expense
  - asset
  - vendor_payable
updated: '2026-04-09'
---

# ERP 財務模組開發規範


## 模組架構概覽

ERP 財務流程為單向管線，各階段依序觸發：

```
Quotation (報價) → Invoice (開票) → Billing (請款)
                                        ↓
                               VendorPayable (應付)
                                        ↓
                                  Ledger (帳本)
```

所有模組透過 `case_code` 橋接 PM 案件與 KG 知識圖譜。

---

## 檔案配置

### 型別定義 (SSOT)

- **前端**: `frontend/src/types/erp.ts` (1080L, 唯一來源)
- **後端**: `backend/app/schemas/erp/` (Pydantic Schema)

### 服務層 (`backend/app/services/erp/`)

| 服務 | 說明 |
|------|------|
| `quotation_service.py` | 報價 CRUD (343L) |
| `quotation_service_io.py` | 報價匯出入 (243L) |
| `invoice_service.py` | 開票管理 |
| `billing_service.py` | 請款管理 |
| `vendor_payable_service.py` | 廠商應付帳款 |
| `asset_service.py` | 資產 CRUD (217L) |
| `asset_service_io.py` | 資產匯出入 (393L) |
| `operational_service.py` | 營運帳目 (預算+審批+分類) |

### API 層 (`backend/app/api/endpoints/erp/`)

12+ 端點檔案：quotations, invoices, billings, vendor_payables, vendor_accounts, client_accounts, assets, expenses, expenses_io, operational, ledger, financial_summary, einvoice_sync

### 費用報銷獨立服務 (`backend/app/services/`)

| 服務 | 說明 |
|------|------|
| `expense_invoice_service.py` | Facade (207L, 委派式) |
| `expense_approval_service.py` | 審核工作流 (多層審批+預算聯防) |
| `expense_import_service.py` | 匯入匯出 (QR+Excel+電子發票) |

---

## 強制規則

### 1. 帳本冪等

每筆 ERP 交易同步寫入 `FinanceLedger`，使用 `source_type + source_id` 做重複防護。刪除交易時必須同步刪除對應帳本記錄。

### 2. 併發審批鎖

審批操作必須使用 `SELECT ... FOR UPDATE` 鎖定目標行，防止多人同時審批同一筆記錄。批次審批 API 需在單一交易內完成。

### 3. 軟刪除

`ERPQuotation` 使用 `deleted_at` 欄位實現軟刪除。查詢時必須加上 `filter(deleted_at.is_(None))` 條件。

### 4. 金額驗證

Schema 層強制 `amount >= tax_amount`。前端送出前也需驗證。

### 5. 三方金額同步

`quotation.total`、`billing.total`、`invoice.total` 三者不一致時，前端顯示 Alert 警告。後端成案審計記錄差異。

### 6. attribution_type 三面向

費用報銷來源分三類：`manual`（手動輸入）、`scan`（QR/OCR 掃描）、`einvoice`（財政部電子發票同步）。建立時必須標記來源。

---

## 費用報銷三輸入流程

### ERPExpenseCreatePage 步驟式流程

1. **手動輸入** — 直接填寫表單欄位
2. **智慧掃描** — QR Code 解碼 + OCR 辨識，自動帶入欄位
3. **財政部同步** — 透過 MOF API (HMAC-SHA256) 拉取電子發票

三種輸入合一頁面，使用 Steps 進度指示。圖片壓縮 (`imageUtils.ts`) 處理行動端拍照。

### ExpenseQRCode 行動核銷入口

`ExpenseQRCode` 元件產生案件核銷 QR Code，支援下載/複製/列印。掃描後導向對應案件的費用新增頁面。

---

## case_code 跨模組橋接

| 模組 | case_code 用途 |
|------|---------------|
| PM Cases | 建案時產生，跨模組主鍵 |
| ERP Quotations | 綁定報價到案件 |
| contract_projects | 成案後產生 project_code |
| KG 知識圖譜 | 透過 case_code 關聯實體 |
| 費用報銷 | 歸屬案件 (case_code 分組) |

---

## Domain Events

ERP 模組產出 4 類事件，由 EventBus 分發：
- `expense.created` / `expense.approved` — 費用報銷
- `billing.created` — 請款
- `invoice.created` — 開票

事件觸發即時入圖 + 財務異常偵測 (3 規則)。

---

## 常見陷阱

1. **FK 方向**: `ERPBilling.invoice_id` 已移除，改單向關聯
2. **Item 欄位名**: 使用 `item_name` (非 description)、`qty` (非 quantity)
3. **帳本對帳**: 排程任務 `ledger_reconciliation` 自動比對，勿手動修帳本
4. **資產照片**: `photo_path` 支援 Gemma 4 Vision 描述，上傳需壓縮
