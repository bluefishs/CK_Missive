# 公司級 ERP 財務模組：主藍圖與任務進度統整 (Master Plan)

> **建立日期**: 2026-03-21
> **最後更新**: 2026-03-22 (v5.1.15 Phase 8~14 + ERP-PM 廠商整合 + QR/行動裝置評估)
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

**Phase 3.6: 安全加固與 Repository 合規** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **S01** | 20 個 ERP 端點全部加上認證保護 (`require_auth` / `require_admin`) | ✅ 完成 |
| **R01** | 新增 `EInvoiceSyncRepository` (16 DB 操作從 Service 遷移) | ✅ 完成 |
| **R02** | 擴展 `ExpenseInvoiceRepository` (+create_with_items/update_fields/update_status) | ✅ 完成 |
| **R03** | 擴展 `LedgerRepository` (+create_entry/delete_entry) | ✅ 完成 |
| **R04** | 擴展 `FinancialSummaryRepository` (+get_case_codes_paginated/get_top_expense_projects) | ✅ 完成 |
| **R05** | 4 Service 直接 DB 操作 39→0 | ✅ 完成 |
| **R06** | `approve()` 改用 `ledger_service.record_from_expense()` (解耦跨 Service 依賴) | ✅ 完成 |
| **T01** | 6 個 API response interface 統一至 `types/erp.ts` (SSOT) | ✅ 完成 |

**Phase 4: 前端整合** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **4-1** | 前端型別定義 (`types/erp.ts` +25 型別 +6 response interfaces) + Endpoint 常數 (+20 端點) | ✅ 完成 |
| **4-2** | React Query Hooks (18 hooks: expenses 7, ledger 6, financialSummary 3, einvoiceSync 4) | ✅ 完成 |
| **4-3** | ERP 費用報銷頁面 (列表+詳情+編輯+建立+QR掃描+審核/駁回) | ✅ 完成 |
| **4-4** | 統一帳本頁面 (列表+手動記帳+分類拆解+刪除保護) | ✅ 完成 |
| **4-5** | 財務儀表板 (全公司總覽+專案一覽+預算警報+支出分類) | ✅ 完成 |
| **4-6** | 電子發票同步管理 (同步觸發+待核銷+收據上傳+歷史) | ✅ 完成 |
| **4-7** | 路由三方同步 (types.ts + AppRouter.tsx + init_navigation_data.py) | ✅ 完成 |

**Phase 5: 進階功能** — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **5-1** | 收據影像上傳/預覽 (Upload+Image+FormData+相對路徑+POST-only 取圖) | ✅ 完成 |
| **5-2** | 發票 OCR 自動辨識 (`InvoiceOCRService` + Tesseract + confidence + 前端 Modal) | ✅ 完成 |
| **5-3** | 匯出 Excel 報表 (`FinanceExportService` + 費用/帳本明細 + openpyxl 樣式) | ✅ 完成 |
| **5-4** | 多幣別支援 (currency+original_amount+exchange_rate, 5幣別, Schema自動換算, 帳本/匯出/前端全通) | ✅ 完成 |
| **5-5** | 多層審核狀態機 (pending→manager_approved→finance_approved→verified, 30K門檻, 64 tests) | ✅ 完成 |
| **5-6** | ERPBilling 收款確認 → Ledger 自動入帳 (paid 狀態觸發 income 記錄, 防重複入帳, 67 tests) | ✅ 完成 |
| **5-7** | 預算聯防控制 (approve→verified 前檢查 ERPQuotation.budget_limit, >80% 預警放行, >100% 攔截, 75 tests) | ✅ 完成 |

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
| `POST /monthly-trend` | 月度收支趨勢 (N 個月) |
| `POST /budget-ranking` | 預算使用率排行 (Top N) |
| `POST /export-expenses` | 匯出費用報銷 Excel |
| `POST /export-ledger` | 匯出帳本收支 Excel |

## 🔮 六、Phase 5 進階優化架構指南

### 5-1. 實體附件儲存 (Attachment Storage)
**目標**: 處理費用報銷圖片與收據上傳。
- **隔離儲存**：嚴格禁止將二進位檔轉 Base64 塞入資料庫。
- **作法**：實作專屬 `StorageService`，將 `receipt_image_path` 指向本地的 `/storage/receipts` 或對接 S3 Bucket。端點僅返回可預覽的 Signed URL。

### 5-2. 發票 OCR 自動辨識 (Tesseract)
**目標**: 從圖檔文字萃取發票資訊。
- 於 `qr_scanner.py` 周邊建立 `ocr_extractor.py` 作為純函數。
- OCR 具有機率性誤判（如 8 變成 B），API 返回結果須加上 `confidence_score`。
- 前端設計為「預填入表單供人類二次確認」，切勿直接產生 `verified` 狀態發票，應維持在 `pending`。

### 5-4. 多幣別支援引擎 (Multi-Currency)
**目標**: 支援 TWD, USD, CNY 等報銷。
- **保留原始金額**：擴充 `original_amount` 與 `currency` 欄位。
- **統一會計本位幣**：`amount` 欄位始終保持公司營運基期幣別 (TWD)。新建發票時提供 `exchange_rate` 做即時轉換。

### 5-5. 多層審核狀態機 (Approval Workflow State-Machine) ✅
**已實作完成**。
- **狀態**: `pending` → `manager_approved` → `finance_approved` → `verified` (+ `rejected` 任意階段可駁回)
- **金額門檻**: `APPROVAL_THRESHOLD = 30,000 TWD`
  - ≤30K: 二級審核 (`pending → manager_approved → verified`)
  - >30K: 三級審核 (`pending → manager_approved → finance_approved → verified`)
- **帳本入帳**: 僅 `verified` 終態觸發 `FinanceLedger` 自動入帳
- **流轉規則**: `APPROVAL_TRANSITIONS` dict 定義合法狀態轉換，防非法跳轉
- **前端**: 按鈕文字動態切換 (主管核准/財務核准/最終核准)，狀態 Tag 顏色區分 6 階段
- **測試**: 64 unit tests (含邊界值 30K/30001)

### 5-7. 預算聯防控制 (Budget Audit Control) ✅
**已實作完成**。
- **觸發點**: `approve()` 進入 `verified` 前自動檢查 `ERPQuotation.budget_limit`
- **門檻**: `BUDGET_WARNING_PCT = 80%` (預警放行) / `BUDGET_BLOCK_PCT = 100%` (攔截審核)
- **邏輯**: 累計支出 + 本筆金額 → 計算使用率 → 攔截/預警/放行
- **API 層**: 預警訊息透過 `_budget_warning` 動態屬性附加至 response.message
- **測試**: 75 unit tests (含邊界值 80%/100%)

---

## 🔗 七、v8.0 跨模組整合戰略 (Cross-Module Integration)

### 戰略 A: AR/AP 自動拋轉 ✅
- **AR (應收)**: `ERPBillingService.update()` → `record_from_billing()` (Phase 5-6)
- **AP (應付)**: `ERPVendorPayableService.update()` → `record_from_vendor_payable()` (v1.1.0)
  - 付款狀態 `unpaid → paid` 自動寫入 `FinanceLedger` 支出記錄
  - 透過 `ERPQuotation` 反查 `case_code` 歸屬專案

### 戰略 B: 預算聯防控制 ✅
- 已在 Phase 5-7 實作完成，詳見上方。

### 戰略 C: 統一 BI 中樞 ✅
- **Excel 匯出**: `FinanceExportService` 費用/帳本明細 openpyxl 匯出 (Phase 5-3)
- **BI 圖表**: 前端 recharts 專案利潤排名 (BarChart Top 15) + 支出分類分布 (PieChart)

---

## 🚀 八、Phase 7: 戰略強化 (Strategic Enhancement)

### Phase 7-A: 前端預算警報 UX 升級 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **7A-1** | `ERPExpenseListPage` 審核按鈕改用 `Modal.warning()` / `Modal.error()` AlertDialog | ✅ 完成 |
| **7A-2** | `ERPExpenseDetailPage` 同步升級預算警報 UX | ✅ 完成 |
| **7A-3** | 錯誤訊息關鍵字匹配 (超支/預算/budget → AlertDialog, 其餘 → toast) | ✅ 完成 |

**設計決策**:
- **預算預警 (80~100%)**: `Modal.warning()` — 標題「預算警告」，放行但提醒
- **預算超支 (>100%)**: `Modal.error()` — 標題「預算超支攔截」，HTTP 400 阻止審核
- **錯誤流**: Backend `ValueError` → `HTTPException(400)` → Frontend `ApiException` → Component catch → `Modal.error()`

### Phase 7-B: ERP Repository 合規修正 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **7B-1** | `ERPQuotationService` create/update/delete 改用 `repo.create()` / `repo.update()` / `repo.delete()` | ✅ 完成 |
| **7B-2** | `ERPInvoiceService` create/update/delete 改用 Repository 方法 | ✅ 完成 |
| **7B-3** | `ERPBillingService` create/delete 改用 Repository (update 保留 — 含 AR 自動拋轉邏輯) | ✅ 完成 |
| **7B-4** | `ERPVendorPayableService` create/delete 改用 Repository (update 保留 — 含 AP 自動拋轉邏輯) | ✅ 完成 |

**修復統計**: 4 Services × 8 violations → 0 直接 DB 操作殘留

### Phase 7-C: NemoClaw 夜間預算掃描器 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **7C-1** | `ERPTriggerScanner` 擴充: 掃描 80~100% 區間專案發出預警通知 | ✅ 完成 |
| **7C-2** | 通知管道整合 (Notification + LINE Push) | ✅ 完成 |

### Phase 7-D: Dashboard 擴展 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **7D-1** | 月度收支趨勢 — API `POST /monthly-trend` + Repository `get_monthly_trend()` + 空月補零 | ✅ 完成 |
| **7D-2** | 預算使用率排行 — API `POST /budget-ranking` + Repository `get_budget_ranking()` + 案名補充 | ✅ 完成 |
| **7D-3** | 匯出功能 — `POST /export-expenses` + `POST /export-ledger` → Excel 下載 | ✅ 完成 |
| **7D-4** | 前端圖表 — recharts BarChart (利潤排名) + PieChart (支出分類) + LineChart (月度趨勢) | ✅ 完成 |
| **7D-5** | 單元測試 — `test_financial_dashboard.py` (17 tests: 月度趨勢/預算排行/批量彙總/Schema驗證) | ✅ 完成 |

### Phase 7-E: 效能與測試強化 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **P01** | N+1 查詢修復 — `get_batch_project_summaries()` 批量方法 (3 queries 取代 N×3) | ✅ 完成 |
| **I01** | ORM 複合索引 — `idx_ledger_case_date`, `idx_ledger_source` | ✅ 完成 |
| **I02** | ORM 複合索引 — `idx_einvoice_buyer`, `idx_einvoice_query_date` | ✅ 完成 |
| **M01** | Alembic 遷移 `20260322a002` — 4 個複合索引 | ✅ 完成 |
| **D01** | 規範同步 — `architecture.md` + `skills-inventory.md` ERP 模組盤點更新 | ✅ 完成 |
| **D02** | 前端頁面測試 — `ERPPages.test.tsx` (8 tests, 5 pages smoke tests) | ✅ 完成 |

---

### Phase 8: 安全加固與原子性修復 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **8-1** | approve/reject 端點改用 `require_permission("projects:write")` + 禁止自我審核 (`user_id == current_user.id`) | ✅ 完成 |
| **8-3** | `ledger_repository.create_entry()` 改 `flush()` 確保交易原子性 (由 service 層控制 commit) | ✅ 完成 |
| **9-2** | ERPExpenseDetailPage 收據圖片改用 `expensesApi.receiptImage()` POST API + Blob URL (移除硬編碼 URL) | ✅ 完成 |
| **8-4** | Docker volume mount 收據儲存 — 已存在 (`./backend/uploads:/app/uploads`) 確認無需變更 | ✅ 已驗證 |

### Phase 13: PM → ERP 整合導航 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **13-1** | PMCaseDetailPage ERP Tab 擴充 — 財務摘要 (預算/支出/收入/淨額/使用率/預算條) + 關聯報價 + 最近費用 | ✅ 完成 |
| **13-2** | `expense_invoice_service.create()` 加 `_validate_case_code()` — 三層驗證 (ContractProject → PMCase → ERPQuotation) | ✅ 完成 |

### Phase 14: ERP 頁面強化 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **14-1** | ERPExpenseListPage + ERPLedgerPage 案號篩選改為專案下拉 (useProjectsDropdown + showSearch) | ✅ 完成 |
| **14-1b** | ERPExpenseListPage 支援 URL `?case_code=` 預填篩選 (PM→ERP 導航銜接) | ✅ 完成 |
| **14-2** | PMCaseListPage 加預算使用率欄位 — useAllProjectsSummary 批次查詢 + 色彩 Tag | ✅ 完成 |

### Phase 14-D: ERP-PM 廠商資訊整合 — ✅ **完成**

| 任務代碼 | 任務內容 | 狀態 |
|---------|---------|------|
| **14D-A** | Model 層 vendor_id FK — ERPVendorPayable, ExpenseInvoice, FinanceLedger 加硬參照 | ✅ 完成 |
| **14D-B** | Alembic 遷移 `20260322a003` — 3 表加 vendor_id + 索引 + 回填 | ✅ 完成 |
| **14D-C** | Service 自動配對 — vendor_code/seller_ban → vendor_id 解析 (3 Services) | ✅ 完成 |
| **14D-D** | 廠商財務彙總 API — `VendorService.get_financial_summary()` + `POST /{vendor_id}/financial-summary` | ✅ 完成 |
| **14D-E** | 前端整合 — endpoint 常數 + `VendorFinancialSummary` 型別 + `useVendorFinancialSummary` Hook | ✅ 完成 |
| **14D-F** | Schema SSOT — `VendorFinancialSummary` + `VendorFinancialSummaryRequest` 定義於 `schemas/erp/vendor_financial.py` | ✅ 完成 |

**設計決策**:
- **單一主資料策略**: `PartnerVendor` (PM) 為唯一廠商主檔，ERP 各表透過 `vendor_id` FK 參照
- **自動配對**: `vendor_code == seller_ban` (統編) 慣例，新建時自動解析，遷移時回填
- **向後相容**: `vendor_id` 為 nullable FK + `SET NULL`，不破壞現有軟參照流程
- **財務彙總**: 3 SQL 聚合查詢 (應付帳款 + 費用報銷 + 帳本支出)，由 vendor_id JOIN

### Phase 15: 進階整合 + LINE Login — 🔜 **規劃中**

#### 軌道 A：LINE Login 整合 (P0)

| Phase | 優先級 | 主題 | 關鍵交付 |
|-------|--------|------|---------|
| **M1-A** | P0 | User Model 擴充 | `line_user_id`, `line_display_name` + Alembic 遷移 + 索引 |
| **M1-B** | P0 | LINE OAuth API | `AuthProvider.LINE` + `POST /auth/line/callback` + `POST /auth/line/bind` |
| **M1-C** | P0 | 前端 LINE Login | LoginPage LINE 按鈕 + authService.lineLogin() + OAuth 流程 |
| **M2** | P0 | LIFF QR 掃描 | LIFF Compact App + `liff.scanCodeV2()` → `/erp/expenses/qr-scan` |
| **M3** | P1 | 收據拍照上傳 | LIFF Full 模式 + 相機/相簿 → `/erp/einvoice-sync/upload-receipt` |
| **M4** | P1 | Flex Message 簽核 | 待審核推播 + Postback 一鍵核准/駁回 |
| **M5** | P2 | LIFF 費用查詢 | LIFF Tall 模式 + 費用清單 + 餘額查詢 |

#### 軌道 B：技術債清理 (P1)

| Phase | 優先級 | 主題 | 關鍵交付 |
|-------|--------|------|---------|
| **G01** | P1 | 全公司餘額邏輯 | `FinanceLedgerService.get_balance()` 實作全公司收支彙總 |
| **G05** | P0 | Alembic 遷移 | 執行 `alembic upgrade head` 套用 20260322a003 |
| **G07** | P2 | vendorPayablesApi 對齊 | 補齊完整 CRUD 方法 (目前僅 10L) |
| **14-3** | P1 | 統一財務 API | 新增合併端點 (expenses+ledger+milestone 一次回傳) |

#### 軌道 C：進階功能 (P2)

| Phase | 優先級 | 主題 | 關鍵交付 |
|-------|--------|------|---------|
| **15-1** | P2 | 預算變更歷史 | 新增 BudgetHistory 表追蹤預算修正紀錄 |
| **15-2** | P2 | Agent 整合工具 | 新增 `get_project_health_summary()` 跨模組 Agent 工具 |
| **15-3** | P3 | 預算預測 | 基於歷史支出速率預測專案預算消耗時間 |
| **15-4** | P2 | StorageService 抽象 | S3/MinIO/Local 三態切換，收據影像脫離本地 |

---

## 🗺️ 九、長線發展藍圖 (Final Roadmap)

詳見 `specs/finance_erp_final_roadmap.md` — 未來三季度 (Q2~Q4) 戰略指引。

| 季度 | 主題 | 重點 |
|------|------|------|
| **Q2** | 前台體驗與 BI 儀表板 | 夜間吹哨者排程、損益表、月度趨勢、預算排行 |
| **Q3** | 實體解耦與 AI 助理 | StorageService 抽象、OCR 強化、Agent 財務問答 |
| **Q4** | 行動決策圈 | LINE LIFF QR 掃描、卡片式簽核、AI 異常偵測 |

三大戰略支柱: **可見性 (Visibility)** → **可觸及 (Accessibility)** → **可預測 (Predictability)**

### 📱 行動裝置整合評估 (2026-03-22)

**評估四方案**:

| 方案 | 優勢 | 劣勢 | 推薦 |
|------|------|------|------|
| **LINE LIFF App** | 既有 LINE Bot 基礎設施、免安裝、台灣普及率高 | 需 LIFF SDK 整合、LINE Login 帳號綁定 | ⭐ **P0 推薦** |
| **PWA** | 跨平台、瀏覽器原生、可離線 | QR 掃描需 getUserMedia、推播需 Service Worker | P1 備選 |
| **Telegram Bot** | API 簡潔、Webhook 原生支援 | 台灣使用率低、企業接受度差 | ❌ 不建議 |
| **Native App** | 效能最佳、裝置 API 完整 | 開發成本高、需上架審核 | ❌ 不符投資效益 |

**LINE LIFF 實作路線圖**:

| Phase | 優先級 | 主題 | 關鍵交付 |
|-------|--------|------|---------|
| **M1** | P0 | LINE Login 帳號綁定 | `users.line_user_id` + 綁定 API + LINE Profile 自動對應 |
| **M2** | P0 | LIFF QR 掃描 | LIFF App (Compact) + `liff.scanCodeV2()` → `/erp/expenses/qr-scan` |
| **M3** | P1 | 收據拍照上傳 | LIFF Full 模式 + 拍照/相簿 → `/erp/einvoice-sync/upload-receipt` |
| **M4** | P1 | Flex Message 簽核 | 待審核推播 + Postback 一鍵核准/駁回 |
| **M5** | P2 | LIFF 費用查詢 | LIFF Tall 模式 + 費用清單 + 餘額查詢 |

---

本規劃書已取代所有過渡用之草案，為當前唯一基準。
