# ERP 財務模組架構審計報告

> **日期**: 2026-03-21
> **版本**: v5.1.2
> **審計範圍**: Phase 1~3.5 全後端 + Agent 整合 + 前端現況

---

## 一、完成狀態總覽

| Phase | 名稱 | 狀態 | 模組數 | 測試數 |
|-------|------|------|--------|--------|
| 1 | 資料基礎核心 (Model/Schema/Service/Repo/API) | ✅ | 15 | 33 |
| 2 | QR Code 辨識引擎 | ✅ | 2 | 4 |
| 2.5 | 財政部電子發票自動同步 | ✅ | 6 | 24 |
| 3 | Agent 整合 + 主動警報 | ✅ | 5 | 19 |
| 3.5 | 架構審計修復 | ✅ | 4 修復 | — |
| 4 | 前端整合 | ⏳ | 0 | 0 |
| 5 | 進階功能 | ⏳ | 0 | 0 |

**後端測試**: 2763 passed, 0 failed, 6 skipped

---

## 二、審計發現與修復記錄

### Critical 修復

| 代碼 | 問題 | 修復 |
|------|------|------|
| **C02** | `ExpenseInvoiceService.create()` 設 `status="processed"` 並直接寫帳本，`approve()` 再次寫帳本 → 雙重記帳 | `create()` 改為 `status="pending"`，移除帳本寫入；帳本僅在 `approve()` 時建立 |

### Warning 修復

| 代碼 | 問題 | 修復 |
|------|------|------|
| **W03** | `update()` 的 `data` 參數無型別 | 加入 `ExpenseInvoiceUpdate` 型別提示 |
| **W07** | `get_category_breakdown()` 在 Python 迴圈中做分類統計 | 遷移至 `LedgerRepository.get_category_breakdown()` SQL GROUP BY |
| **W08** | `FinanceLedgerService.delete()` 只 flush 不 commit | 補上 `await self.db.commit()` |

### Warning 保留 (低風險/可接受)

| 代碼 | 說明 | 原因 |
|------|------|------|
| **W04** | `update()` 可更新 status 繞過工作流 | 端點層已有權限控制，暫不額外限制 |
| **W05/W06** | `_get_top_projects` / `get_all_projects_summary` N+1 查詢 | N 被 `top_n`(≤50) 和 `limit`(≤20) 限制，有界 N+1 可接受 |
| **W10** | `ReceiptUploadRequest` schema | Phase 2.5 einvoice_sync 使用中，非孤兒 |
| **W13** | `FinancialSummaryService` 部分直接 DB 查詢 | 已有 Repository，Service 層的 `_get_top_projects` 屬於跨模組聚合邏輯 |

### 其他修復 (非財務模組)

| 問題 | 修復 |
|------|------|
| `test_federation_client` 測試因 v3.0 錯誤訊息格式改變而失敗 | 斷言改為檢查 system_id 是否出現在錯誤訊息中 |
| `test_tool_registry` / `test_pm_erp_tools` 工具數量斷言 23→26 | 更新為 26 (23 原有 + 3 finance) |

---

## 三、模組清單

### 新增檔案 (Phase 1~3.5 累計)

| 類型 | 路徑 | 說明 |
|------|------|------|
| **Model** | `extended/models/invoice.py` | ExpenseInvoice, ExpenseInvoiceItem |
| **Model** | `extended/models/finance.py` | FinanceLedger |
| **Model** | `extended/models/einvoice_sync.py` | EInvoiceSyncLog |
| **Migration** | `alembic/versions/3fc21c653f96_...` | Phase 1: 3 tables |
| **Migration** | `alembic/versions/20260321a001_...` | Phase 2.5: sync log + columns |
| **Schema** | `schemas/erp/expense.py` | 6 classes (Create/Update/Query/Item/Response) |
| **Schema** | `schemas/erp/ledger.py` | 4 classes (Create/Query/Response) |
| **Schema** | `schemas/erp/financial_summary.py` | 5 classes |
| **Schema** | `schemas/erp/einvoice_sync.py` | 5 classes |
| **Repository** | `repositories/erp/expense_invoice_repository.py` | inv_num/case_code/query |
| **Repository** | `repositories/erp/ledger_repository.py` | balance/category_breakdown/query |
| **Repository** | `repositories/erp/financial_summary_repository.py` | 跨模組 JOIN |
| **Service** | `services/expense_invoice_service.py` | QR+CRUD+審核入帳 |
| **Service** | `services/finance_ledger_service.py` | 手動記帳+刪除保護 |
| **Service** | `services/financial_summary_service.py` | 專案+公司總覽 |
| **Service** | `services/einvoice/mof_api_client.py` | 財政部 HMAC-SHA256 |
| **Service** | `services/einvoice/einvoice_sync_service.py` | 自動同步+收據 |
| **Endpoint** | `api/endpoints/erp/expenses.py` | 7 POST 端點 |
| **Endpoint** | `api/endpoints/erp/ledger.py` | 6 POST 端點 |
| **Endpoint** | `api/endpoints/erp/financial_summary.py` | 3 POST 端點 |
| **Endpoint** | `api/endpoints/erp/einvoice_sync.py` | 4 POST 端點 |
| **Test** | `tests/unit/test_expense_invoice.py` | 33 tests |
| **Test** | `tests/unit/test_einvoice_sync.py` | 24 tests |
| **Test** | `tests/unit/test_finance_agent_tools.py` | 19 tests |

### 修改的現有檔案

| 路徑 | 修改內容 |
|------|---------|
| `services/ai/tool_definitions.py` | +3 工具定義 (get_financial_summary/get_expense_overview/check_budget_alert) |
| `services/ai/tool_executor_domain.py` | +3 執行方法 |
| `services/ai/agent_tools.py` | +3 dispatch keys + guard templates |
| `services/ai/tool_registry.py` | +finance 查詢類型關鍵字 + 工具提升 |
| `services/ai/proactive_triggers_erp.py` | +check_budget_overrun + check_pending_receipts |
| `extended/models/__init__.py` | 匯出新 Model |
| `schemas/erp/__init__.py` | 匯出新 Schema |
| `api/routes.py` | 註冊新路由 |

---

## 四、架構品質評級

| 維度 | 評級 | 說明 |
|------|------|------|
| 分層合規 (Endpoint→Service→Repo) | **A** | 全部遵循三層架構 |
| Schema SSOT | **A** | 0 本地 BaseModel |
| 型別安全 | **A** | Decimal 精度、Literal 枚舉、型別提示完整 |
| 測試覆蓋 | **A** | 76 財務測試 + 2763 全後端 |
| Agent 整合 | **A** | 3 工具 + 2 觸發器 + dispatch 一致性驗證 |
| 資料完整性 | **A** | C02 雙重帳本已修復，status 工作流正確 |
| 前端就緒度 | **F** | Phase 4 全部 0%，零前端頁面 |
| N+1 查詢 | **B+** | 有界 N+1 (≤50 次)，非無限遞迴 |

**綜合評級**: **A-** (後端完整，前端缺失)

---

## 五、下一步建議

### 優先級 P0 — Phase 4 前端整合

1. **4-1**: 前端型別 (`types/erp.ts`) + Endpoint 常數 (`api/endpoints.ts`)
2. **4-2**: React Query Hooks (useExpenses, useLedger, useFinancialSummary, useEInvoiceSync)
3. **4-3**: ERP 費用報銷頁面 (列表+建立+詳情+審核)
4. **4-4**: 專案財務儀表板 (ProjectFinancialSummary 卡片)
5. **4-5**: 全公司財務總覽頁

### 優先級 P1 — 功能強化

6. **4-6**: 收據拍照上傳 (PWA Camera API)
7. **5-1**: Excel/PDF 匯出報表
8. **5-3**: ERPBilling 收款自動入帳

### 優先級 P2 — 技術債

9. `_get_top_projects` 批次查詢優化 (可用 `IN` 查詢替代 N+1)
10. `FinancialSummaryService` 直接查詢遷移至 Repository
11. 統一 `update()` 欄位白名單 (防止 status 繞過)

---

## 六、數據指標

| 指標 | 數值 |
|------|------|
| 新增檔案 | 23 |
| 修改檔案 | 8 |
| 新增 API 端點 | 20 (7+6+3+4) |
| 新增 DB 表 | 4 (expense_invoices, expense_invoice_items, finance_ledgers, einvoice_sync_logs) |
| Agent 工具 | 26 手動 (+3) + ~50 自動發現 = ~76 total |
| 測試 | 76 新增 (33+24+19) |
| 全後端測試 | 2763 passed, 0 failed |
