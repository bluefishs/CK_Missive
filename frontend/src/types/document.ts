/**
 * 公文 (Document) 相關型別
 *
 * @extracted-from api.ts (lines 407-609, 806-834)
 * @version 1.0.0
 * @created 2026-02-11
 */

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
  doc_word?: string;          // 公文文別
  doc_class?: string;         // 公文分類
}

/** 公文更新請求 — 包含 DocumentCreate 所有欄位(可選) + 更新專用欄位 */
export interface DocumentUpdate extends Partial<DocumentCreate> {
  title?: string;
  cloud_file_link?: string;
  dispatch_format?: string;
  auto_serial?: string;
}

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

/** 公文統計（簡易版） */
export interface DocumentStats {
  total_documents: number;
  receive_count: number;
  send_count: number;
  current_year_count: number;
  last_auto_serial?: number;
}

/** 公文統計資料（完整版 - API 回應） */
export interface DocumentStatistics {
  total: number;
  total_documents: number;
  send: number;
  send_count: number;
  receive: number;
  receive_count: number;
  current_year_count: number;
  current_year_send_count: number;
  delivery_method_stats: {
    electronic: number;
    paper: number;
    both: number;
  };
}

/** 下一個發文字號回應 */
export interface NextSendNumberResponse {
  /** 完整文號 (如: 乾坤測字第1150000001號) */
  full_number: string;
  /** 西元年 */
  year: number;
  /** 民國年 */
  roc_year: number;
  /** 流水號 */
  sequence_number: number;
  /** 前一個最大序號 */
  previous_max: number;
  /** 文號前綴 */
  prefix: string;
}

// ============================================================================
// 文件列表相關型別
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
// 檔案管理 API 型別 (從 filesApi.ts 遷移)
// ============================================================================

/** 上傳結果 */
export interface UploadResult {
  success: boolean;
  message: string;
  files: Array<{
    id: number | null;
    filename: string;
    original_name: string;
    size: number;
    content_type: string;
    checksum: string;
    storage_path: string;
    uploaded_by: string | null;
  }>;
  errors?: string[];
}

/** 上傳進度回調 */
export interface UploadProgressCallback {
  onProgress?: (percent: number, loaded: number, total: number) => void;
  onSuccess?: (result: UploadResult) => void;
  onError?: (error: Error) => void;
}

/** 儲存資訊 */
export interface StorageInfo {
  success: boolean;
  storage_path: string;
  storage_type: 'local' | 'network' | 'nas';
  is_network_path: boolean;
  network_ip?: string;
  is_local_ip?: boolean;
  total_files: number;
  total_size_mb: number;
  allowed_extensions: string[];
  max_file_size_mb: number;
  disk_info?: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    usage_percent: number;
  };
}

/** 網路檢查結果 */
export interface NetworkCheckResult {
  success: boolean;
  storage_path: string;
  storage_type: string;
  is_network_path: boolean;
  network_ip?: string;
  is_local_ip?: boolean;
  healthy: boolean;
  checks: {
    path_exists: boolean;
    writable: boolean;
    write_error?: string;
    network_reachable?: boolean;
    connected_port?: number;
    network_error?: string;
  };
}

/** 檔案驗證結果 */
export interface FileVerifyResult {
  success: boolean;
  file_id: number;
  status: 'valid' | 'corrupted' | 'file_missing' | 'read_error' | 'no_checksum';
  is_valid?: boolean;
  stored_checksum?: string;
  current_checksum?: string;
  message: string;
}

/** 刪除結果 */
export interface DeleteResult {
  success: boolean;
  message: string;
  deleted_by?: string;
}

/** 附件列表回應 */
export interface AttachmentListResponse {
  success: boolean;
  document_id: number;
  total: number;
  attachments: DocumentAttachment[];
}
