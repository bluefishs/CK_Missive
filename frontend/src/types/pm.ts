/**
 * PM 專案管理型別定義
 * 對應後端 app/schemas/pm/
 */

import type { ERPQuotation } from './erp';

// ============================================================================
// PM 案件核心型別 (原定義於 api.ts)
// ============================================================================

/** PM 案件狀態
 *
 * ⚠️ `in_progress` 是**後端在成案成功後自己寫入的**，不是使用者選的：
 * `CaseCodeService.promote_to_project` 在建立 ContractProject、寫入 project_code 之後
 * 會把 PM 案件設為 `in_progress`（語意＝已成案、進入執行）。
 *
 * 2026-08-10 之前這個值不在本詞彙內，於是前端的預設值 fallback 把它顯示成「評估中」——
 * owner 把承攬狀態改成「已承攬」、成案其實**成功了**（產號、ContractProject、ERP 報價都建了），
 * 回到畫面卻看到「評估中」，看起來就像「改了沒反應」。
 * 產出端與消費端對同一個欄位的詞彙不一致，兩邊都不會報錯。
 */
export type PMCaseStatus = 'planning' | 'contracted' | 'in_progress' | 'closed';

/** PM 案件狀態標籤 */
export const PM_CASE_STATUS_LABELS: Record<PMCaseStatus, string> = {
  planning: '評估中',
  contracted: '已承攬',
  in_progress: '執行中',
  closed: '已結案',
};

/** PM 案件狀態顏色 */
export const PM_CASE_STATUS_COLORS: Record<PMCaseStatus, string> = {
  planning: 'default',
  contracted: 'blue',
  in_progress: 'processing',
  closed: 'success',
};

/** PM 案件類別 */
export const PM_CATEGORY_LABELS: Record<string, string> = {
  '01': '委辦招標',
  '02': '承攬報價',
};

/** PM 案件 */
export interface PMCase {
  id: number;
  case_code: string;
  project_code?: string;
  case_name: string;
  year?: number;
  category?: string;
  case_nature?: string;
  client_name?: string;
  client_vendor_id?: number;
  client_contact?: string;
  client_phone?: string;
  contract_amount?: number;
  status: PMCaseStatus;
  progress: number;
  start_date?: string;
  end_date?: string;
  actual_end_date?: string;
  location?: string;
  description?: string;
  notes?: string;
  created_by?: number;
  created_at?: string;
  updated_at?: string;
  milestone_count: number;
  staff_count: number;
}

/** PM 案件建立 */
export interface PMCaseCreate {
  case_code?: string;
  case_name: string;
  year?: number;
  category?: string;
  case_nature?: string;
  client_name?: string;
  client_vendor_id?: number;
  client_contact?: string;
  client_phone?: string;
  contract_amount?: number;
  status?: string;
  start_date?: string;
  end_date?: string;
  location?: string;
  description?: string;
  notes?: string;
}

/** PM 案件更新 */
export type PMCaseUpdate = Partial<PMCaseCreate> & {
  progress?: number;
  actual_end_date?: string;
};

/** PM 案件統計摘要 */
export interface PMCaseSummary {
  total_cases: number;
  by_status: Record<string, number>;
  by_year: Record<string, number>;
  total_contract_amount?: number;
}

/** PM 多年度趨勢 */
export interface PMYearlyTrendItem {
  year: number;
  case_count: number;
  total_contract: number;
  closed_count: number;
  in_progress_count: number;
  avg_progress: number;
}

/** PM 跨模組查詢結果 */
export interface PMCrossLookup {
  pm_case?: PMCase;
  erp_quotation?: ERPQuotation;
  case_code: string;
}

// ============================================================================
// PM 擴展型別
// ============================================================================

/** PM 案件列表查詢參數 */
export interface PMCaseListParams {
  page?: number;
  page_size?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  year?: number;
  status?: string;
  category?: string;
  case_nature?: string;
  search?: string;
  client_name?: string;
  [key: string]: unknown;
}

/** PM 里程碑 */
export interface PMMilestone {
  id: number;
  pm_case_id: number;
  milestone_name: string;
  milestone_type?: string;
  planned_date?: string;
  actual_date?: string;
  status: string;
  sort_order: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PMMilestoneCreate {
  pm_case_id: number;
  milestone_name: string;
  milestone_type?: string;
  planned_date?: string;
  actual_date?: string;
  status?: string;
  sort_order?: number;
  notes?: string;
}

export type PMMilestoneUpdate = Partial<Omit<PMMilestoneCreate, 'pm_case_id'>>;

/** PM 案件人員 */
export interface PMCaseStaff {
  id: number;
  pm_case_id: number;
  user_id?: number;
  staff_name: string;
  role: string;
  is_primary: boolean;
  start_date?: string;
  end_date?: string;
  notes?: string;
  created_at?: string;
}

export interface PMCaseStaffCreate {
  pm_case_id: number;
  user_id?: number;
  staff_name: string;
  role: string;
  is_primary?: boolean;
  start_date?: string;
  end_date?: string;
  notes?: string;
}

export type PMCaseStaffUpdate = Partial<Omit<PMCaseStaffCreate, 'pm_case_id'>>;

// ============================================================================
// Extended types for sub-module consumers
// ============================================================================

export type PMMilestoneType = 'kickoff' | 'design' | 'review' | 'submission' | 'acceptance' | 'warranty' | 'other';
export type PMMilestoneStatus = 'pending' | 'in_progress' | 'completed' | 'overdue' | 'skipped';
export type PMStaffRole = 'project_manager' | 'engineer' | 'surveyor' | 'assistant' | 'other';

export interface PMLinkedDocument {
  readonly id: number;
  readonly doc_number: string | null;
  readonly subject: string | null;
  readonly doc_type: string | null;
  readonly doc_date: string | null;
}

export const PM_MILESTONE_TYPE_LABELS: Record<PMMilestoneType, string> = {
  kickoff: '開工',
  design: '設計',
  review: '審查',
  submission: '送件',
  acceptance: '驗收',
  warranty: '保固',
  other: '其他',
};

/**
 * 里程碑狀態標籤。
 * 2026-08-02 由 MilestonesTab 內的區域常數提升至型別 SSOT —— 填報頁抽成獨立路由後
 * 有第二個消費端，留在元件內就會變成兩份各自演化的定義（異質同工）。
 */
export const PM_MILESTONE_STATUS_LABELS: Record<PMMilestoneStatus, string> = {
  pending: '待辦',
  in_progress: '進行中',
  completed: '已完成',
  overdue: '逾期',
  skipped: '略過',
};

export const PM_STAFF_ROLE_LABELS: Record<PMStaffRole, string> = {
  project_manager: '專案經理',
  engineer: '工程師',
  surveyor: '測量員',
  assistant: '助理',
  other: '其他',
};

export const PM_CATEGORY_CODES: Record<string, string> = {
  '01': '委辦招標',
  '02': '承攬報價',
};

/** 跨模組案號查詢結果 */
export interface CrossModuleLookupResult {
  case_code: string;
  pm: { id: number; case_name: string; status: string; progress: number } | null;
  erp: { id: number; case_name: string; status: string; total_price: string; gross_profit: string } | null;
}
