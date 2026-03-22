# ERP 財務體系開發任務清單 (Task Tracker)

> **同步版本**: Master Plan v5.1.8
> **狀態**: Phase 7-D 完成，Q2 核心任務全部竣工

## ✅ 已完成核心里程碑 (Phase 1-5, 100%)
- [x] ORM / Schemas / Repository 極致職責隔離
- [x] API (20 endpoints) / React Query Hooks / Dashboards
- [x] 多幣別自動換算引擎 & 門檻級多層審核狀態機 (`APPROVAL_TRANSITIONS`)

## ✅ 跨模組總帳整合戰略 (Phase 6 竣工)
- [x] **AP 應付拋轉對接**：完成 `record_from_vendor_payable` 供採購核銷
- [x] **AR 應收拋轉對接**：完成 `record_from_billing` 供出納請款核銷
- [x] **預算防火牆阻斷機制**：80% 預警、100% 阻擋 (`ValueError`) 之超級聯防

## ✅ Phase 7-A: 前端預算警報 UX 升級
- [x] `ERPExpenseListPage` 審核 → `Modal.warning()` / `Modal.error()` AlertDialog
- [x] `ERPExpenseDetailPage` 同步升級預算警報 UX
- [x] 錯誤訊息關鍵字匹配 (超支/預算/budget → AlertDialog, 其餘 → toast)

## ✅ Phase 7-B: ERP Repository 合規修正
- [x] `ERPQuotationService` v1.3.0 — create/update/delete 改用 Repository
- [x] `ERPInvoiceService` v1.1.0 — create/update/delete 改用 Repository
- [x] `ERPBillingService` v1.2.0 — create/delete 改用 Repository (update 保留 AR 邏輯)
- [x] `ERPVendorPayableService` v1.2.0 — create/delete 改用 Repository (update 保留 AP 邏輯)
- [x] 測試修復: 6 quotation tests + 1 export test mock 更新 → 220 passed, 0 failed

## ✅ Phase 7-C: NemoClaw 夜間吹哨者
- [x] `proactive_trigger_scan_job()` 排程任務 — APScheduler CronTrigger(00:30)
- [x] 整合掃描: ProactiveTriggerService (公文) + ERPTriggerScanner (預算/請款/發票/廠商)
- [x] 通知持久化: `_safe_create_notification()` warning+ 寫入 SystemNotification
- [x] LINE 推播: `LinePushScheduler.scan_and_push()` 可選推播
- [x] 類型標籤: `budget_overrun` + `pending_receipt_stale` 加入 `_TYPE_LABELS`
- [x] 測試: 8 tests (4 job + 2 registration + 2 labels) → 全部通過

## ✅ Phase 7-D: Dashboard 擴展
- [x] 月度收支趨勢 API — `POST /erp/financial-summary/monthly-trend` (回溯 N 月, 空月補零)
- [x] 預算使用率排行 API — `POST /erp/financial-summary/budget-ranking` (Top N, alert 三級)
- [x] Repository: `get_monthly_trend()` + `get_budget_ranking()` (SQL GROUP BY + 排序)
- [x] Schema: 6 新增 (MonthlyTrendRequest/Item/Response + BudgetRankingRequest/Item/Response)
- [x] 前端 types/hooks/API: `useMonthlyTrend` + `useBudgetRanking` + 端點常數
- [x] Dashboard 頁面: LineChart 月度趨勢 + BarChart 預算排行 (color-coded by alert)
- [x] 測試: 13 tests (3 trend + 3 ranking + 1 service + 6 schema) → 全部通過

## 📋 Final Roadmap 指引
詳見 `specs/finance_erp_final_roadmap.md` — 未來三季度長線發展藍圖
