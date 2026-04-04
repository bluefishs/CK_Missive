/** api-project — 專案/承攬案件/人員/廠商關聯型別 */

import type { Vendor } from './api-entity';
import type { User } from './api-user';
import type { ProjectAgencyContact } from './admin-system';

// ============================================================================
// 專案 (Project) 相關型別
// ============================================================================

/** 專案類別 */
export type ProjectCategory =
  | '01委辦招標'
  | '02承攬報價'
  // 舊格式相容
  | '01委辦案件'
  | '02協力計畫'
  | '03小額採購'
  | '04其他類別';

/** 專案狀態 */
export type ProjectStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'suspended';

/** 專案基礎介面 */
export interface Project {
  id: number;
  project_name: string;
  project_code?: string;
  case_code?: string;
  year?: number;
  client_agency?: string;
  category?: string;
  case_nature?: string;           // 案件性質 (01測量案/02資訊案/03複合案)
  contract_doc_number?: string;
  contract_amount?: number;
  winning_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: ProjectStatus;
  progress?: number;
  notes?: string;
  project_path?: string;
  description?: string;
  // ORM 對齊欄位 (v1.55.0)
  contract_number?: string;
  contract_type?: string;
  location?: string;
  procurement_method?: string;
  completion_date?: string;
  acceptance_date?: string;
  completion_percentage?: number;
  warranty_end_date?: string;
  contact_person?: string;
  contact_phone?: string;
  client_agency_id?: number;
  agency_contact_person?: string;
  agency_contact_phone?: string;
  agency_contact_email?: string;
  has_dispatch_management?: boolean;
  client_type?: 'agency' | 'vendor' | 'other';
  created_at: string;
  updated_at: string;
}

/** 專案建立請求 */
export interface ProjectCreate {
  project_name: string;
  project_code?: string;
  year?: number;
  client_agency?: string;
  category?: string;
  case_nature?: string;
  contract_doc_number?: string;
  contract_amount?: number;
  winning_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: ProjectStatus;
  progress?: number;
  notes?: string;
  project_path?: string;
  description?: string;
  // ORM 對齊欄位 (v1.55.0)
  contract_number?: string;
  contract_type?: string;
  location?: string;
  procurement_method?: string;
  completion_date?: string;
  acceptance_date?: string;
  completion_percentage?: number;
  warranty_end_date?: string;
  contact_person?: string;
  contact_phone?: string;
  client_agency_id?: number;
  agency_contact_person?: string;
  agency_contact_phone?: string;
  agency_contact_email?: string;
  has_dispatch_management?: boolean;
  client_type?: 'agency' | 'vendor' | 'other';
}

/** 專案更新請求 */
export type ProjectUpdate = Partial<ProjectCreate>;

/** 專案選項（下拉選單用） */
export interface ProjectOption {
  id: number;
  project_name: string;
  project_code?: string;
  year?: number;
}

// ============================================================================
// 專案廠商關聯 (ProjectVendor) 相關型別
// ============================================================================

/** 專案廠商關聯 - 用於承攬案件中的協力廠商列表 */
export interface ProjectVendorAssociation {
  id: number;
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  contact_person?: string;
  phone?: string;
  role: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status: string;
}

/** 廠商角色 */
export type VendorRole = '主承包商' | '分包商' | '供應商';

/** 專案廠商關聯 */
export interface ProjectVendor {
  id?: number;
  project_id: number;
  vendor_id: number;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  // 關聯資料（從 join 取得）
  vendor?: Vendor;
  vendor_name?: string;
  // API 回應擴展欄位
  vendor_contact_person?: string;
  vendor_phone?: string;
  vendor_business_type?: string;
}

/** 專案廠商建立請求 */
export interface ProjectVendorCreate {
  project_id: number;
  vendor_id: number;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
}

// ============================================================================
// 專案人員關聯 (ProjectStaff) 相關型別
// ============================================================================

/** 人員角色 */
export type StaffRole = '計畫主持' | '計畫協同' | '專案PM' | '職安主管' | '成員';

/** 專案人員關聯 */
export interface ProjectStaff {
  id: number;
  project_id: number;
  user_id: number;
  role?: string;
  is_primary?: boolean;
  assignment_date?: string;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  // 關聯資料（從 join 取得）
  user?: User;
  user_name?: string;
  username?: string;
  full_name?: string;
  // API 回應擴展欄位
  user_email?: string;
  department?: string;
  phone?: string;
}

/** 專案人員建立請求 */
export interface ProjectStaffCreate {
  project_id: number;
  user_id: number;
  role?: string;
  is_primary?: boolean;
  assignment_date?: string;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
}

// ============================================================================
// 承攬案件 (ContractCase) 相關型別 - 從 contractCase.ts 統一
// ============================================================================

/** 承攬案件介面 */
export interface ContractCase {
  id: number;
  year: string;
  project_name: string;
  client_unit: string;
  contract_period_start: string;
  contract_period_end: string;
  responsible_staff: string;
  partner_vendor: string;
  case_type: ContractCaseType;
  case_status: ContractCaseStatus;
  contract_amount?: number;
  description?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** 案件性質分類 */
export enum ContractCaseType {
  INNOVATION = 0,
  COMMISSION = 1,
  COOPERATION = 2,
  EXTENSION = 3,
  SMALL_PURCHASE = 4,
}

/** 案件性質標籤 */
export const CONTRACT_CASE_TYPE_LABELS = {
  [ContractCaseType.INNOVATION]: '創新專案',
  [ContractCaseType.COMMISSION]: '委辦計畫',
  [ContractCaseType.COOPERATION]: '協辦計畫',
  [ContractCaseType.EXTENSION]: '委辦擴充',
  [ContractCaseType.SMALL_PURCHASE]: '小額採購',
} as const;

/** 案件性質顏色 */
export const CONTRACT_CASE_TYPE_COLORS = {
  [ContractCaseType.INNOVATION]: 'purple',
  [ContractCaseType.COMMISSION]: 'blue',
  [ContractCaseType.COOPERATION]: 'green',
  [ContractCaseType.EXTENSION]: 'orange',
  [ContractCaseType.SMALL_PURCHASE]: 'cyan',
} as const;

/** 案件狀態 */
export enum ContractCaseStatus {
  PLANNED = 'planned',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  SUSPENDED = 'suspended',
  CANCELLED = 'cancelled',
}

/** 案件狀態標籤 */
export const CONTRACT_CASE_STATUS_LABELS = {
  [ContractCaseStatus.PLANNED]: '規劃中',
  [ContractCaseStatus.IN_PROGRESS]: '執行中',
  [ContractCaseStatus.COMPLETED]: '已完成',
  [ContractCaseStatus.SUSPENDED]: '暫停',
  [ContractCaseStatus.CANCELLED]: '已取消',
} as const;

/** 案件狀態顏色 */
export const CONTRACT_CASE_STATUS_COLORS = {
  [ContractCaseStatus.PLANNED]: 'default',
  [ContractCaseStatus.IN_PROGRESS]: 'processing',
  [ContractCaseStatus.COMPLETED]: 'success',
  [ContractCaseStatus.SUSPENDED]: 'warning',
  [ContractCaseStatus.CANCELLED]: 'error',
} as const;

/** 承攬案件篩選條件 */
export interface ContractCaseFilter {
  search?: string;
  year?: string;
  case_type?: ContractCaseType;
  case_status?: ContractCaseStatus;
  client_unit?: string;
  responsible_staff?: string;
  partner_vendor?: string;
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

/** 承攬案件列表參數 */
export interface ContractCaseListParams {
  page?: number;
  limit?: number;
  filters?: ContractCaseFilter;
}

/** 承攬案件列表響應 */
export interface ContractCaseListResponse {
  items: ContractCase[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

/** 視圖模式 */
export type ViewMode = 'board' | 'list';

/** 看板項目 */
export interface BoardItem extends ContractCase {
  progress?: number;
}

// ============================================================================
// API 操作回應型別
// ============================================================================

/** 協力廠商操作回應 */
export interface VendorOperationResponse {
  message: string;
  project_id: number;
  vendor_id: number;
}

/** 承辦同仁操作回應 */
export interface StaffOperationResponse {
  message: string;
  project_id: number;
  user_id: number;
}

// ============================================================================
// 專案廠商 CRUD 請求/回應型別
// ============================================================================

/** 協力廠商列表回應 */
export interface ProjectVendorListResponse {
  project_id: number;
  project_name: string;
  associations: ProjectVendor[];
  total: number;
}

/** 新增協力廠商請求 */
export interface ProjectVendorRequest {
  project_id: number;
  vendor_id: number;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
}

/** 更新協力廠商請求 */
export interface ProjectVendorUpdate {
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
}

// ============================================================================
// 專案人員 CRUD 請求/回應型別
// ============================================================================

/** 承辦同仁列表回應 */
export interface ProjectStaffListResponse {
  project_id: number;
  project_name: string;
  staff: ProjectStaff[];
  total: number;
}

/** 新增/更新承辦同仁請求 */
export interface ProjectStaffRequest {
  project_id: number;
  user_id: number;
  role?: string;
  is_primary?: boolean;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
}

/** 承辦同仁更新請求 */
export interface ProjectStaffUpdate {
  role?: string;
  is_primary?: boolean;
  start_date?: string;
  end_date?: string;
  status?: string;
  notes?: string;
}

// ============================================================================
// 專案機關承辦型別
// ============================================================================

/** 專案機關承辦列表回應 */
export interface ProjectAgencyContactListResponse {
  items: ProjectAgencyContact[];
  total: number;
}

// ============================================================================
// 統計型別
// ============================================================================

/** 專案統計資料 */
export interface ProjectStatistics {
  total_projects: number;
  status_breakdown: Array<{
    status: string;
    count: number;
  }>;
  year_breakdown: Array<{
    year: number;
    count: number;
  }>;
  average_contract_amount: number;
}
