/**
 * 系統管理相關型別
 *
 * 證照管理、專案機關承辦、使用者會話、備份管理、
 * 儀表板統計、登入歷史、MFA 雙因素認證
 *
 * @extracted-from api.ts (lines 1527-1897)
 * @version 1.0.0
 * @created 2026-02-11
 */

// ============================================================================
// 證照管理型別 (Certifications)
// ============================================================================

/** 證照類型選項 */
export const CERT_TYPES = ['核發證照', '評量證書', '訓練證明'] as const;
export type CertType = typeof CERT_TYPES[number];

/** 證照狀態選項 */
export const CERT_STATUS = ['有效', '已過期', '已撤銷'] as const;
export type CertStatus = typeof CERT_STATUS[number];

/** 證照基礎介面 */
export interface Certification {
  id: number;
  user_id: number;
  cert_type: CertType;
  cert_name: string;
  issuing_authority?: string;
  cert_number?: string;
  issue_date?: string;
  expiry_date?: string;
  status: CertStatus;
  notes?: string;
  attachment_path?: string;
  created_at?: string;
  updated_at?: string;
}

/** 建立證照請求 */
export interface CertificationCreate {
  user_id: number;
  cert_type: CertType;
  cert_name: string;
  issuing_authority?: string;
  cert_number?: string;
  issue_date?: string;
  expiry_date?: string;
  status?: CertStatus;
  notes?: string;
}

/** 更新證照請求 */
export interface CertificationUpdate {
  cert_type?: CertType;
  cert_name?: string;
  issuing_authority?: string;
  cert_number?: string;
  issue_date?: string;
  expiry_date?: string;
  status?: CertStatus;
  notes?: string;
  attachment_path?: string;
}

/** 證照列表查詢參數 */
export interface CertificationListParams {
  page?: number;
  page_size?: number;
  cert_type?: CertType;
  status?: CertStatus;
  keyword?: string;
}

/** 證照統計 */
export interface CertificationStats {
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  total: number;
}

// ============================================================================
// 專案機關承辦 (ProjectAgencyContact) 相關型別
// ============================================================================

/** 專案機關承辦介面 */
export interface ProjectAgencyContact {
  id: number;
  project_id: number;
  contact_name: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

/** 專案機關承辦建立請求 */
export interface ProjectAgencyContactCreate {
  project_id: number;
  contact_name: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary?: boolean;
  notes?: string;
}

/** 專案機關承辦更新請求 */
export interface ProjectAgencyContactUpdate {
  contact_name?: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary?: boolean;
  notes?: string;
}

// ============================================================================
// 使用者會話 (UserSession) 相關型別
// ============================================================================

/** 使用者會話資訊 */
export interface UserSession {
  id: number;
  user_id: number;
  token_hash?: string;
  device_info?: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  expires_at: string;
  last_activity?: string;
  is_active: boolean;
}

// ============================================================================
// 備份管理 (Backup) 相關型別
// ============================================================================

/** 備份項目 */
export interface BackupItem {
  /** 檔案名稱 (資料庫備份) */
  filename?: string;
  /** 目錄名稱 (附件備份) */
  dirname?: string;
  /** 完整路徑 */
  path: string;
  /** 大小 (bytes) */
  size_bytes: number;
  /** 大小 (KB) - 資料庫備份 */
  size_kb?: number;
  /** 大小 (MB) - 附件備份 */
  size_mb?: number;
  /** 檔案數量 - 附件備份 */
  file_count?: number;
  /** 建立時間 */
  created_at: string;
  /** 備份類型 */
  type: 'database' | 'attachments';
  /** 複製的檔案數 - 增量備份 */
  copied_count?: number;
  /** 跳過的檔案數 - 增量備份 */
  skipped_count?: number;
  /** 移除的檔案數 - 增量備份 */
  removed_count?: number;
  /** 備份模式 */
  mode?: 'full' | 'incremental';
  /** 本次複製大小 (MB) */
  copied_size_mb?: number;
}

/** 備份統計資訊 */
export interface BackupStatistics {
  database_backup_count: number;
  attachment_backup_count: number;
  total_database_size_mb: number;
  total_attachment_size_mb: number;
  total_size_mb: number;
}

/** 備份列表回應 */
export interface BackupListResponse {
  database_backups: BackupItem[];
  attachment_backups: BackupItem[];
  statistics: BackupStatistics;
}

/** 建立備份請求 */
export interface CreateBackupRequest {
  include_database: boolean;
  include_attachments: boolean;
  retention_days: number;
}

/** 刪除備份請求 */
export interface DeleteBackupRequest {
  backup_name: string;
  backup_type: 'database' | 'attachments';
}

/** 還原備份請求 */
export interface RestoreBackupRequest {
  backup_name: string;
}

/** 異地備份設定 */
export interface RemoteBackupConfig {
  remote_path?: string;
  sync_enabled: boolean;
  sync_interval_hours: number;
  last_sync_time?: string;
  sync_status: string;
}

/** 異地備份設定請求 */
export interface RemoteBackupConfigRequest {
  remote_path: string;
  sync_enabled: boolean;
  sync_interval_hours: number;
}

/** 排程器統計資訊 */
export interface SchedulerStats {
  total_backups: number;
  successful_backups: number;
  failed_backups: number;
  last_backup_result?: Record<string, unknown>;
}

/** 排程器狀態 */
export interface SchedulerStatus {
  running: boolean;
  backup_time: string;
  next_backup?: string;
  last_backup?: string;
  stats: SchedulerStats;
}

/** 備份日誌項目 */
export interface BackupLogEntry {
  id: number;
  timestamp: string;
  action: 'create' | 'delete' | 'restore' | 'sync' | 'config_update';
  status: 'success' | 'failed' | 'in_progress';
  details?: string;
  backup_name?: string;
  file_size_kb?: number;
  duration_seconds?: number;
  error_message?: string;
  operator?: string;
}

/** 備份日誌列表請求 */
export interface BackupLogListRequest {
  page: number;
  page_size: number;
  action_filter?: string;
  status_filter?: string;
  date_from?: string;
  date_to?: string;
}

/** 備份日誌列表回應 */
export interface BackupLogListResponse {
  logs: BackupLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================================
// 儀表板統計型別 (v13.0 新增)
// ============================================================================

/** 公文月度趨勢項目 */
export interface DocumentTrendItem {
  /** 月份格式 YYYY-MM */
  month: string;
  /** 收文數量 */
  received: number;
  /** 發文數量 */
  sent: number;
}

/** 公文趨勢回應 */
export interface DocumentTrendsResponse {
  trends: DocumentTrendItem[];
}

/** 公文狀態分布項目 */
export interface StatusDistributionItem {
  status: string;
  count: number;
}

/** 公文處理效率回應 */
export interface DocumentEfficiencyResponse {
  status_distribution: StatusDistributionItem[];
  overdue_count: number;
  overdue_rate: number;
  total: number;
}

/** AI 功能使用統計 */
export interface AIFeatureStats {
  count: number;
  cache_hits: number;
  cache_misses: number;
  errors: number;
  total_latency_ms: number;
  avg_latency_ms: number;
}

/** AI 使用統計回應 */
export interface AIStatsResponse {
  total_requests: number;
  by_feature: Record<string, AIFeatureStats>;
  rate_limit_hits: number;
  groq_requests: number;
  ollama_requests: number;
  fallback_requests: number;
  start_time: string;
}

// ============================================================================
// 登入歷史 (LoginHistory) 相關型別
// ============================================================================

/** 登入歷史項目 */
export interface LoginHistoryItem {
  id: number;
  event_type: string;
  ip_address?: string;
  user_agent?: string;
  success: boolean;
  created_at: string;
  details?: Record<string, unknown>;
}

/** 登入歷史回應 */
export interface LoginHistoryResponse {
  items: LoginHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// MFA (雙因素認證) 相關型別
// ============================================================================

/** MFA 設定回應 — /auth/mfa/setup 回傳 */
export interface MFASetupData {
  secret: string;
  qr_uri: string;
  qr_code_base64: string;
  backup_codes: string[];
}

/** MFA 狀態 — /auth/mfa/status 回傳 */
export interface MFAStatus {
  mfa_enabled: boolean;
  backup_codes_remaining: number;
}

/** MFA 驗證頁面的 location state */
export interface MFALocationState {
  mfa_token: string;
  returnUrl?: string;
}

// ============================================================================
// Session 管理 API 型別 (從 sessionApi.ts 遷移)
// ============================================================================

/** Session 資訊 (API 回應格式) */
export interface SessionInfo {
  id: number;
  ip_address: string | null;
  user_agent: string | null;
  device_info: string | null;
  created_at: string;
  last_activity: string | null;
  is_active: boolean;
  is_current: boolean;
}

/** Session 列表回應 */
export interface SessionListResponse {
  sessions: SessionInfo[];
  total: number;
}

/** 撤銷 Session 回應 */
export interface RevokeSessionResponse {
  message: string;
  session_id?: number;
  revoked_count?: number;
}

// ============================================================================
// 儀表板 API 型別 (從 dashboardApi.ts 遷移)
// ============================================================================

import type { OfficialDocument } from './document';

/** 儀表板統計資料 */
export interface DashboardStats {
  total: number;
  approved: number;
  pending: number;
  rejected: number;
}

/**
 * 近期公文 - 基於 OfficialDocument 的簡化版本
 * 僅包含儀表板顯示所需的欄位
 */
export type RecentDocument = Pick<OfficialDocument,
  | 'id'
  | 'doc_number'
  | 'subject'
  | 'doc_type'
  | 'status'
  | 'sender'
  | 'creator'
  | 'created_at'
  | 'receive_date'
>

/** 儀表板完整回應 */
export interface DashboardResponse {
  stats: DashboardStats;
  recent_documents: RecentDocument[];
}

/** 格式化後的近期公文 (用於表格顯示) */
export interface FormattedDocument {
  key: number;
  id: string;
  title: string;
  type: string;
  status: string;
  agency: string;
  creator: string;
  createDate: string;
  deadline: string;
}

// ============================================================================
// 資料庫管理 (Database Management) 相關型別
// ============================================================================

/** 資料庫欄位資訊 */
export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  primaryKey: boolean;
}

/** 資料庫表格資訊 */
export interface TableInfo {
  name: string;
  recordCount: number;
  columns: ColumnInfo[];
  size: string;
  lastModified: string;
}

/** 資料庫整體資訊 */
export interface DatabaseInfo {
  name: string;
  size: string;
  tables: TableInfo[];
  totalRecords: number;
  status: string;
}

/** 自訂查詢結果 */
export interface QueryResult {
  totalRows: number;
  executionTime: number;
  columns: string[];
  rows: unknown[][];
}

/** 資料完整性檢查結果 */
export interface IntegrityResult {
  issues: Array<{ table: string; description: string }>;
  status: string;
  totalIssues: number;
  checkTime: string;
}

// ============================================================================
// 管理儀表板 (Admin Dashboard) 相關型別
// ============================================================================

/** 待審核使用者 */
export interface PendingUser {
  id: number;
  email: string;
  full_name: string;
  auth_provider: string;
  created_at: string;
  role: string;
  status: string;
}

/** 系統警告 */
export interface SystemAlert {
  id: string;
  type: 'warning' | 'error' | 'info';
  title: string;
  description: string;
  timestamp: string;
  action?: () => void;
  actionText?: string;
}

