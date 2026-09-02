---
title: 功能模組 ERP財務
type: topic
sources: [site_navigation_items, router/AppRouter.tsx, api/endpoints, api/routes.py, ui-sweep.json]
tags: [功能模組, 履歷, 整合, auto-compiled]
confidence: high
---

> 由 `scripts/dev/feature_dossier.py` 組出，**不要手改**。
> 這是使用者語言的履歷：一個功能模組用到哪些頁面、API、後端模組，以及**誰在看它**。

# 功能模組履歷：ERP財務

## 使用者看到的（7 個項目）
- 財務儀表板　`/erp/financial-dashboard`　→ frontend/src/pages/ERPFinancialDashboardPage.tsx
- ERP 管理中心　`/erp`　→ frontend/src/pages/ERPHubPage.tsx
- 電子發票　`/erp/einvoice-sync`　→ frontend/src/pages/ERPEInvoiceSyncPage.tsx
- 財務總覽　`/erp/expenses`　→ frontend/src/pages/ERPExpenseListPage.tsx
- 統一帳本　`/erp/ledger`　→ frontend/src/pages/ERPLedgerPage.tsx
- 營運帳目　`/erp/operational`　→ frontend/src/pages/ERPOperationalListPage.tsx
- 發票彙總　`/erp/invoices/summary-view`　→ frontend/src/pages/ERPInvoiceSummaryPage.tsx

## 它打哪些 API（走查實際觀測，非靜態推論）
- 本模組特有 **18** 個：
  - /api/erp/einvoice-sync/pending-list
  - /api/erp/einvoice-sync/sync-logs
  - /api/erp/expenses/grouped-summary
  - /api/erp/expenses/list
  - /api/erp/financial-summary/aging
  - /api/erp/financial-summary/budget-ranking
  - /api/erp/financial-summary/company
  - /api/erp/financial-summary/erp-overview
  - /api/erp/financial-summary/monthly-trend
  - /api/erp/financial-summary/projects
  - /api/erp/invoices/summary
  - /api/erp/ledger/category-breakdown
  - /api/erp/ledger/list
  - /api/erp/ledger/totals
  - /api/erp/operational/list
  - /api/erp/operational/stats
  - /api/erp/quotations/case-code-map
  - /api/projects/list
- （已扣除 7 個全站共用啟動請求：/api/ai/config、/api/auth/check、/api/auth/me、/api/secure-site-management/csrf-token…）—— 不扣的話每個功能看起來都一樣

## 誰在看它
- 瀏覽器走查涵蓋：**7/7** 條路由
