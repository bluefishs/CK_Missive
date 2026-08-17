/**
 * ERP 財務管理型別定義
 * 對應後端 app/schemas/erp/
 */

// ============================================================================
// ERP 核心型別 (原定義於 api.ts)
// ============================================================================

/** ERP 報價狀態 */
export type ERPQuotationStatus = 'draft' | 'confirmed' | 'revised' | 'closed';

/** ERP 報價狀態標籤 */
export const ERP_QUOTATION_STATUS_LABELS: Record<ERPQuotationStatus, string> = {
  draft: '草稿',
  confirmed: '已確認',
  revised: '已修訂',
  closed: '已結案',
};

/** ERP 報價狀態顏色 */
export const ERP_QUOTATION_STATUS_COLORS: Record<ERPQuotationStatus, string> = {
  draft: 'default',
  confirmed: 'processing',
  revised: 'warning',
  closed: 'success',
};

/** ERP 報價/成本主檔 */
export interface ERPQuotation {
  id: number;
  case_code: string;
  project_code?: string;
  case_name?: string;
  year?: number;
  total_price?: number;
  tax_amount: number;
  outsourcing_fee: number;
  personnel_fee: number;
  overhead_fee: number;
  other_cost: number;
  status: ERPQuotationStatus;
  notes?: string;
  created_by?: number;
  created_at?: string;
  updated_at?: string;
  budget_limit?: number;
  budget_usage_pct?: number;
  is_over_budget: boolean;
  /** 報價單上填的**估列**成本合計（外包＋人事＋管銷＋其他）—— 不是實際支出 */
  total_cost: number;
  /** 預估毛利 = (總價 − 稅) − 估列成本 —— 基準是估列，不是實際 */
  gross_profit: number;
  /** 預估毛利率（%）—— cost_declared 為 false 時不得呈現 */
  gross_margin?: number;
  /** @deprecated 目前與 gross_profit 是同一個數字。真正的淨利要再扣營運費用與稅，
   *  那些資料不在報價這一層。UI 已不再顯示，保留僅為相容。 */
  net_profit: number;
  /** 實際成本（已入帳）—— 統一帳本裡掛在此案號的支出。與估列 total_cost 是兩件事。 */
  actual_cost?: number;
  /** 已發生但尚未入帳（核銷未入帳 ＋ 應付未付）—— 填報缺口，不計入實際成本。 */
  pending_cost?: number;
  /** 成本四欄是否有填。後端把未填存成 0，「沒填」與「真的是零」分不出來，
   *  毛利率會顯示 100%。為 false 時前端不得呈現毛利數字。 */
  cost_declared?: boolean;
  invoice_count: number;
  billing_count: number;
  total_billed: number;
  total_received: number;
  total_payable: number;
  total_paid: number;
  pm_contract_amount?: number;
  amount_mismatch?: boolean;
}

/** ERP 報價建立 */
export interface ERPQuotationCreate {
  case_code?: string;
  /** 成案專案編號（對應 contract_projects.project_code）；後端 schema 已支援 */
  project_code?: string;
  case_name?: string;
  year?: number;
  total_price?: number | string;
  tax_amount?: number | string;
  outsourcing_fee?: number | string;
  personnel_fee?: number | string;
  overhead_fee?: number | string;
  other_cost?: number | string;
  budget_limit?: number | string;
  status?: string;
  notes?: string;
}

/** ERP 報價更新 */
export type ERPQuotationUpdate = Partial<ERPQuotationCreate>;

/** ERP 損益摘要 */
export interface ERPProfitSummary {
  total_revenue: number;
  total_cost: number;
  total_gross_profit: number;
  avg_gross_margin?: number;
  total_billed: number;
  total_received: number;
  total_outstanding: number;
  case_count: number;
  by_year: Record<string, unknown>;
}

/** ERP 損益趨勢項目 */
export interface ERPProfitTrendItem {
  year: number;
  revenue: number;
  cost: number;
  gross_profit: number;
  gross_margin?: number;
  case_count: number;
}

/** ERP 廠商應付帳款 */
export interface ERPVendorPayable {
  id: number;
  erp_quotation_id: number;
  vendor_name: string;
  payable_amount: number;
  description?: string;
  payment_status: string;
  paid_date?: string;
  paid_amount: number;
}

// ============================================================================
// ERP 擴展型別
// ============================================================================

/** ERP 報價列表查詢參數 */
export interface ERPQuotationListParams {
  page?: number;
  page_size?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  year?: number;
  status?: string;
  case_code?: string;
  search?: string;
  [key: string]: unknown;
}

/** ERP 發票 */
export interface ERPInvoice {
  id: number;
  erp_quotation_id: number;
  invoice_number: string;
  invoice_date: string;
  amount: number;
  tax_amount: number;
  invoice_type: string;
  description?: string;
  status: string;
  voided_at?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ERPInvoiceCreate {
  erp_quotation_id: number;
  invoice_number: string;
  invoice_date: string;
  amount: number;
  tax_amount?: number;
  invoice_type?: string;
  description?: string;
  notes?: string;
}

export type ERPInvoiceUpdate = Partial<Omit<ERPInvoiceCreate, 'erp_quotation_id'>> & {
  status?: string;
};

/** 跨案件發票彙總項目 */
export interface InvoiceSummaryItem {
  id: number;
  invoice_number: string;
  invoice_date?: string;
  amount: number;
  tax_amount: number;
  invoice_type: string;
  status: string;
  description?: string;
  case_code: string;
  project_code?: string;
  case_name?: string;
  billing_id?: number;
  erp_quotation_id?: number;
}

/** 跨案件發票彙總查詢參數 */
export interface InvoiceSummaryRequest {
  invoice_type?: string;
  year?: number;
  skip?: number;
  limit?: number;
}

/** ERP 請款 */
export interface ERPBilling {
  id: number;
  erp_quotation_id: number;
  billing_period?: string;
  billing_date: string;
  billing_amount: number;
  payment_status: string;
  payment_date?: string;
  payment_amount?: number;
  notes?: string;
  invoice_number?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ERPBillingCreate {
  erp_quotation_id: number;
  billing_period?: string;
  billing_date: string;
  billing_amount: number;
  payment_status?: string;
  notes?: string;
}

export type ERPBillingUpdate = Partial<Omit<ERPBillingCreate, 'erp_quotation_id'>> & {
  payment_date?: string;
  payment_amount?: number;
};

/** ERP 廠商應付 (full detail interface) */
export interface ERPVendorPayableDetail {
  id: number;
  erp_quotation_id: number;
  vendor_name: string;
  vendor_code?: string;
  vendor_id?: number;
  payable_amount: number;
  description?: string;
  due_date?: string;
  paid_date?: string;
  paid_amount?: number;
  payment_status: string;
  invoice_number?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ERPVendorPayableCreate {
  erp_quotation_id: number;
  vendor_name: string;
  vendor_code?: string;
  payable_amount: number;
  description?: string;
  due_date?: string;
  invoice_number?: string;
  notes?: string;
}

export type ERPVendorPayableUpdate = Partial<Omit<ERPVendorPayableCreate, 'erp_quotation_id'>> & {
  paid_date?: string;
  paid_amount?: number;
  payment_status?: string;
};

// ============================================================================
// Extended types and constants for sub-module consumers
// ============================================================================

export type ERPInvoiceType = 'sales' | 'purchase';
export type ERPInvoiceStatus = 'issued' | 'voided' | 'cancelled';
export type ERPBillingStatus = 'pending' | 'partial' | 'paid' | 'overdue';
export type ERPPayableStatus = 'unpaid' | 'partial' | 'paid';

export const ERP_INVOICE_TYPE_LABELS: Record<ERPInvoiceType, string> = {
  sales: '銷項',
  purchase: '進項',
};

export const ERP_BILLING_STATUS_LABELS: Record<ERPBillingStatus, string> = {
  pending: '待收款',
  partial: '部分收款',
  paid: '已收款',
  overdue: '逾期',
};

export const ERP_PAYABLE_STATUS_LABELS: Record<ERPPayableStatus, string> = {
  unpaid: '未付',
  partial: '部分付款',
  paid: '已付清',
};

export const ERP_CATEGORY_CODES: Record<string, string> = {
  '01': '報價單',
  '02': '變更單',
  '03': '追加減',
  '99': '其他',
};

// ============================================================================
// 費用報銷模組 (ExpenseInvoice) — 對應 schemas/erp/expense.py
// ============================================================================

/** 支援幣別 (ISO 4217) — 與後端 SUPPORTED_CURRENCIES 同步 */
export type SupportedCurrency = 'TWD' | 'USD' | 'CNY' | 'JPY' | 'EUR';

export const CURRENCY_OPTIONS: { value: SupportedCurrency; label: string }[] = [
  { value: 'TWD', label: 'TWD 新台幣' },
  { value: 'USD', label: 'USD 美元' },
  { value: 'CNY', label: 'CNY 人民幣' },
  { value: 'JPY', label: 'JPY 日圓' },
  { value: 'EUR', label: 'EUR 歐元' },
];

export const CURRENCY_SYMBOLS: Record<SupportedCurrency, string> = {
  TWD: 'NT$',
  USD: '$',
  CNY: '¥',
  JPY: '¥',
  EUR: '€',
};

/** 費用分類 — 與後端 EXPENSE_CATEGORIES Literal 同步 */
export type ExpenseCategory =
  | '交通費' | '差旅費' | '文具及印刷' | '郵電費' | '水電費'
  | '保險費' | '租金' | '維修費' | '雜費' | '設備採購'
  | '外包及勞務' | '訓練費' | '材料費' | '報銷及費用' | '其他';

export const EXPENSE_CATEGORY_OPTIONS: { value: ExpenseCategory; label: string }[] = [
  { value: '交通費', label: '交通費' },
  { value: '差旅費', label: '差旅費' },
  { value: '文具及印刷', label: '文具及印刷' },
  { value: '郵電費', label: '郵電費' },
  { value: '水電費', label: '水電費' },
  { value: '保險費', label: '保險費' },
  { value: '租金', label: '租金' },
  { value: '維修費', label: '維修費' },
  { value: '雜費', label: '雜費' },
  { value: '設備採購', label: '設備採購' },
  { value: '外包及勞務', label: '外包及勞務' },
  { value: '訓練費', label: '訓練費' },
  { value: '材料費', label: '材料費' },
  { value: '報銷及費用', label: '報銷及費用' },
  { value: '其他', label: '其他' },
];

/** 費用發票來源 */
export type ExpenseSource = 'qr_scan' | 'manual' | 'api' | 'ocr' | 'mof_sync' | 'line_upload';

/** 費用發票狀態 — Phase 5-5 多層審核 */
export type ExpenseInvoiceStatus =
  | 'pending'           // 待主管審核
  | 'pending_receipt'   // 待上傳收據
  | 'manager_approved'  // 主管已核准
  | 'finance_approved'  // 財務已核准
  | 'verified'          // 最終通過 (已入帳)
  | 'rejected';         // 已駁回

/**
 * 2026-08-17 owner「流程簡化」：財務層已移除，一律最多兩段
 * （小額直達／其餘 主管核准 → 完成）。
 *
 * ⚠️ 這份是 SSOT，但在此之前**前端有四份各自的狀態文字**
 * （ERPExpenseDetailPage／erpQuotation/ExpensesTab／pmCase/ExpensesTab
 * 各寫一份，而這份 SSOT 沒有人用）。其中詳情頁那份還依金額判斷要不要顯示
 * 「財務核准」—— 流程改了它不會跟。已全數改為引用這裡。
 */
export const EXPENSE_STATUS_LABELS: Record<ExpenseInvoiceStatus, string> = {
  pending: '待審核',
  pending_receipt: '待上傳收據',
  manager_approved: '主管已核准・待確認',
  finance_approved: '待確認（舊流程）',
  verified: '已完成・已入帳',
  rejected: '已駁回',
};

/** 審核按鈕文字 —— 由狀態決定，**不再依金額判斷** */
export const EXPENSE_APPROVE_LABELS: Record<string, string> = {
  pending: '核准',
  manager_approved: '確認完成',
  finance_approved: '確認完成',
  pending_receipt: '推進',
};

export const EXPENSE_STATUS_COLORS: Record<ExpenseInvoiceStatus, string> = {
  pending: 'orange',
  pending_receipt: 'blue',
  manager_approved: 'cyan',
  finance_approved: 'geekblue',
  verified: 'green',
  rejected: 'red',
};

/** 審核金額門檻 (TWD) — 與後端 APPROVAL_THRESHOLD 同步 */
export const APPROVAL_THRESHOLD = 30000;

export const EXPENSE_SOURCE_LABELS: Record<ExpenseSource, string> = {
  qr_scan: 'QR 掃描',
  manual: '手動輸入',
  api: 'API',
  ocr: 'OCR 辨識',
  mof_sync: '財政部同步',
  line_upload: 'LINE 上傳',
};

/** 費用發票明細項目 */
export interface ExpenseInvoiceItem {
  id: number;
  invoice_id: number;
  item_name: string;
  qty: number;
  unit_price: number;
  amount: number;
}

export interface ExpenseInvoiceItemCreate {
  item_name: string;
  qty: number;
  unit_price: number;
  amount: number;
}

/** 費用報銷發票 */
/** 歸屬類型 */
export type AttributionType = 'project' | 'operational' | 'none';

export type VoucherType = 'invoice' | 'receipt' | 'ticket' | 'utility' | 'other';

export const VOUCHER_TYPE_LABELS: Record<VoucherType, string> = {
  invoice: '統一發票',
  receipt: '普通收據',
  ticket: '車票/機票',
  utility: '水電/電信帳單',
  other: '其他憑證',
};

export const VOUCHER_TYPE_OPTIONS = Object.entries(VOUCHER_TYPE_LABELS).map(([value, label]) => ({ value, label }));

export interface ExpenseInvoice {
  id: number;
  voucher_type: VoucherType;
  inv_num: string;
  date: string;
  amount: number;
  tax_amount?: number;
  buyer_ban?: string;
  seller_ban?: string;
  case_code?: string;
  attribution_type: AttributionType;
  operational_account_id?: number;
  vendor_id?: number;
  category?: ExpenseCategory;
  source: ExpenseSource;
  notes?: string;
  user_id?: number;
  status: ExpenseInvoiceStatus;
  source_image_path?: string;
  receipt_image_path?: string;
  items: ExpenseInvoiceItem[];
  currency: SupportedCurrency;
  original_amount?: number;
  exchange_rate?: number;
  approval_level?: string;
  next_approval?: string;
  synced_at?: string;
}

export interface ExpenseInvoiceCreate {
  voucher_type?: VoucherType;
  inv_num: string;
  date: string;
  amount: number;
  tax_amount?: number;
  buyer_ban?: string;
  seller_ban?: string;
  case_code?: string;
  attribution_type?: AttributionType;
  operational_account_id?: number;
  category?: ExpenseCategory;
  source?: ExpenseSource;
  notes?: string;
  items?: ExpenseInvoiceItemCreate[];
  currency?: SupportedCurrency;
  original_amount?: number;
  exchange_rate?: number;
}

export interface ExpenseInvoiceUpdate {
  category?: ExpenseCategory;
  notes?: string;
  status?: string;
}

/** OCR 辨識結果 */
export interface ExpenseInvoiceOCRResult {
  inv_num?: string;
  date?: string;
  amount?: number;
  tax_amount?: number;
  buyer_ban?: string;
  seller_ban?: string;
  raw_text: string;
  confidence: number;
  warnings: string[];
  source_image_path?: string;
}

export interface ExpenseInvoiceQuery {
  case_code?: string;
  attribution_type?: string;
  category?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  user_id?: number;
  skip?: number;
  limit?: number;
}

export interface ExpenseInvoiceRejectRequest {
  id: number;
  reason?: string;
}

export interface ExpenseInvoiceQRScanRequest {
  raw_qr: string;
  case_code?: string;
  category?: ExpenseCategory;
}

// ============================================================================
// 統一帳本模組 (FinanceLedger) — 對應 schemas/erp/ledger.py
// ============================================================================

/** 帳本類型 */
export type LedgerEntryType = 'income' | 'expense';

export const LEDGER_ENTRY_TYPE_LABELS: Record<LedgerEntryType, string> = {
  income: '收入',
  expense: '支出',
};

/**
 * 帳本分類（會計科目）—— 對應後端 `schemas/erp/ledger.py` 的 `LEDGER_CATEGORY_VALUES`。
 *
 * 2026-08-16 owner：「分類仍有中英紛雜 如統一帳本」。
 * 根因是後端 `ledger.py` 的 category 原本是無約束的 `str`，而手動記帳表單的
 * 分類欄是**自由輸入的 Input**（placeholder「例：交通費」）—— 兩端都不約束，
 * 於是帳本累積出 `billing_payment`（英文代碼、35 筆歷史匯入）等清單外的值。
 *
 * 帳本同時記收入與支出，所以分類 = 收入科目 + 營運 + 支出科目
 * （支出科目沿用 `EXPENSE_CATEGORY_OPTIONS`，**不另造一份**）。
 */
export const LEDGER_INCOME_CATEGORIES = ['收款', '其他收入'] as const;
export const LEDGER_OPERATIONAL_CATEGORIES = ['營運費用'] as const;

export const LEDGER_CATEGORY_GROUPS: {
  label: string;
  options: { value: string; label: string }[];
}[] = [
  { label: '收入', options: LEDGER_INCOME_CATEGORIES.map(v => ({ value: v, label: v })) },
  { label: '營運', options: LEDGER_OPERATIONAL_CATEGORIES.map(v => ({ value: v, label: v })) },
  { label: '支出科目', options: EXPENSE_CATEGORY_OPTIONS.map(o => ({ value: o.value, label: o.label })) },
];

/**
 * 帳本分錄的來源單據類型。
 *
 * 2026-08-15：原本頁面直接顯示 raw 值（`erp_billing`、`expense_invoice`），
 * 而 DB 裡同時存在 `billing` 與 `erp_billing` 兩套標籤 ——
 * 寫入端某次改名時舊資料沒跟著遷移，於是**同一件事在畫面上有兩種名稱**，
 * 而任何依這個欄位篩選的功能都只會拿到一半資料。
 * 該次也讓對帳程式報出一個不存在的 1,329,710 差額（詳見 scheduler 的註解）。
 *
 * 資料已於同日統一為 `erp_billing`（35 筆遷移，金額與筆數守恆）。
 * 這裡是**呈現層的單一來源** —— 兩個頁面共用，不各自寫一份對照。
 */
export const LEDGER_SOURCE_TYPE_LABELS: Record<string, string> = {
  // 措辭沿用 ERPExpenseListPage 原本頁內的那一份 —— 使用者已經看習慣，
  // 收斂時改動措辭會讓「同一件事」在他們眼中變成另一件事。
  manual: '手動',
  expense_invoice: '報銷',
  erp_billing: '請款',
  vendor_payable: '付款',
  operational: '營運',
};

/** 未知來源保留原值顯示 —— 靜靜顯示空白會讓新來源看起來像資料遺失 */
export const ledgerSourceLabel = (v?: string | null): string =>
  (v ? LEDGER_SOURCE_TYPE_LABELS[v] || v : '—');

export const LEDGER_SOURCE_TYPE_OPTIONS = Object.entries(LEDGER_SOURCE_TYPE_LABELS)
  .map(([value, label]) => ({ value, label }));

/** 帳本記錄 */
export interface FinanceLedger {
  id: number;
  amount: number;
  entry_type: LedgerEntryType;
  category?: string;
  description?: string;
  case_code?: string;
  transaction_date?: string;
  user_id?: number;
  source_type: string;
  source_id?: number;
  vendor_id?: number;
}

export interface LedgerCreate {
  amount: number;
  entry_type: LedgerEntryType;
  category?: string;
  description?: string;
  case_code?: string;
  transaction_date?: string;
}

export interface LedgerQuery {
  case_code?: string;
  entry_type?: LedgerEntryType;
  category?: string;
  date_from?: string;
  date_to?: string;
  user_id?: number;
  skip?: number;
  limit?: number;
}

export interface LedgerBalanceRequest {
  case_code: string;
}

export interface LedgerCategoryBreakdownRequest {
  case_code?: string;
  date_from?: string;
  date_to?: string;
  entry_type?: LedgerEntryType;
}

export interface LedgerBalance {
  income: number;
  expense: number;
  net: number;
}

export interface LedgerCategoryBreakdown {
  category: string;
  total: number;
  count: number;
}

// ============================================================================
// 財務彙總模組 (FinancialSummary) — 對應 schemas/erp/financial_summary.py
// ============================================================================

/** 單一專案財務彙總 */
export interface ProjectFinancialSummary {
  case_code: string;
  project_code?: string;
  case_name?: string;
  erp_quotation_id?: number;
  budget_total?: number;
  quotation_total?: number;
  billed_amount: number;
  received_amount: number;
  vendor_payable_total: number;
  vendor_paid_total: number;
  expense_invoice_count: number;
  expense_invoice_total: number;
  total_income: number;
  total_expense: number;
  net_balance: number;
  budget_used_percentage?: number;
  budget_alert?: string;
}

/** 全公司財務總覽 */
export interface CompanyFinancialOverview {
  period_start: string;
  period_end: string;
  total_income: number;
  total_expense: number;
  net_balance: number;
  expense_by_category: Record<string, number>;
  project_expense: number;
  operation_expense: number;
  top_projects: ProjectFinancialSummary[];
}

export interface ProjectSummaryRequest {
  case_code: string;
}

export interface AllProjectsSummaryRequest {
  year?: number;
  skip?: number;
  limit?: number;
}

export interface CompanyOverviewRequest {
  date_from?: string;
  date_to?: string;
  year?: number;
  top_n?: number;
}

// ============================================================================
// Dashboard 擴展 (Phase 7-D) — 月度趨勢 + 預算排行
// ============================================================================

/** 月度收支趨勢請求 */
export interface MonthlyTrendRequest {
  months?: number;
  case_code?: string;
}

/** 單月收支 */
export interface MonthlyTrendItem {
  month: string;
  income: number;
  expense: number;
  net: number;
}

/** 月度收支趨勢回應 */
export interface MonthlyTrendResponse {
  months: MonthlyTrendItem[];
  case_code?: string;
}

/** 預算使用率排行請求 */
export interface BudgetRankingRequest {
  top_n?: number;
  order?: 'asc' | 'desc';
}

/** 預算排行項目 */
export interface BudgetRankingItem {
  case_code: string;
  case_name?: string;
  budget_total?: number;
  total_expense: number;
  total_income: number;
  usage_pct?: number;
  alert: string;
}

/** 預算使用率排行回應 */
export interface BudgetRankingResponse {
  items: BudgetRankingItem[];
  total_projects: number;
}

// ============================================================================
// 帳齡分析 (Aging Analysis)
// ============================================================================

/** 帳齡區間 */
export interface AgingBucket {
  bucket: string;  // "0-30", "31-60", "61-90", "90+"
  count: number;
  amount: number;
}

/** 帳齡分析結果 */
export interface AgingAnalysis {
  direction: string;
  buckets: AgingBucket[];
  total_outstanding: number;
  total_count: number;
}

/** 帳齡分析請求 */
export interface AgingAnalysisRequest {
  direction: 'receivable' | 'payable';
  year?: number;
}

/** 匯出費用報銷 Excel 請求 */
export interface ExportExpensesRequest {
  date_from?: string;
  date_to?: string;
  case_code?: string;
  status?: string;
  attribution_type?: string;
}

/** 匯出帳本 Excel 請求 */
export interface ExportLedgerRequest {
  date_from?: string;
  date_to?: string;
  case_code?: string;
  entry_type?: string;
}

// ============================================================================
// 電子發票同步模組 (EInvoiceSync) — 對應 schemas/erp/einvoice_sync.py
// ============================================================================

export interface EInvoiceSyncRequest {
  start_date?: string;
  end_date?: string;
}

export interface EInvoiceSyncLog {
  id: number;
  buyer_ban: string;
  query_start: string;
  query_end: string;
  status: string;
  total_fetched: number;
  new_imported: number;
  skipped_duplicate: number;
  detail_fetched: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface EInvoiceSyncLogQuery {
  skip?: number;
  limit?: number;
}

export interface ReceiptUploadRequest {
  invoice_id: number;
  case_code?: string;
  category?: string;
}

export interface PendingReceiptQuery {
  skip?: number;
  limit?: number;
}

// ============================================================================
// API Response Wrappers — 各 API 服務共用分頁回應型別
// ============================================================================

export interface ExpenseListResponse {
  success?: boolean;
  items: ExpenseInvoice[];
  pagination?: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface LedgerListResponse {
  items: FinanceLedger[];
  total: number;
}

export interface ProjectsSummaryResponse {
  items: ProjectFinancialSummary[];
  total: number;
}

export interface SyncResult {
  total_fetched: number;
  new_imported: number;
  skipped_duplicate: number;
}

export interface PendingListResponse {
  items: ExpenseInvoice[];
  total: number;
}

export interface SyncLogsResponse {
  items: EInvoiceSyncLog[];
  total: number;
}

// ============================================================================
// 廠商/委託帳款 — 對應 schemas/erp/vendor_accounts.py / client_accounts.py
// ============================================================================

export interface VendorAccountSummaryItem {
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  case_count: number;
  total_payable: number;
  total_paid: number;
  outstanding: number;
}

export interface VendorCasePayableItem {
  erp_quotation_id: number;
  case_code: string;
  project_code?: string;
  case_name?: string;
  year?: number;
  total_price?: number;
  quotation_status?: string;
  payable_amount: number;
  paid_amount: number;
  outstanding: number;
  payment_status: string;
  items: Array<{
    id: number;
    description?: string;
    payable_amount: number;
    paid_amount: number;
    payment_status: string;
    due_date?: string;
    paid_date?: string;
    invoice_number?: string;
    notes?: string;
  }>;
}

export interface VendorAccountDetail {
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  total_payable: number;
  total_paid: number;
  outstanding: number;
  cases: VendorCasePayableItem[];
}

export interface ClientAccountSummaryItem {
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  case_count: number;
  total_contract: number;
  total_billed: number;
  total_received: number;
  outstanding: number;
}

export interface ClientCaseReceivableItem {
  erp_quotation_id: number;
  case_code: string;
  project_code?: string;
  case_name?: string;
  year?: number;
  quotation_status?: string;
  contract_amount: number;
  total_billed: number;
  total_received: number;
  outstanding: number;
  items: Array<{
    id: number;
    billing_period?: string;
    billing_date?: string;
    billing_amount: number;
    payment_status: string;
    payment_date?: string;
    payment_amount: number;
    notes?: string;
  }>;
}

export interface ClientAccountDetail {
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  total_contract: number;
  total_billed: number;
  total_received: number;
  outstanding: number;
  cases: ClientCaseReceivableItem[];
}

export interface AccountListRequest {
  vendor_type?: string;
  year?: number;
  keyword?: string;
  skip?: number;
  limit?: number;
}

export interface AccountDetailRequest {
  vendor_id: number;
  year?: number;
}

// ============================================================================
// 廠商財務彙總 — 對應 schemas/erp/vendor_financial.py
// ============================================================================

/** 廠商財務彙總 */
export interface VendorFinancialSummary {
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  total_payable: number;
  total_paid: number;
  pending_payable: number;
  payable_count: number;
  total_expenses: number;
  expense_count: number;
  ledger_expense_total: number;
  ledger_entry_count: number;
}

// ============================================================================
// 資產管理模組 (Asset) — 對應 schemas/erp/asset.py
// ============================================================================

/** 資產 */
export interface Asset {
  id: number;
  asset_code: string;
  name: string;
  category: string;
  brand?: string;
  asset_model?: string;
  serial_number?: string;
  purchase_date?: string;
  purchase_amount: number;
  current_value?: number;
  depreciation_rate: number;
  expense_invoice_id?: number;
  case_code?: string;
  status: string;
  location?: string;
  custodian?: string;
  photo_path?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

/** 資產異動記錄 */
export interface AssetLog {
  id: number;
  asset_id: number;
  action: string;
  action_date: string;
  description?: string;
  cost: number;
  expense_invoice_id?: number;
  from_location?: string;
  to_location?: string;
  operator?: string;
  notes?: string;
  created_at?: string;
}

/** 資產統計 */
export interface AssetStats {
  total_count: number;
  in_use: number;
  maintenance: number;
  idle: number;
  disposed: number;
  total_value: number;
  by_category: Record<string, number>;
}

/** 資產列表查詢參數 */
export interface AssetListRequest {
  category?: string;
  status?: string;
  keyword?: string;
  case_code?: string;
  skip?: number;
  limit?: number;
}

/** 批次盤點請求 */
export interface AssetBatchInventoryRequest {
  asset_ids: number[];
  operator: string;
  notes?: string;
}

/** 資產異動記錄建立請求 */
export interface AssetLogCreateRequest {
  asset_id: number;
  action: string;
  action_date: string;
  description?: string;
  cost?: number;
  expense_invoice_id?: number;
  from_location?: string;
  to_location?: string;
  operator?: string;
  notes?: string;
}

// ============================================================================
// 營運帳目模組 (OperationalAccount) — 對應 schemas/erp/operational.py
// ============================================================================

/** 營運帳目類別 */
export const OPERATIONAL_CATEGORIES: Record<string, string> = {
  office: '辦公室營運',
  vehicle: '車輛管理',
  equipment: '設備管理',
  personnel: '人事費用',
  maintenance: '維修保養',
  misc: '雜項',
};

/** 營運帳目狀態 */
export const OPERATIONAL_STATUS: Record<string, string> = {
  active: '啟用',
  closed: '已結束',
  frozen: '凍結',
};

/** 營運帳目 */
export interface OperationalAccount {
  id: number;
  account_code: string;
  name: string;
  category: string;
  fiscal_year: number;
  budget_limit: number;
  department?: string;
  status: string;
  owner_id?: number;
  notes?: string;
  total_spent?: number;
  created_at?: string;
}

/** 營運帳目費用明細 */
export interface OperationalExpense {
  id: number;
  account_id: number;
  expense_date: string;
  amount: number;
  description?: string;
  category?: string;
  expense_invoice_id?: number;
  asset_id?: number;
  approval_status: string;
  approved_by?: number;
  notes?: string;
  created_at?: string;
}

/** 營運帳目統計 */
export interface OperationalAccountStats {
  total_accounts: number;
  total_budget: number;
  total_spent: number;
  by_category: Record<string, { count: number; budget: number; spent: number }>;
}

/** 營運帳目建立請求 */
export interface OperationalAccountCreate {
  name: string;
  category: string;
  fiscal_year: number;
  budget_limit: number;
  department?: string;
  notes?: string;
}

/** 營運帳目更新請求 */
export interface OperationalAccountUpdate {
  name?: string;
  category?: string;
  fiscal_year?: number;
  budget_limit?: number;
  department?: string;
  status?: string;
  notes?: string;
}

/** 營運帳目費用建立請求 */
export interface OperationalExpenseCreate {
  account_id: number;
  expense_date: string;
  amount: number;
  description?: string;
  category?: string;
  expense_invoice_id?: number;
  asset_id?: number;
  notes?: string;
}

// ---------------------------------------------------------------------------
// 案件整合財務紀錄（case-finance）— 2026-07-31 收斂為 SSOT
// ---------------------------------------------------------------------------
// 此型別原本在 pages/pmCase/ExpensesTab.tsx 與 pages/erpQuotation/ExpensesTab.tsx
// **各自宣告一份**。後端欄位一改，兩處都得手動跟，漏改是靜默錯位
//（欄位變 undefined，畫面只少一格、不會報錯）。
// 後端契約：backend/app/schemas/erp/expense.py CaseFinanceResponse（已綁 response_model）。

/** 案件財務紀錄單列（費用核銷 / 請款 / 開票 三種來源統一形狀） */
export interface CaseFinanceRecord {
  type: 'expense' | 'billing' | 'invoice';
  id: number;
  date: string | null;
  amount: number;
  description: string;
  category: string;
  status: string;
  source: string;
}

export interface CaseFinanceSummary {
  expense_count: number;
  expense_total: number;
  billing_count: number;
  billing_total: number;
  invoice_count: number;
  invoice_total: number;
}

export interface CaseFinanceData {
  case_code: string;
  records: CaseFinanceRecord[];
  summary: CaseFinanceSummary;
}

/**
 * 報價狀態 SSOT（2026-08-15）
 *
 * 原本只定義在 ERPQuotationDetailPage 內；列表頁要用就會變成第二份，
 * 而本專案反覆記過「同一件事有兩份說法時，沒有任何一方會報錯」。
 */
export const ERP_QUOTATION_STATUS = [
  { value: 'draft', label: '草稿', color: 'default' },
  { value: 'confirmed', label: '已確認', color: 'success' },
  { value: 'revised', label: '修訂中', color: 'warning' },
  { value: 'closed', label: '已結案', color: 'default' },
] as const;

export const erpQuotationStatusLabel = (v?: string | null): string =>
  ERP_QUOTATION_STATUS.find((o) => o.value === v)?.label ?? (v || '-');

export const erpQuotationStatusColor = (v?: string | null): string =>
  ERP_QUOTATION_STATUS.find((o) => o.value === v)?.color ?? 'default';

/**
 * 資產行為類型 —— 2026-08-16 由 `ERPAssetDetailPage` 的區域常數提升為 SSOT。
 * 原本只寫在詳情頁裡；行為紀錄改為獨立填報頁後兩處都要用，
 * 各留一份就是下一個「兩份說法不一致而沒有人會報錯」。
 */
export const ASSET_ACTION_LABELS: Record<string, string> = {
  purchase: '採購', repair: '維修', maintain: '保養',
  transfer: '調撥', dispose: '報廢', inspect: '盤點', other: '其他',
};

export const ASSET_ACTION_COLORS: Record<string, string> = {
  purchase: 'blue', repair: 'orange', maintain: 'green',
  transfer: 'purple', dispose: 'red', inspect: 'cyan', other: 'default',
};

// ---------------------------------------------------------------------------
// 線上報價單明細（2026-08-16 owner：「線上報價單機制」）
// ---------------------------------------------------------------------------
// 原本宣告在 pages/erpQuotation/QuotationItemsTab.tsx 內。搬到這裡的理由與
// 上面「案件整合財務紀錄」「報價狀態 SSOT」兩例完全相同 ——
// 只要有第二個消費端（例如未來的列印檢視頁或 PDF 匯出）就會出現第二份宣告，
// 而後端欄位一改，漏改的那一份是**靜默錯位**：欄位變 undefined，
// 畫面只少一格、不會報錯。
// 後端契約：backend/app/schemas/erp/quotation.py QuotationItemIn。

/** 報價明細的一列（前端編輯用，`key` 為表格 rowKey 非後端欄位） */
export interface FilingGapItem {
  kind: string;
  ref: string;
  label: string;
  detail: string;
  url: string;
  /** 這個案子還在跑嗎。2026-08-17：62 項缺口裡 44 項是已結案的歷史補登，
   *  把 18 項急件埋在裡面就是告警疲勞。 */
  active: boolean;
}

export interface MyFilingGaps {
  total: number;
  active_total: number;
  items: FilingGapItem[];
}

export interface QuotationItemRow {
  key: string;
  item_name: string;
  spec?: string;
  unit?: string;
  qty: number;
  unit_price: number;
  amount: number;
}

/** 線上報價單完整內容（對應後端 /erp/quotation-items/detail） */
export interface QuotationItemsDetail {
  items: QuotationItemRow[];
  subtotal: number;
  tax_amount: number;
  total: number;
  /** 沒有明細時對外報價單不呈現逐項區塊 */
  has_items: boolean;
}
