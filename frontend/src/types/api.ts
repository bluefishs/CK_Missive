/**
 * API 業務型別定義
 *
 * 與後端 Pydantic Schema 對應，確保前後端型別一致
 */

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

/** 使用者基礎介面 */
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
  permissions?: string;
  login_count?: number;
  last_login?: string;
  email_verified?: boolean;
  created_at: string;
  updated_at?: string;
}

/** 使用者選項（下拉選單用） */
export interface UserOption {
  id: number;
  username: string;
  full_name?: string;
  email?: string;
}

// ============================================================================
// 公文 (Document) 相關型別
// ============================================================================

/** 公文類型 */
export type DocType = '收文' | '發文' | '函' | '開會通知單' | '會勘通知單';

/** 公文狀態 */
export type DocStatus = '待處理' | '處理中' | '已結案' | 'active' | 'inactive' | 'completed';

/** 公文基礎介面 - 與後端 DocumentResponse 完整對應 */
export interface OfficialDocument {
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
  priority_level?: string;
  content?: string;
  created_at: string;
  updated_at: string;

  // 標題與內容欄位 (2026-01-08 新增)
  title?: string;            // 標題
  cloud_file_link?: string;  // 雲端檔案連結
  dispatch_format?: string;  // 發文形式 (與 delivery_method 區分)

  // 發文形式與附件欄位
  delivery_method?: string;   // 發文形式 (電子交換/紙本郵寄/電子+紙本)
  has_attachment?: boolean;   // 是否含附件
  attachment_count?: number;  // 附件數量

  // 承攬案件關聯資訊 (由後端填充)
  contract_project_name?: string;  // 承攬案件名稱
  assigned_staff?: Array<{         // 負責業務同仁
    user_id: number;
    name: string;
    role: string;
  }>;

  // 機關名稱（虛擬欄位，由後端填充）
  sender_agency_name?: string;    // 發文機關名稱
  receiver_agency_name?: string;  // 受文機關名稱

  // 公文字號拆分欄位（前端解析用）
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

/** 行事曆事件 */
export interface CalendarEvent {
  id: number;
  document_id?: number;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  all_day?: boolean;
  event_type?: string;
  priority?: string;
  location?: string;
  assigned_user_id?: number;
  created_by?: number;
  created_at: string;
  updated_at: string;
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
