/**
 * PM 專案管理型別定義
 * 對應後端 app/schemas/pm/
 */

// Re-export from api.ts SSOT
export type { PMCase, PMCaseCreate, PMCaseUpdate, PMCaseSummary, PMYearlyTrendItem, PMCrossLookup, PMCaseStatus } from './api';
export { PM_CASE_STATUS_LABELS, PM_CASE_STATUS_COLORS, PM_CATEGORY_LABELS } from './api';

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

export const PM_STAFF_ROLE_LABELS: Record<PMStaffRole, string> = {
  project_manager: '專案經理',
  engineer: '工程師',
  surveyor: '測量員',
  assistant: '助理',
  other: '其他',
};

export const PM_CATEGORY_CODES: Record<string, string> = {
  '01': '測量案',
  '02': '資訊案',
  '03': '規劃案',
  '04': '監造案',
  '05': '複合案',
  '99': '其他',
};

/** 跨模組案號查詢結果 */
export interface CrossModuleLookupResult {
  case_code: string;
  pm: { id: number; case_name: string; status: string; progress: number } | null;
  erp: { id: number; case_name: string; status: string; total_price: string; gross_profit: string } | null;
}
