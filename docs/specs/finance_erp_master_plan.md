# 公司級 ERP 財務模組：主藍圖與任務進度統整 (Master Plan)

> **建立日期**: 2026-03-21
> **最後更新**: 2026-03-21 (v5.1.2 架構審計修復)
> **角色定位**: 作為團隊開發之唯一真實來源 (SSOT) 狀態版
> **衍生自**: `invoice_system_architecture_plan.md` (v2.0)

## 📌 一、架構核心準則 (Architecture Guidelines)

為確保 ERP 與財務模組能負載未來的 Agent 審查與公司金流，所有新開發必須遵循以下規範：

1. **資料模型 (Model)**：全面使用 `case_code` 作為軟參照橋樑，嚴禁濫用外鍵綁定，以確保一般營運支出等非專案金流能順利登記於 `FinanceLedger`。
2. **多態關聯 (Polymorphic Reference)**：`FinanceLedger` 依靠 `source_type` 及 `source_id` 反查來源憑證 (`ExpenseInvoice`, `ERPBilling` 等)。
3. **分層設計 (Layered Architecture)**：
   - **Schema**: 定義於 `schemas/erp`，嚴格攔截非法輸入。
   - **Endpoint**: 封裝路由與 Request 校驗，嚴禁直接引入 `db.add`。
   - **Service**: 處理核心商務邏輯 (`ExpenseInvoiceService`, `FinanceLedgerService`)。
   - **Repository**: 使用 `AsyncSession` 的持久化操作。

## 📊 二、開發進度儀表板 (Status Dashboard)

**Phase 1: 資料基礎核心建立 (Data Foundation)** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **1-1** ~ **1-5** | Model、Schema、Service、Repository 非同步架構底層重建 | ✅ 完成 |
| **1-6** | API 端點建立 (`expenses.py`, `ledger.py`, `financial_summary.py`) | ✅ 完成 |
| **1-7** | Alembic 遷移腳本 (`3fc21c653f96`) | ✅ 完成 |
| **1-8** | 單元測試 (33 tests, `test_expense_invoice.py`) | ✅ 完成 |
| **1-9** | SSOT 合規、Decimal 精度修正、EXPENSE_CATEGORIES Literal | ✅ 完成 |

**Phase 2: QR Code 辨識引擎 (QR Engine)** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **2-1** | 依賴建立 (`opencv-python-headless`, `pyzbar`) | ✅ 完成 |
| **2-2** | `qr_scanner.py` 純函數實作 + `parse_qr_data()` 服務內建 | ✅ 完成 |
| **2-3** | `ExpenseInvoiceService.create_from_qr()` QR 掃描建立 | ✅ 完成 |

**Phase 2.5: 財政部電子發票自動同步 (MOF E-Invoice Sync)** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **2.5-1** | `MofApiClient` — HMAC-SHA256 簽章 + 買方發票查詢 + 明細查詢 | ✅ 完成 |
| **2.5-2** | `EInvoiceSyncService` — 自動同步 + 重複過濾 + 收據關聯 | ✅ 完成 |
| **2.5-3** | `EInvoiceSyncLog` Model + Alembic 遷移 (`20260321a001`) | ✅ 完成 |
| **2.5-4** | APScheduler 每晚 01:00 排程 (env-gated: MOF_APP_ID) | ✅ 完成 |
| **2.5-5** | API 端點 (`/erp/einvoice-sync/`: sync, pending-list, upload-receipt, sync-logs) | ✅ 完成 |
| **2.5-6** | Schema (`einvoice_sync.py`: 5 classes) | ✅ 完成 |
| **2.5-7** | 單元測試 (24 tests, `test_einvoice_sync.py`) | ✅ 完成 |

**Phase 3: Agent 整合 + 主動警報** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **3-1** | `tool_definitions.py` 註冊 get_financial_summary, get_expense_overview, check_budget_alert (3 tools) | ✅ 完成 |
| **3-2** | `tool_executor_domain.py` 實作工具邏輯 + `agent_tools.py` dispatch 接線 | ✅ 完成 |
| **3-3** | `proactive_triggers_erp.py` 預算超支掃描 (`check_budget_overrun`) + 待核銷提醒 (`check_pending_receipts`) | ✅ 完成 |
| **3-4** | Agent 整合測試 (`test_finance_agent_tools.py`, 19 tests) | ✅ 完成 |

**Phase 3.5: 架構審計修復** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **C02** | `ExpenseInvoiceService.create()` 雙重帳本修復 — status 改為 pending，移除 create 時帳本寫入 | ✅ 完成 |
| **W03** | `update()` 方法加入 `ExpenseInvoiceUpdate` 型別提示 | ✅ 完成 |
| **W07** | `get_category_breakdown()` 從 Python 迴圈改為 SQL GROUP BY | ✅ 完成 |
| **W08** | `FinanceLedgerService.delete()` 補上 `commit()` | ✅ 完成 |

**Phase 4: 前端整合** — ⏳ **待辦**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **4-1** | 前端型別定義 (`types/erp.ts`) + Endpoint 常數 | ⏳ 待辦 |
| **4-2** | React Query Hooks (expenses, ledger, financialSummary, einvoiceSync) | ⏳ 待辦 |
| **4-3** | ERP 費用報銷頁面 + 待核銷手機清單 | ⏳ 待辦 |
| **4-4** | 專案財務儀表板 (ProjectFinancialSummary) | ⏳ 待辦 |
| **4-5** | 全公司財務總覽頁 | ⏳ 待辦 |
| **4-6** | 收據拍照上傳 (PWA / Mobile Web) | ⏳ 待辦 |

**Phase 5: 進階功能** — ⏳ **待辦**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **5-1** | 匯出報表 (Excel / PDF) | ⏳ 待辦 |
| **5-2** | 定期對帳自動化 (排程) | ⏳ 待辦 |
| **5-3** | ERPBilling 收款 → Ledger 自動入帳 | ⏳ 待辦 |

## 📐 三、環境配置要求

### 財政部電子發票 API (Phase 2.5)

在 `.env` 中設定以下環境變數以啟用自動同步：

```bash
# 財政部電子發票 API 設定 (取得方式: einvoice.nat.gov.tw 申請)
MOF_APP_ID=你的AppID
MOF_API_KEY=你的API金鑰
COMPANY_BAN=公司八碼統編

# 收據影像儲存路徑 (預設: uploads/receipts)
RECEIPT_UPLOAD_DIR=uploads/receipts
```

**未設定 `MOF_APP_ID` 時排程任務不會啟用**，其餘功能 (手動同步、收據上傳) 仍可使用。

## 🏗️ 四、新增模組清單 (Phase 2.5)

| 類型 | 檔案 | 說明 |
|------|------|------|
| Model | `extended/models/einvoice_sync.py` | EInvoiceSyncLog 同步批次記錄 |
| Model | `extended/models/invoice.py` | +4 欄位 (receipt_image_path, mof_*) |
| Service | `services/einvoice/mof_api_client.py` | 財政部 API 客戶端 (HMAC-SHA256) |
| Service | `services/einvoice/einvoice_sync_service.py` | 同步服務 (下載+比對+入庫+收據) |
| Schema | `schemas/erp/einvoice_sync.py` | 5 classes |
| Endpoint | `api/endpoints/erp/einvoice_sync.py` | 4 POST 端點 |
| Migration | `alembic/versions/20260321a001_...py` | 新表 + 欄位擴充 |
| Scheduler | `core/scheduler.py` | +einvoice_sync_job (每晚 01:00) |
| Test | `tests/unit/test_einvoice_sync.py` | 24 tests |

## 🔗 五、API 端點一覽

### 費用報銷 (`/erp/expenses/`)
| 端點 | 說明 |
|------|------|
| `POST /list` | 費用發票列表 (多條件查詢) |
| `POST /create` | 建立報銷發票 |
| `POST /detail` | 取得發票詳情 |
| `POST /update` | 更新報銷發票 |
| `POST /approve` | 審核通過 (自動寫入帳本) |
| `POST /reject` | 駁回報銷 |
| `POST /qr-scan` | QR Code 掃描建立 |

### 電子發票同步 (`/erp/einvoice-sync/`)
| 端點 | 說明 |
|------|------|
| `POST /sync` | 手動觸發同步 (管理員) |
| `POST /pending-list` | 待核銷清單 (手機端) |
| `POST /upload-receipt` | 上傳收據照片並關聯 |
| `POST /sync-logs` | 同步歷史記錄 |

### 統一帳本 (`/erp/ledger/`)
| 端點 | 說明 |
|------|------|
| `POST /list` | 帳本記錄列表 |
| `POST /create` | 手動記帳 |
| `POST /detail` | 帳本詳情 |
| `POST /balance` | 專案收支餘額 |
| `POST /category-breakdown` | 分類拆解 |
| `POST /delete` | 刪除 (僅手動記帳) |

### 財務彙總 (`/erp/financial-summary/`)
| 端點 | 說明 |
|------|------|
| `POST /project` | 單一專案財務彙總 |
| `POST /projects` | 所有專案一覽 |
| `POST /company` | 全公司財務總覽 |

本規劃書已取代所有過渡用之草案，為當前唯一基準。
