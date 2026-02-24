/**
 * API 業務型別定義
 *
 * 與後端 Pydantic Schema 對應，確保前後端型別一致。
 *
 * 原始 1897 行已拆分至領域型別檔：
 * - document.ts     — 公文、附件、篩選、統計 (~230 行)
 * - taoyuan.ts      — 工程、派工、契金、關聯、總控 (~675 行)
 * - admin-system.ts — 證照、備份、儀表板、MFA (~370 行)
 *
 * 此檔案保留核心型別 (專案/廠商/機關/使用者/行事曆/承攬案件/通用)
 * 並 re-export 所有領域型別，確保 101 個匯入者無需修改。
 *
 * @version 2.0.0
 * @refactored 2026-02-11
 */

// ============================================================================
// Re-export 領域型別（向後相容 — 所有 import { X } from 'types/api' 仍有效）
// ============================================================================

export * from './document';
export * from './taoyuan';
export * from './admin-system';
export * from './deployment';

// ============================================================================
// 公文類別 (Document Category) 常數與判斷函數
// ============================================================================

/**
 * 公文類別常數
 * 用於統一處理資料庫可能存在的中英文混用問題
 */
export const DOCUMENT_CATEGORY = {
  /** 收文 */
  RECEIVE: 'receive',
  /** 發文 */
  SEND: 'send',
  /** 收文（中文） */
  RECEIVE_CN: '收文',
  /** 發文（中文） */
  SEND_CN: '發文',
} as const;

/** 公文類別型別 */
export type DocumentCategoryType = 'receive' | 'send' | '收文' | '發文';

/**
 * 判斷是否為收文
 * @param category 公文類別（可能是中文或英文）
 */
export const isReceiveDocument = (category?: string | null): boolean =>
  category === DOCUMENT_CATEGORY.RECEIVE || category === DOCUMENT_CATEGORY.RECEIVE_CN;

/**
 * 判斷是否為發文
 * @param category 公文類別（可能是中文或英文）
 */
export const isSendDocument = (category?: string | null): boolean =>
  category === DOCUMENT_CATEGORY.SEND || category === DOCUMENT_CATEGORY.SEND_CN;

/**
 * 取得標準化的公文類別（轉為英文）
 * @param category 公文類別
 */
export const normalizeDocumentCategory = (category?: string | null): 'receive' | 'send' | null => {
  if (isReceiveDocument(category)) return 'receive';
  if (isSendDocument(category)) return 'send';
  return null;
};

// ============================================================================
// 專案 (Project) 相關型別
// ============================================================================

/** 專案類別 */
export type ProjectCategory =
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
// 廠商 (Vendor) 相關型別
// ============================================================================

/** 廠商業務類型 */
export type VendorBusinessType =
  | '測量業務'
  | '系統業務'
  | '查估業務'
  | '其他類別';

/** 廠商基礎介面 */
export interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  business_type?: string;
  rating?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** 廠商建立請求 */
export interface VendorCreate {
  vendor_name: string;
  vendor_code?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  business_type?: string;
  rating?: number;
  notes?: string;
}

/** 廠商更新請求 */
export type VendorUpdate = Partial<VendorCreate>;

/** 廠商選項（下拉選單用） */
export interface VendorOption {
  id: number;
  vendor_name: string;
  vendor_code?: string;
}

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

// ============================================================================
// 機關 (Agency) 相關型別
// ============================================================================

/** 機關類型 */
export type AgencyType = '中央機關' | '地方機關' | '民間單位' | '其他';

/** 機關基礎介面 */
export interface Agency {
  id: number;
  agency_name: string;
  agency_short_name?: string;
  agency_code?: string;
  agency_type?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** 機關建立請求 */
export interface AgencyCreate {
  agency_name: string;
  agency_short_name?: string;
  agency_code?: string;
  agency_type?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
}

/** 機關更新請求 */
export type AgencyUpdate = Partial<AgencyCreate>;

/** 機關選項（下拉選單用） */
export interface AgencyOption {
  id: number;
  agency_name: string;
  agency_short_name?: string;
  agency_code?: string;
}

/** 機關（含統計資料） */
export interface AgencyWithStats extends Agency {
  document_count: number;
  sent_count: number;
  received_count: number;
  last_activity: string | null;
  primary_type: 'sender' | 'receiver' | 'both' | 'unknown';
  category?: string;
  original_names?: string[];
}

/** 機關分類統計 */
export interface CategoryStat {
  category: string;
  count: number;
  percentage: number;
}

/** 機關統計資料 */
export interface AgencyStatistics {
  total_agencies: number;
  categories: CategoryStat[];
}

// ============================================================================
// 專案廠商關聯 (ProjectVendor) 相關型別
// ============================================================================

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
// 使用者 (User) 相關型別
// ============================================================================

/** 使用者角色 */
export type UserRole = 'unverified' | 'user' | 'staff' | 'admin' | 'superuser';

/** 使用者狀態 */
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'pending';

/** 使用者基礎介面 - 單一真實來源 (Single Source of Truth) */
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  is_superuser?: boolean;
  role?: string;
  auth_provider?: string;
  avatar_url?: string;
  permissions?: string | string[];
  login_count?: number;
  last_login?: string;
  email_verified?: boolean;
  created_at: string;
  updated_at?: string;
  // 狀態相關欄位
  status?: UserStatus;
  verification_status?: string;
  suspended_reason?: string;
  can_login?: boolean;
  // 組織相關欄位
  department?: string;
  position?: string;
  // MFA 雙因素認證
  mfa_enabled?: boolean;
}

/** 使用者選項（下拉選單用） */
export interface UserOption {
  id: number;
  username: string;
  full_name?: string;
  email?: string;
}

/** 權限定義 */
export interface Permission {
  name: string;
  display_name: string;
  default_permissions: string[];
}

/** 使用者權限 */
export interface UserPermissions {
  user_id: number;
  permissions: string[];
  role: string;
}

/** 使用者表單資料 */
export interface UserFormData {
  email: string;
  username: string;
  full_name?: string;
  password?: string;
  role: string;
  status: string;
  is_admin?: boolean;
  suspended_reason?: string;
}

/** 使用者分頁 */
export interface UserPagination {
  current: number;
  pageSize: number;
  total: number;
}

// ============================================================================
// 管理員使用者管理 (Admin User Management) 相關型別
// ============================================================================

/** 使用者列表查詢參數 */
export interface AdminUserListParams {
  page?: number;
  per_page?: number;
  limit?: number;
  skip?: number;
  q?: string;
  search?: string;
  role?: string;
  auth_provider?: string;
  status?: string;
}

/** 使用者建立/更新請求 */
export interface AdminUserUpdate {
  username?: string;
  email?: string;
  full_name?: string;
  role?: string;
  status?: string;
  is_active?: boolean;
  password?: string;
}

/** 使用者權限更新請求 */
export interface AdminPermissionUpdate {
  user_id: number;
  permissions: string[];
  role: string;
}

/** 使用者列表回應 */
export interface AdminUserListResponse {
  users: User[];
  items?: User[];
  total: number;
  page?: number;
  per_page?: number;
  skip?: number;
  limit?: number;
}

/** 可用權限回應 */
export interface AvailablePermissionsResponse {
  roles: Permission[];
  permissions?: string[];
}

// ============================================================================
// 行事曆事件相關型別
// ============================================================================

/** 行事曆事件提醒 */
export interface CalendarEventReminder {
  id: number;
  reminder_time: string;
  notification_type: 'email' | 'system';
  status: 'pending' | 'sent' | 'failed';
  is_sent: boolean;
  retry_count: number;
}

/** 行事曆事件（後端 API 格式） */
export interface CalendarEvent {
  id: number;
  document_id?: number;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  all_day?: boolean;
  event_type?: 'deadline' | 'meeting' | 'review' | 'reminder' | 'reference' | string;
  priority?: number | string;
  location?: string;
  assigned_user_id?: number;
  created_by?: number;
  created_at?: string;
  updated_at?: string;
  // Google Calendar 整合
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
  // 提醒功能
  status?: 'pending' | 'completed' | 'cancelled';
  reminder_enabled?: boolean;
  reminders?: CalendarEventReminder[];
  // 關聯公文
  doc_number?: string;
}

/** 行事曆事件（前端 UI 格式，使用 datetime 欄位名稱） */
export interface CalendarEventUI {
  id: number;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  all_day?: boolean;  // 全天事件
  document_id?: number;
  doc_number?: string;
  contract_project_name?: string;  // 承攬案件名稱
  event_type?: string;
  priority?: number | string;
  status?: 'pending' | 'completed' | 'cancelled';  // 事件狀態
  location?: string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
}

// ============================================================================
// 行事曆 API 型別 (從 calendarApi.ts 遷移)
// ============================================================================

/** Google Calendar 狀態 */
export interface GoogleCalendarStatus {
  google_calendar_available: boolean;
  connection_status: {
    status: string;
    message: string;
    calendars?: Array<{
      id: string;
      summary: string;
      primary: boolean;
    }>;
  };
  service_type: string;
  supported_event_types: Array<{
    type: string;
    name: string;
    color: string;
  }>;
  features: string[];
}

/** 事件分類 */
export interface EventCategory {
  value: string;
  label: string;
  color: string;
}

/** 行事曆統計 */
export interface CalendarStats {
  total_events: number;
  today_events: number;
  this_week_events: number;
  this_month_events: number;
  upcoming_events: number;
}

/** 行事曆完整回應 */
export interface CalendarDataResponse {
  events: CalendarEventUI[];
  googleStatus: GoogleCalendarStatus;
}

// ============================================================================
// 通用工具型別
// ============================================================================

/** 將所有屬性設為可選 */
export type PartialEntity<T> = {
  [P in keyof T]?: T[P];
};

/** ID 型別 */
export type EntityId = number;

/** 時間戳欄位 */
export interface Timestamps {
  created_at: string;
  updated_at: string;
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
// 通用分頁型別
// ============================================================================

/** 分頁元資料 */
export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ============================================================================
// API 操作回應型別 (從 api/*.ts 遷移)
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

/**
 * 行事曆事件原始 API 回應格式
 * 後端回傳的原始格式，欄位名稱為 start_date/end_date
 * 用於 calendarApi 內部轉換為 CalendarEventUI
 */
export interface RawCalendarEventResponse {
  id: number;
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  all_day?: boolean;
  document_id?: number;
  doc_number?: string;
  contract_project_name?: string;
  event_type?: string;
  priority?: number | string;
  status?: 'pending' | 'completed' | 'cancelled';
  location?: string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
}

// ============================================================================
// 使用者 CRUD 請求型別
// ============================================================================

/** 使用者建立請求 */
export interface UserCreate {
  username: string;
  email: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  password: string;
  department?: string;
  position?: string;
}

/** 使用者更新請求 */
export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  password?: string;
  department?: string;
  position?: string;
}

/** 使用者狀態更新請求 */
export interface UserStatusUpdate {
  is_active: boolean;
}

// ============================================================================
// 公文相關輔助型別
// ============================================================================

/** 下拉選項 */
export interface DropdownOption {
  value: string;
  label: string;
  id?: number;
  year?: number;
  category?: string;
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
  items: import('./admin-system').ProjectAgencyContact[];
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

/** 廠商統計資料 */
export interface VendorStatistics {
  total_vendors: number;
  business_types: Array<{
    business_type: string;
    count: number;
  }>;
  average_rating: number;
}
