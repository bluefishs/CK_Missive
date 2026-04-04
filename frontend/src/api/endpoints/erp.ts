/**
 * PM + ERP 財務管理端點
 */

/** PM 專案管理 API 端點 */
export const PM_ENDPOINTS = {
  /** 案件列表 POST /pm/cases/list */
  CASES_LIST: '/pm/cases/list',
  /** 建立案件 POST /pm/cases/create */
  CASES_CREATE: '/pm/cases/create',
  /** 案件詳情 POST /pm/cases/detail */
  CASES_DETAIL: '/pm/cases/detail',
  /** 更新案件 POST /pm/cases/update-by-id */
  CASES_UPDATE: '/pm/cases/update-by-id',
  /** 刪除案件 POST /pm/cases/delete */
  CASES_DELETE: '/pm/cases/delete',
  /** 案件統計摘要 POST /pm/cases/summary */
  CASES_SUMMARY: '/pm/cases/summary',
  /** 里程碑列表 POST /pm/milestones/list */
  MILESTONES_LIST: '/pm/milestones/list',
  /** 建立里程碑 POST /pm/milestones/create */
  MILESTONES_CREATE: '/pm/milestones/create',
  /** 更新里程碑 POST /pm/milestones/update */
  MILESTONES_UPDATE: '/pm/milestones/update',
  /** 刪除里程碑 POST /pm/milestones/delete */
  MILESTONES_DELETE: '/pm/milestones/delete',
  /** 匯出里程碑 XLSX POST /pm/milestones/export-xlsx */
  MILESTONES_EXPORT: '/pm/milestones/export-xlsx',
  /** 匯入里程碑 XLSX POST /pm/milestones/import-xlsx */
  MILESTONES_IMPORT: '/pm/milestones/import-xlsx',
  /** 人員列表 POST /pm/staff/list */
  STAFF_LIST: '/pm/staff/list',
  /** 建立人員 POST /pm/staff/create */
  STAFF_CREATE: '/pm/staff/create',
  /** 更新人員 POST /pm/staff/update */
  STAFF_UPDATE: '/pm/staff/update',
  /** 刪除人員 POST /pm/staff/delete */
  STAFF_DELETE: '/pm/staff/delete',
  /** 產生案號 POST /pm/cases/generate-code */
  GENERATE_CODE: '/pm/cases/generate-code',
  /** 重新計算進度 POST /pm/cases/recalculate-progress */
  RECALCULATE_PROGRESS: '/pm/cases/recalculate-progress',
  /** 跨模組案號查詢 POST /pm/cases/cross-lookup */
  CROSS_LOOKUP: '/pm/cases/cross-lookup',
  /** 甘特圖 POST /pm/cases/gantt */
  GANTT: '/pm/cases/gantt',
  /** 案號關聯公文 POST /pm/cases/linked-documents */
  LINKED_DOCUMENTS: '/pm/cases/linked-documents',
  /** 報價附件上傳 POST /pm/cases/attachments/{caseCode}/upload */
  ATTACHMENTS_UPLOAD: (caseCode: string) => `/pm/cases/attachments/${caseCode}/upload` as const,
  /** 報價附件列表 POST /pm/cases/attachments/{caseCode}/list */
  ATTACHMENTS_LIST: (caseCode: string) => `/pm/cases/attachments/${caseCode}/list` as const,
  /** 報價附件下載 POST /pm/cases/attachments/{id}/download */
  ATTACHMENTS_DOWNLOAD: (id: number) => `/pm/cases/attachments/${id}/download` as const,
  /** 報價附件刪除 POST /pm/cases/attachments/{id}/delete */
  ATTACHMENTS_DELETE: (id: number) => `/pm/cases/attachments/${id}/delete` as const,
  /** 匯出 CSV POST /pm/cases/export */
  EXPORT: '/pm/cases/export',
  /** 多年度趨勢 POST /pm/cases/yearly-trend */
  YEARLY_TREND: '/pm/cases/yearly-trend',
  /** 作業性質代碼列表 POST /pm/case-nature/list */
  CASE_NATURE_LIST: '/pm/case-nature/list',
  /** 作業性質下拉選項 POST /pm/case-nature/options */
  CASE_NATURE_OPTIONS: '/pm/case-nature/options',
  /** 新增作業性質 POST /pm/case-nature/create */
  CASE_NATURE_CREATE: '/pm/case-nature/create',
  /** 更新作業性質 POST /pm/case-nature/update */
  CASE_NATURE_UPDATE: '/pm/case-nature/update',
  /** 停用作業性質 POST /pm/case-nature/delete */
  CASE_NATURE_DELETE: '/pm/case-nature/delete',
} as const;

/** ERP 財務管理 API 端點 */
export const ERP_ENDPOINTS = {
  /** 報價列表 POST /erp/quotations/list */
  QUOTATIONS_LIST: '/erp/quotations/list',
  /** 建立報價 POST /erp/quotations/create */
  QUOTATIONS_CREATE: '/erp/quotations/create',
  /** 報價詳情 POST /erp/quotations/detail */
  QUOTATIONS_DETAIL: '/erp/quotations/detail',
  /** 更新報價 POST /erp/quotations/update */
  QUOTATIONS_UPDATE: '/erp/quotations/update',
  /** 刪除報價 POST /erp/quotations/delete */
  QUOTATIONS_DELETE: '/erp/quotations/delete',
  /** 損益摘要 POST /erp/quotations/profit-summary */
  PROFIT_SUMMARY: '/erp/quotations/profit-summary',
  /** 發票列表 POST /erp/invoices/list */
  INVOICES_LIST: '/erp/invoices/list',
  /** 建立發票 POST /erp/invoices/create */
  INVOICES_CREATE: '/erp/invoices/create',
  /** 更新發票 POST /erp/invoices/update */
  INVOICES_UPDATE: '/erp/invoices/update',
  /** 刪除發票 POST /erp/invoices/delete */
  INVOICES_DELETE: '/erp/invoices/delete',
  /** 跨案件發票彙總 POST /erp/invoices/summary */
  INVOICES_SUMMARY: '/erp/invoices/summary',
  /** 從請款開立發票 POST /erp/invoices/create-from-billing */
  INVOICES_CREATE_FROM_BILLING: '/erp/invoices/create-from-billing',
  /** 請款列表 POST /erp/billings/list */
  BILLINGS_LIST: '/erp/billings/list',
  /** 建立請款 POST /erp/billings/create */
  BILLINGS_CREATE: '/erp/billings/create',
  /** 更新請款 POST /erp/billings/update */
  BILLINGS_UPDATE: '/erp/billings/update',
  /** 刪除請款 POST /erp/billings/delete */
  BILLINGS_DELETE: '/erp/billings/delete',
  /** 請款期別整合視圖 POST /erp/billings/list-with-details */
  BILLINGS_LIST_DETAILS: '/erp/billings/list-with-details',
  /** 廠商應付列表 POST /erp/vendor-payables/list */
  VENDOR_PAYABLES_LIST: '/erp/vendor-payables/list',
  /** 建立廠商應付 POST /erp/vendor-payables/create */
  VENDOR_PAYABLES_CREATE: '/erp/vendor-payables/create',
  /** 更新廠商應付 POST /erp/vendor-payables/update */
  VENDOR_PAYABLES_UPDATE: '/erp/vendor-payables/update',
  /** 刪除廠商應付 POST /erp/vendor-payables/delete */
  VENDOR_PAYABLES_DELETE: '/erp/vendor-payables/delete',
  /** 產生案號 POST /erp/quotations/generate-code */
  GENERATE_CODE: '/erp/quotations/generate-code',
  /** 損益趨勢 POST /erp/quotations/profit-trend */
  PROFIT_TREND: '/erp/quotations/profit-trend',
  /** 匯出 CSV POST /erp/quotations/export */
  EXPORT: '/erp/quotations/export',
  /** 匯出 Excel POST /erp/quotations/export-excel */
  EXPORT_EXCEL: '/erp/quotations/export-excel',
  /** 匯入 Excel POST /erp/quotations/import */
  IMPORT: '/erp/quotations/import',
  /** 下載匯入範本 POST /erp/quotations/import-template */
  IMPORT_TEMPLATE: '/erp/quotations/import-template',
  /** 案號→成案編號對照表 POST /erp/quotations/case-code-map */
  CASE_CODE_MAP: '/erp/quotations/case-code-map',

  // --- 費用報銷 (expenses) ---
  /** 費用發票列表 POST /erp/expenses/list */
  EXPENSES_LIST: '/erp/expenses/list',
  /** 建立報銷發票 POST /erp/expenses/create */
  EXPENSES_CREATE: '/erp/expenses/create',
  /** 發票詳情 POST /erp/expenses/detail */
  EXPENSES_DETAIL: '/erp/expenses/detail',
  /** 更新報銷發票 POST /erp/expenses/update */
  EXPENSES_UPDATE: '/erp/expenses/update',
  /** 審核通過 POST /erp/expenses/approve */
  EXPENSES_APPROVE: '/erp/expenses/approve',
  /** 駁回報銷 POST /erp/expenses/reject */
  EXPENSES_REJECT: '/erp/expenses/reject',
  /** QR Code 掃描建立 POST /erp/expenses/qr-scan */
  EXPENSES_QR_SCAN: '/erp/expenses/qr-scan',
  /** 上傳收據影像 POST /erp/expenses/upload-receipt */
  EXPENSES_UPLOAD_RECEIPT: '/erp/expenses/upload-receipt',
  /** 取得收據影像 POST /erp/expenses/receipt-image */
  EXPENSES_RECEIPT_IMAGE: '/erp/expenses/receipt-image',
  /** OCR 辨識發票影像 POST /erp/expenses/ocr-parse */
  EXPENSES_OCR_PARSE: '/erp/expenses/ocr-parse',
  /** 智慧發票辨識 (QR+OCR) POST /erp/expenses/smart-scan */
  EXPENSES_SMART_SCAN: '/erp/expenses/smart-scan',
  /** AI 費用分類建議 POST /erp/expenses/suggest-category */
  EXPENSES_SUGGEST_CATEGORY: '/erp/expenses/suggest-category',
  /** 費用核銷分組彙總 POST /erp/expenses/grouped-summary */
  EXPENSES_GROUPED_SUMMARY: '/erp/expenses/grouped-summary',
  /** 案件整合財務紀錄 POST /erp/expenses/case-finance */
  EXPENSES_CASE_FINANCE: '/erp/expenses/case-finance',
  /** 自動關聯電子發票 POST /erp/expenses/auto-link-einvoice */
  EXPENSES_AUTO_LINK_EINVOICE: '/erp/expenses/auto-link-einvoice',
  /** 匯入費用報銷 Excel POST /erp/expenses/import */
  EXPENSES_IMPORT: '/erp/expenses/import',
  /** 下載費用報銷匯入範本 POST /erp/expenses/import-template */
  EXPENSES_IMPORT_TEMPLATE: '/erp/expenses/import-template',

  // --- 統一帳本 (ledger) ---
  /** 帳本列表 POST /erp/ledger/list */
  LEDGER_LIST: '/erp/ledger/list',
  /** 手動記帳 POST /erp/ledger/create */
  LEDGER_CREATE: '/erp/ledger/create',
  /** 帳本詳情 POST /erp/ledger/detail */
  LEDGER_DETAIL: '/erp/ledger/detail',
  /** 專案收支餘額 POST /erp/ledger/balance */
  LEDGER_BALANCE: '/erp/ledger/balance',
  /** 分類拆解 POST /erp/ledger/category-breakdown */
  LEDGER_CATEGORY_BREAKDOWN: '/erp/ledger/category-breakdown',
  /** 刪除帳本 POST /erp/ledger/delete */
  LEDGER_DELETE: '/erp/ledger/delete',

  // --- 財務彙總 (financial-summary) ---
  /** 單一專案財務彙總 POST /erp/financial-summary/project */
  FINANCIAL_SUMMARY_PROJECT: '/erp/financial-summary/project',
  /** 所有專案一覽 POST /erp/financial-summary/projects */
  FINANCIAL_SUMMARY_PROJECTS: '/erp/financial-summary/projects',
  /** 全公司財務總覽 POST /erp/financial-summary/company */
  FINANCIAL_SUMMARY_COMPANY: '/erp/financial-summary/company',
  /** 月度收支趨勢 POST /erp/financial-summary/monthly-trend */
  FINANCIAL_SUMMARY_MONTHLY_TREND: '/erp/financial-summary/monthly-trend',
  /** 預算使用率排行 POST /erp/financial-summary/budget-ranking */
  FINANCIAL_SUMMARY_BUDGET_RANKING: '/erp/financial-summary/budget-ranking',
  /** 帳齡分析 POST /erp/financial-summary/aging */
  FINANCIAL_SUMMARY_AGING: '/erp/financial-summary/aging',
  /** ERP 模組快速統計 POST /erp/financial-summary/erp-overview */
  FINANCIAL_SUMMARY_ERP_OVERVIEW: '/erp/financial-summary/erp-overview',
  /** 匯出費用報銷 Excel POST /erp/financial-summary/export-expenses */
  EXPORT_EXPENSES: '/erp/financial-summary/export-expenses',
  /** 匯出帳本 Excel POST /erp/financial-summary/export-ledger */
  EXPORT_LEDGER: '/erp/financial-summary/export-ledger',

  // --- 廠商/委託帳款 (vendor-accounts / client-accounts) ---
  /** 廠商帳款彙總 POST /erp/vendor-accounts/summary */
  VENDOR_ACCOUNTS_SUMMARY: '/erp/vendor-accounts/summary',
  /** 廠商帳款明細 POST /erp/vendor-accounts/detail */
  VENDOR_ACCOUNTS_DETAIL: '/erp/vendor-accounts/detail',
  /** 委託單位帳款彙總 POST /erp/client-accounts/summary */
  CLIENT_ACCOUNTS_SUMMARY: '/erp/client-accounts/summary',
  /** 委託單位帳款明細 POST /erp/client-accounts/detail */
  CLIENT_ACCOUNTS_DETAIL: '/erp/client-accounts/detail',

  // --- 電子發票同步 (einvoice-sync) ---
  /** 手動觸發同步 POST /erp/einvoice-sync/sync */
  EINVOICE_SYNC: '/erp/einvoice-sync/sync',
  /** 待核銷清單 POST /erp/einvoice-sync/pending-list */
  EINVOICE_PENDING_LIST: '/erp/einvoice-sync/pending-list',
  /** 上傳收據照片 POST /erp/einvoice-sync/upload-receipt */
  EINVOICE_UPLOAD_RECEIPT: '/erp/einvoice-sync/upload-receipt',
  /** 同步歷史記錄 POST /erp/einvoice-sync/sync-logs */
  EINVOICE_SYNC_LOGS: '/erp/einvoice-sync/sync-logs',

  // --- 資產管理 (assets) ---
  /** 資產列表 POST /erp/assets/list */
  ASSETS_LIST: '/erp/assets/list',
  /** 建立資產 POST /erp/assets/create */
  ASSETS_CREATE: '/erp/assets/create',
  /** 資產詳情 POST /erp/assets/detail */
  ASSETS_DETAIL: '/erp/assets/detail',
  /** 更新資產 POST /erp/assets/update */
  ASSETS_UPDATE: '/erp/assets/update',
  /** 刪除資產 POST /erp/assets/delete */
  ASSETS_DELETE: '/erp/assets/delete',
  /** 資產統計 POST /erp/assets/stats */
  ASSETS_STATS: '/erp/assets/stats',
  /** 資產異動記錄列表 POST /erp/assets/logs/list */
  ASSET_LOGS_LIST: '/erp/assets/logs/list',
  /** 建立資產異動記錄 POST /erp/assets/logs/create */
  ASSET_LOGS_CREATE: '/erp/assets/logs/create',
  /** 資產完整詳情 (含關聯發票+案件) POST /erp/assets/detail-full */
  ASSETS_DETAIL_FULL: '/erp/assets/detail-full',
  /** 匯出資產清單 Excel POST /erp/assets/export */
  ASSETS_EXPORT: '/erp/assets/export',
  /** 依發票查詢關聯資產 POST /erp/assets/by-invoice */
  ASSETS_BY_INVOICE: '/erp/assets/by-invoice',
  /** 批次盤點 POST /erp/assets/batch-inventory */
  ASSETS_BATCH_INVENTORY: '/erp/assets/batch-inventory',
  /** 匯出盤點報表 Excel POST /erp/assets/export-inventory */
  ASSETS_EXPORT_INVENTORY: '/erp/assets/export-inventory',
  /** 匯入資產清單 Excel POST /erp/assets/import */
  ASSETS_IMPORT: '/erp/assets/import',
  /** 下載資產匯入範本 Excel POST /erp/assets/import-template */
  ASSETS_IMPORT_TEMPLATE: '/erp/assets/import-template',
  /** 上傳資產照片 POST /erp/assets/upload-photo */
  ASSETS_UPLOAD_PHOTO: '/erp/assets/upload-photo',
  /** 取得資產照片 POST /erp/assets/photo */
  ASSETS_PHOTO: '/erp/assets/photo',

  // --- 營運帳目 (operational) ---
  /** 營運帳目列表 POST /erp/operational/list */
  OPERATIONAL_LIST: '/erp/operational/list',
  /** 建立營運帳目 POST /erp/operational/create */
  OPERATIONAL_CREATE: '/erp/operational/create',
  /** 營運帳目詳情 POST /erp/operational/detail */
  OPERATIONAL_DETAIL: '/erp/operational/detail',
  /** 更新營運帳目 POST /erp/operational/update */
  OPERATIONAL_UPDATE: '/erp/operational/update',
  /** 刪除營運帳目 POST /erp/operational/delete */
  OPERATIONAL_DELETE: '/erp/operational/delete',
  /** 營運帳目統計 POST /erp/operational/stats */
  OPERATIONAL_STATS: '/erp/operational/stats',
  /** 營運帳目費用列表 POST /erp/operational/expenses/list */
  OPERATIONAL_EXPENSES_LIST: '/erp/operational/expenses/list',
  /** 建立營運帳目費用 POST /erp/operational/expenses/create */
  OPERATIONAL_EXPENSES_CREATE: '/erp/operational/expenses/create',
  /** 審核營運帳目費用 POST /erp/operational/expenses/approve */
  OPERATIONAL_EXPENSES_APPROVE: '/erp/operational/expenses/approve',
  /** 駁回營運帳目費用 POST /erp/operational/expenses/reject */
  OPERATIONAL_EXPENSES_REJECT: '/erp/operational/expenses/reject',
} as const;
