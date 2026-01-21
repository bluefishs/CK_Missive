/**
 * API 業務型別定義
 *
 * 與後端 Pydantic Schema 對應，確保前後端型別一致
 */

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
// 公文 (Document) 相關型別
// ============================================================================

/** 公文類型 */
export type DocType = '收文' | '發文' | '函' | '開會通知單' | '會勘通知單';

/** 公文狀態 */
export type DocStatus = '待處理' | '處理中' | '已結案' | 'active' | 'inactive' | 'completed';

/**
 * 公文基礎介面 - 與後端 DocumentResponse 完整對應
 *
 * 虛擬欄位說明 (Virtual Fields):
 * - 標記為 @virtual 的欄位由 API endpoint 在執行時查詢填充
 * - 這些欄位不存儲於資料庫，在建立/更新時會被忽略
 * - 前端應使用對應的 ID 欄位（如 contract_project_id）來關聯資料
 */
export interface OfficialDocument {
  // === 主鍵與核心欄位 ===
  id: number;
  doc_number: string;
  doc_type?: string;
  subject: string;
  sender?: string;
  receiver?: string;
  doc_date?: string;
  receive_date?: string;
  send_date?: string;
  status?: string;
  category?: string;
  contract_case?: string;
  contract_project_id?: number;
  sender_agency_id?: number;
  receiver_agency_id?: number;
  doc_word?: string;
  doc_class?: string;
  assignee?: string;
  user_confirm?: boolean;
  auto_serial?: string;  // 流水序號 (R0001=收文, S0001=發文)
  creator?: string;
  is_deleted?: boolean;
  notes?: string;
  ck_note?: string;  // 簡要說明(乾坤備註)
  priority_level?: string;
  content?: string;
  created_at: string;
  updated_at: string;

  // === 標題與內容欄位 (2026-01-08 新增) ===
  title?: string;            // 標題
  cloud_file_link?: string;  // 雲端檔案連結
  dispatch_format?: string;  // 發文形式 (與 delivery_method 區分)

  // === 發文形式與附件欄位 ===
  delivery_method?: string;   // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;   // 是否含附件
  attachment_count?: number;  // 附件數量

  // === 虛擬欄位 (Virtual Fields) - 由 API endpoint 填充，建立/更新時忽略 ===

  /**
   * @virtual 承攬案件名稱
   * 由 endpoint 從 contract_project_id 查詢 ContractProject.project_name 填充
   * 建立公文時請使用 contract_project_id 而非此欄位
   */
  contract_project_name?: string;

  /**
   * @virtual 負責業務同仁列表
   * 由 endpoint 從 ProjectStaff 表查詢填充
   * 人員指派請使用 ProjectStaff API
   */
  assigned_staff?: Array<{
    user_id: number;
    name: string;
    role: string;
  }>;

  /**
   * @virtual 發文機關名稱
   * 由 endpoint 從 sender_agency_id 查詢 GovernmentAgency.agency_name 填充
   * 建立公文時請使用 sender_agency_id 而非此欄位
   */
  sender_agency_name?: string;

  /**
   * @virtual 受文機關名稱
   * 由 endpoint 從 receiver_agency_id 查詢 GovernmentAgency.agency_name 填充
   * 建立公文時請使用 receiver_agency_id 而非此欄位
   */
  receiver_agency_name?: string;

  // === 前端解析用欄位 ===
  doc_zi?: string;       // 公文「字」部分，如「桃工用」
  doc_wen_hao?: string;  // 公文「文號」部分，如「1140024090」
}

/** 公文建立請求 */
export interface DocumentCreate {
  doc_number: string;
  doc_type: string;
  subject: string;
  sender?: string;
  receiver?: string;
  doc_date?: string;
  receive_date?: string;
  send_date?: string;
  status?: string;
  category?: string;
  contract_case?: string;
  contract_project_id?: number;
  sender_agency_id?: number;
  receiver_agency_id?: number;
  content?: string;           // 說明
  notes?: string;             // 備註
  ck_note?: string;           // 簡要說明(乾坤備註)
  assignee?: string;          // 承辦人
  priority_level?: string;
  // 發文形式與附件欄位
  delivery_method?: string;   // 發文形式
  has_attachment?: boolean;   // 是否含附件
}

/** 公文更新請求 */
export type DocumentUpdate = Partial<DocumentCreate>;

/** 公文附件 - 與後端 DocumentAttachment 對應 */
export interface DocumentAttachment {
  id: number;
  document_id: number;
  filename: string;
  file_name?: string;           // 後端欄位名稱
  original_filename?: string;
  original_name?: string;       // 後端欄位名稱
  file_path?: string;
  file_size: number;
  content_type?: string;
  mime_type?: string;           // 後端欄位名稱
  storage_type?: 'local' | 'network' | 'nas' | 's3';
  checksum?: string;
  uploaded_at?: string;
  uploaded_by?: number;
  created_at?: string;
  updated_at?: string;
}

/** 擴展附件資訊 - 包含所屬公文資訊（用於專案附件彙整） */
export interface ExtendedAttachment extends DocumentAttachment {
  document_number: string;
  document_subject: string;
  uploaded_by_name?: string;
}

/** 按公文分組的附件（用於摺疊顯示） */
export interface GroupedAttachment {
  document_id: number;
  document_number: string;
  document_subject: string;
  file_count: number;
  total_size: number;
  last_updated: string;
  attachments: ExtendedAttachment[];
}

/** 公文篩選參數 */
export interface DocumentFilter {
  // 搜尋欄位
  search?: string;           // 通用搜尋關鍵字
  keyword?: string;          // 關鍵字搜尋 (別名)
  doc_number?: string;       // 公文字號搜尋

  // 類型與狀態篩選
  doc_type?: string;
  category?: string;
  status?: string;
  year?: number;

  // 收發單位篩選
  sender?: string;
  receiver?: string;
  contract_case?: string;
  delivery_method?: string;  // 發文形式 (電子交換/紙本郵寄/電子+紙本)

  // 日期篩選
  date_from?: string;        // 通用起始日期
  date_to?: string;          // 通用結束日期
  doc_date_from?: string;    // 公文日期起始
  doc_date_to?: string;      // 公文日期結束

  // 排序
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 公文統計 */
export interface DocumentStats {
  total_documents: number;
  receive_count: number;
  send_count: number;
  current_year_count: number;
  last_auto_serial?: number;
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
  document_id?: number;
  doc_number?: string;
  event_type?: string;
  priority?: number | string;
  location?: string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
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
// 文件列表相關型別 - 從 document.ts 統一
// ============================================================================

/** 文件列表參數 */
export interface DocumentListParams {
  readonly page?: number;
  readonly limit?: number;
  readonly search?: string;
  readonly status?: DocStatus;
  readonly type?: DocType;
  readonly priority?: DocumentPriority;
  readonly category?: string;
  readonly creator?: string;
  readonly assignee?: string;
  readonly dateFrom?: string;
  readonly dateTo?: string;
}

/** 文件列表響應 */
export interface DocumentListResponse {
  readonly items: readonly OfficialDocument[];
  readonly total: number;
  readonly page: number;
  readonly limit: number;
  readonly total_pages: number;
}

/** 公文優先等級 */
export type DocumentPriority = 'normal' | 'urgent' | 'critical';

// ============================================================================
// 桃園查估派工管理系統 (TaoyuanDispatch) 相關型別
// ============================================================================

/** 作業類別常數 (匹配後端 WORK_TYPES) */
export const TAOYUAN_WORK_TYPES = [
  '#0.專案行政作業',
  '00.專案會議',
  '01.地上物查估作業',
  '02.土地協議市價查估作業',
  '03.土地徵收市價查估作業',
  '04.相關計畫書製作',
  '05.測量作業',
  '06.樁位測釘作業',
  '07.辦理教育訓練',
  '08.作業提繳事項',
] as const;

export type TaoyuanWorkType = (typeof TAOYUAN_WORK_TYPES)[number];

/** 轄管工程基礎介面 (匹配後端 TaoyuanProject Schema) */
export interface TaoyuanProject {
  id: number;
  contract_project_id?: number;

  // 縣府原始資料
  sequence_no?: number;
  review_year?: number;
  case_type?: string;
  district?: string;
  project_name: string;
  start_point?: string;
  start_coordinate?: string;  // 起點坐標(經緯度)
  end_point?: string;
  end_coordinate?: string;    // 迄點坐標(經緯度)
  road_length?: number;
  current_width?: number;
  planned_width?: number;
  public_land_count?: number;
  private_land_count?: number;
  rc_count?: number;
  iron_sheet_count?: number;
  construction_cost?: number;
  land_cost?: number;
  compensation_cost?: number;
  total_cost?: number;
  review_result?: string;
  urban_plan?: string;
  completion_date?: string;
  proposer?: string;
  remark?: string;

  // 派工關聯欄位
  sub_case_name?: string;
  case_handler?: string;
  survey_unit?: string;
  work_type?: string;
  estimated_count?: number;
  cloud_path?: string;
  notes?: string;

  // 進度追蹤欄位
  land_agreement_status?: string;
  land_expropriation_status?: string;
  building_survey_status?: string;
  actual_entry_date?: string;
  acceptance_status?: string;

  created_at?: string;
  updated_at?: string;
}

/** 轄管工程建立請求 */
export interface TaoyuanProjectCreate {
  contract_project_id?: number;
  sequence_no?: number;
  review_year?: number;
  case_type?: string;
  district?: string;
  project_name: string;
  start_point?: string;
  start_coordinate?: string;  // 起點坐標(經緯度)
  end_point?: string;
  end_coordinate?: string;    // 迄點坐標(經緯度)
  road_length?: number;
  current_width?: number;
  planned_width?: number;
  public_land_count?: number;
  private_land_count?: number;
  rc_count?: number;
  iron_sheet_count?: number;
  construction_cost?: number;
  land_cost?: number;
  compensation_cost?: number;
  total_cost?: number;
  review_result?: string;
  urban_plan?: string;
  completion_date?: string;
  proposer?: string;
  remark?: string;
  sub_case_name?: string;
  case_handler?: string;
  survey_unit?: string;
  work_type?: string;
  estimated_count?: number;
  cloud_path?: string;
  notes?: string;
  land_agreement_status?: string;
  land_expropriation_status?: string;
  building_survey_status?: string;
  actual_entry_date?: string;
  acceptance_status?: string;
}

/** 轄管工程更新請求 */
export type TaoyuanProjectUpdate = Partial<TaoyuanProjectCreate>;

/** 轄管工程列表查詢參數 */
export interface TaoyuanProjectListQuery {
  page?: number;
  limit?: number;
  search?: string;
  contract_project_id?: number;
  district?: string;
  review_year?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 轄管工程列表回應 */
export interface TaoyuanProjectListResponse {
  success: boolean;
  items: TaoyuanProject[];
  pagination: PaginationMeta;
}

/** 派工單基礎介面 (匹配後端 DispatchOrder Schema) */
export interface DispatchOrder {
  id: number;
  contract_project_id?: number;
  dispatch_no: string;
  agency_doc_id?: number;
  company_doc_id?: number;
  project_name?: string;
  work_type?: TaoyuanWorkType | string;
  sub_case_name?: string;
  deadline?: string;
  case_handler?: string;
  survey_unit?: string;
  cloud_folder?: string;
  project_folder?: string;
  contact_note?: string; // 聯絡備註 (原始需求欄位 #13)
  created_at?: string;
  updated_at?: string;

  // 關聯資訊（列表顯示用）
  agency_doc_number?: string;
  company_doc_number?: string;
  /** 關聯工程（包含 link_id 和 project_id 用於解除關聯） */
  linked_projects?: (TaoyuanProject & { link_id: number; project_id: number })[];
  /** 關聯公文（使用統一的關聯格式） */
  linked_documents?: DispatchDocumentLink[];
}

/** 派工單關聯的公文資訊 */
export interface DispatchDocumentLink extends BaseLink {
  link_type: LinkType;
  dispatch_order_id: number;
  document_id: number;
  doc_number?: string;
  subject?: string;
  doc_date?: string;
}

/** 派工單建立請求 */
export interface DispatchOrderCreate {
  dispatch_no: string;
  contract_project_id?: number;
  agency_doc_id?: number;
  company_doc_id?: number;
  project_name?: string;
  work_type?: string;
  sub_case_name?: string;
  deadline?: string;
  case_handler?: string;
  survey_unit?: string;
  cloud_folder?: string;
  project_folder?: string;
  contact_note?: string; // 聯絡備註
  linked_project_ids?: number[];
}

/** 派工單更新請求 */
export interface DispatchOrderUpdate {
  dispatch_no?: string;
  contract_project_id?: number;
  agency_doc_id?: number;
  company_doc_id?: number;
  project_name?: string;
  work_type?: string;
  sub_case_name?: string;
  deadline?: string;
  case_handler?: string;
  survey_unit?: string;
  cloud_folder?: string;
  project_folder?: string;
  contact_note?: string; // 聯絡備註
  linked_project_ids?: number[];
}

/** 派工單列表查詢參數 */
export interface DispatchOrderListQuery {
  page?: number;
  limit?: number;
  search?: string;
  contract_project_id?: number;
  work_type?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 派工單列表回應 */
export interface DispatchOrderListResponse {
  success: boolean;
  items: DispatchOrder[];
  pagination: PaginationMeta;
}

/** 工程統計資料 */
export interface ProjectStatistics {
  total_count: number;
  dispatched_count: number;
  completed_count: number;
  completion_rate: number;
}

/** 派工統計資料 */
export interface DispatchStatistics {
  total_count: number;
  with_agency_doc_count: number;
  with_company_doc_count: number;
  work_type_count: number;
}

/** 契金統計資料 */
export interface PaymentStatistics {
  total_current_amount: number;
  total_cumulative_amount: number;
  total_remaining_amount: number;
  payment_count: number;
}

/** 桃園查估派工統計資料回應 */
export interface TaoyuanStatisticsResponse {
  success: boolean;
  projects: ProjectStatistics;
  dispatches: DispatchStatistics;
  payments: PaymentStatistics;
}

/**
 * 派工單公文關聯建立請求
 * 注意：DispatchDocumentLink 已移至關聯類型定義區塊 (繼承 BaseLink)
 */
export interface DispatchDocumentLinkCreate {
  document_id: number;
  link_type: LinkType;
}

/** 契金管控紀錄 (匹配後端 ContractPayment Schema) */
export interface ContractPayment {
  id: number;
  dispatch_order_id: number;

  // 7種作業類別的派工日期/金額
  work_01_date?: string;
  work_01_amount?: number;
  work_02_date?: string;
  work_02_amount?: number;
  work_03_date?: string;
  work_03_amount?: number;
  work_04_date?: string;
  work_04_amount?: number;
  work_05_date?: string;
  work_05_amount?: number;
  work_06_date?: string;
  work_06_amount?: number;
  work_07_date?: string;
  work_07_amount?: number;

  // 彙總欄位
  current_amount?: number;
  cumulative_amount?: number;
  remaining_amount?: number;
  acceptance_date?: string;

  created_at?: string;
  updated_at?: string;

  // 派工單資訊
  dispatch_no?: string;
  project_name?: string;
}

/** 契金管控建立請求 */
export interface ContractPaymentCreate {
  dispatch_order_id: number;
  work_01_date?: string;
  work_01_amount?: number;
  work_02_date?: string;
  work_02_amount?: number;
  work_03_date?: string;
  work_03_amount?: number;
  work_04_date?: string;
  work_04_amount?: number;
  work_05_date?: string;
  work_05_amount?: number;
  work_06_date?: string;
  work_06_amount?: number;
  work_07_date?: string;
  work_07_amount?: number;
  current_amount?: number;
  cumulative_amount?: number;
  remaining_amount?: number;
  acceptance_date?: string;
}

/** 契金管控更新請求 */
export type ContractPaymentUpdate = Partial<Omit<ContractPaymentCreate, 'dispatch_order_id'>>;

/** 契金管控列表回應 */
export interface ContractPaymentListResponse {
  success: boolean;
  items: ContractPayment[];
  pagination: PaginationMeta;
}

// =============================================================================
// 關聯類型定義 (公文-派工-工程三角關係)
// =============================================================================

/** 關聯類型：機關來函 / 乾坤發文 */
export type LinkType = 'agency_incoming' | 'company_outgoing';

/**
 * 基礎關聯介面 (SSOT)
 * 所有關聯型別都必須包含這些欄位
 */
export interface BaseLink {
  /** 關聯記錄 ID (用於刪除操作) */
  link_id: number;
  /** 關聯類型 */
  link_type?: LinkType;
  /** 建立時間 */
  created_at?: string;
}

/**
 * 派工單關聯基礎介面
 * 擴展 BaseLink，包含派工單識別資訊
 */
export interface DispatchLinkBase extends BaseLink {
  /** 派工單 ID */
  dispatch_order_id: number;
  /** 派工單號 */
  dispatch_no: string;
  /** 工程名稱 */
  project_name?: string;
  /** 作業類別 */
  work_type?: string;
}

/**
 * 工程關聯基礎介面
 * 擴展 BaseLink，包含工程識別資訊
 */
export interface ProjectLinkBase extends BaseLink {
  /** 工程 ID */
  project_id: number;
  /** 工程名稱 */
  project_name: string;
}

/** 公文關聯的派工單資訊 (完整版) */
export interface DocumentDispatchLink extends DispatchLinkBase {
  link_type: LinkType; // 必填（覆蓋可選）
  sub_case_name?: string;
  deadline?: string;
  case_handler?: string;
  survey_unit?: string;
  contact_note?: string;
  cloud_folder?: string;
  project_folder?: string;
  agency_doc_number?: string;
  company_doc_number?: string;
}

/** 公文關聯的工程資訊 (完整版) */
export interface DocumentProjectLink extends ProjectLinkBase {
  notes?: string;
  district?: string;
  review_year?: number;
  case_type?: string;
  sub_case_name?: string;
  case_handler?: string;
  survey_unit?: string;
  start_point?: string;
  end_point?: string;
  road_length?: number;
  current_width?: number;
  planned_width?: number;
  review_result?: string;
}

/** 工程關聯的派工單資訊 (簡化版) */
export interface ProjectDispatchLink extends DispatchLinkBase {
  // 繼承 DispatchLinkBase 的所有欄位
}

/** 總控表查詢參數 */
export interface MasterControlQuery {
  contract_project_id?: number;
  district?: string;
  review_year?: number;
  search?: string;
}

/** 公文歷程資訊 */
export interface DocumentHistory {
  doc_number: string;
  doc_date?: string;
  subject?: string;
}

/** 總控表項目 (匹配後端 MasterControlItem Schema) */
export interface MasterControlItem {
  // 工程基本資訊
  id: number;
  project_name: string;
  sub_case_name?: string;
  district?: string;
  review_year?: number;

  // 進度追蹤
  land_agreement_status?: string;
  land_expropriation_status?: string;
  building_survey_status?: string;
  actual_entry_date?: string;
  acceptance_status?: string;

  // 派工資訊
  dispatch_no?: string;
  case_handler?: string;
  survey_unit?: string;

  // 公文歷程
  agency_documents?: DocumentHistory[];
  company_documents?: DocumentHistory[];

  // 契金資訊
  payment_info?: ContractPayment;
}

/** 總控表回應 */
export interface MasterControlResponse {
  success: boolean;
  items: MasterControlItem[];
  summary: MasterControlSummary;
}

/** 總控表摘要統計 (匹配後端回應) */
export interface MasterControlSummary {
  total_projects: number;
  total_dispatches: number;
  total_agency_docs: number;
  total_company_docs: number;
}

/** Excel 匯入請求 */
export interface ExcelImportRequest {
  contract_project_id: number;
  review_year?: number;
}

/** Excel 匯入結果 */
export interface ExcelImportResult {
  success: boolean;
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  error_count: number;
  errors: ExcelImportError[];
}

/** Excel 匯入錯誤 */
export interface ExcelImportError {
  row: number;
  field?: string;
  message: string;
}

// ============================================================================
// 公文歷程匹配型別 (對應原始需求欄位 14-17)
// ============================================================================

/** 公文歷程項目 (詳細版，用於匹配 API) */
export interface DocumentHistoryItem {
  id: number;
  doc_number?: string;
  doc_date?: string;
  subject?: string;
  sender?: string;
  receiver?: string;
  doc_type?: '收文' | '發文';
  match_type?: 'project_name' | 'subject';
}

/** 公文歷程匹配回應 */
export interface DocumentHistoryMatchResponse {
  success: boolean;
  project_name: string;
  agency_documents: DocumentHistoryItem[];
  company_documents: DocumentHistoryItem[];
  total_agency_docs: number;
  total_company_docs: number;
}

/** 派工單詳情 (含公文歷程) */
export interface DispatchOrderWithHistory extends DispatchOrder {
  // 公文歷程欄位 (對應原始需求欄位 14-17)
  agency_doc_history_by_name?: DocumentHistoryItem[];
  agency_doc_history_by_subject?: DocumentHistoryItem[];
  company_doc_history_by_name?: DocumentHistoryItem[];
  company_doc_history_by_subject?: DocumentHistoryItem[];
}

/** 派工單詳情含歷程回應 */
export interface DispatchOrderWithHistoryResponse {
  success: boolean;
  data: DispatchOrderWithHistory;
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
