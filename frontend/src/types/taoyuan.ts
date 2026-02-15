/**
 * 桃園查估派工管理系統 (TaoyuanDispatch) 相關型別
 *
 * 轄管工程、派工單、派工附件、契金管控、
 * 公文-派工-工程三角關聯、總控表、Excel 匯入
 *
 * @extracted-from api.ts (lines 836-1511)
 * @version 1.0.0
 * @created 2026-02-11
 */

import type { PaginationMeta } from './api';

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

// ============================================================================
// 關聯類型定義 (公文-派工-工程三角關係)
// ============================================================================

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

// ============================================================================
// 轄管工程 (TaoyuanProject) 相關型別
// ============================================================================

/** 工程關聯的派工單簡要資訊 */
export interface ProjectDispatchLinkItem {
  link_id: number;
  dispatch_order_id: number;
  dispatch_no?: string;
  work_type?: string;
}

/** 工程關聯的公文簡要資訊 */
export interface ProjectDocumentLinkItem {
  link_id: number;
  document_id: number;
  doc_number?: string;
  link_type: LinkType;
}

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

  // 進度追蹤欄位
  land_agreement_status?: string;
  land_expropriation_status?: string;
  building_survey_status?: string;
  actual_entry_date?: string;
  acceptance_status?: string;

  // 關聯資訊 (從 API 返回)
  linked_dispatches?: ProjectDispatchLinkItem[];
  linked_documents?: ProjectDocumentLinkItem[];

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
  start_coordinate?: string;
  end_point?: string;
  end_coordinate?: string;
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

// ============================================================================
// 派工單 (DispatchOrder) 相關型別
// ============================================================================

/** 派工單關聯的公文資訊 */
export interface DispatchDocumentLink extends BaseLink {
  link_type: LinkType;
  dispatch_order_id: number;
  document_id: number;
  doc_number?: string;
  subject?: string;
  doc_date?: string;
}

/** 作業類別正規化項目 */
export interface DispatchWorkTypeItem {
  id: number;
  work_type: string;
  sort_order: number;
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
  /** 附件數量 */
  attachment_count?: number;
  /** 關聯工程（包含 link_id 和 project_id 用於解除關聯） */
  linked_projects?: (TaoyuanProject & { link_id: number; project_id: number })[];
  /** 關聯公文（使用統一的關聯格式） */
  linked_documents?: DispatchDocumentLink[];
  /** 作業類別正規化項目 */
  work_type_items?: DispatchWorkTypeItem[];
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

// =============================================================================
// 派工單附件 (DispatchAttachment) 相關型別
// =============================================================================

/** 派工單附件介面 */
export interface DispatchAttachment {
  id: number;
  dispatch_order_id: number;
  file_name: string;
  file_path?: string;
  file_size: number;
  mime_type?: string;
  storage_type?: 'local' | 'network' | 'nas' | 's3';
  original_name?: string;
  checksum?: string;
  uploaded_by?: number;
  created_at?: string;
  updated_at?: string;
  // 相容欄位
  filename?: string;
  original_filename?: string;
  content_type?: string;
}

/** 派工單附件列表回應 */
export interface DispatchAttachmentListResponse {
  success: boolean;
  dispatch_order_id: number;
  total: number;
  attachments: DispatchAttachment[];
}

/** 派工單附件上傳結果 */
export interface DispatchAttachmentUploadResult {
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

/** 派工單附件刪除結果 */
export interface DispatchAttachmentDeleteResult {
  success: boolean;
  message: string;
}

/** 派工單附件驗證結果 */
export interface DispatchAttachmentVerifyResult {
  success: boolean;
  message: string;
  valid: boolean;
  expected_checksum?: string;
  actual_checksum?: string;
}

// ============================================================================
// 統計資料型別
// ============================================================================

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

// ============================================================================
// 契金管控 (ContractPayment) 相關型別
// ============================================================================

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
  work_01_date?: string | null;
  work_01_amount?: number | null;
  work_02_date?: string | null;
  work_02_amount?: number | null;
  work_03_date?: string | null;
  work_03_amount?: number | null;
  work_04_date?: string | null;
  work_04_amount?: number | null;
  work_05_date?: string | null;
  work_05_amount?: number | null;
  work_06_date?: string | null;
  work_06_amount?: number | null;
  work_07_date?: string | null;
  work_07_amount?: number | null;
  current_amount?: number | null;
  cumulative_amount?: number | null;
  remaining_amount?: number | null;
  acceptance_date?: string | null;
}

/** 契金管控更新請求 */
export type ContractPaymentUpdate = Partial<Omit<ContractPaymentCreate, 'dispatch_order_id'>>;

/** 契金管控列表回應 */
export interface ContractPaymentListResponse {
  success: boolean;
  items: ContractPayment[];
  pagination: PaginationMeta;
}

/** 契金管控展示項目（派工單為主） */
export interface PaymentControlItem {
  dispatch_order_id: number;
  dispatch_no: string;
  project_name?: string;
  work_type?: string;
  sub_case_name?: string;
  case_handler?: string;
  survey_unit?: string;
  cloud_folder?: string;
  project_folder?: string;
  deadline?: string;

  /** 派工日期（取第一筆機關來函日期） */
  dispatch_date?: string;

  /** 公文歷程 */
  agency_doc_history?: string;
  company_doc_history?: string;

  /** 契金紀錄 ID */
  payment_id?: number;

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
  remark?: string;
}

/** 契金管控展示回應 */
export interface PaymentControlResponse {
  success: boolean;
  items: PaymentControlItem[];
  total_budget?: number;
  total_dispatched?: number;
  total_remaining?: number;
  pagination: PaginationMeta;
}

// ============================================================================
// 關聯完整型別定義
// ============================================================================

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

// ============================================================================
// 總控表相關型別
// ============================================================================

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

// ============================================================================
// Excel 匯入型別
// ============================================================================

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
// 作業歷程 (WorkRecord) 相關型別
// ============================================================================

/** 里程碑類型 */
export type MilestoneType =
  | 'dispatch'
  | 'survey'
  | 'site_inspection'
  | 'submit_result'
  | 'revision'
  | 'review_meeting'
  | 'negotiation'
  | 'final_approval'
  | 'boundary_survey'
  | 'closed'
  | 'other';

/** 作業紀錄狀態 */
export type WorkRecordStatus = 'pending' | 'in_progress' | 'completed' | 'overdue' | 'on_hold';

/** 作業類別 (新格式，鏈式時間軸) */
export type WorkCategory =
  | 'dispatch_notice'
  | 'work_result'
  | 'meeting_notice'
  | 'meeting_record'
  | 'survey_notice'
  | 'survey_record'
  | 'other';

/** 關聯公文摘要 */
export interface DocBrief {
  id: number;
  doc_number?: string;
  doc_date?: string;
  subject?: string;
}

/** 作業歷程紀錄 */
export interface WorkRecord {
  id: number;
  dispatch_order_id: number;
  taoyuan_project_id?: number;
  incoming_doc_id?: number;
  outgoing_doc_id?: number;
  // v2 鏈式欄位
  document_id?: number;
  parent_record_id?: number;
  work_category?: WorkCategory;
  batch_no?: number;
  batch_label?: string;
  milestone_type: MilestoneType;
  description?: string;
  submission_type?: string;
  record_date: string;
  deadline_date?: string;
  completed_date?: string;
  status: WorkRecordStatus;
  sort_order: number;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  incoming_doc?: DocBrief;
  outgoing_doc?: DocBrief;
  document?: DocBrief;
  dispatch_subject?: string;
}

/** 作業歷程簡要（防止鏈式序列化遞迴） */
export interface WorkRecordBrief {
  id: number;
  doc_number?: string;
  work_category?: string;
  record_date?: string;
  status?: string;
}

/** 作業歷程建立請求 */
export interface WorkRecordCreate {
  dispatch_order_id: number;
  taoyuan_project_id?: number;
  incoming_doc_id?: number;
  outgoing_doc_id?: number;
  // v2 鏈式欄位
  document_id?: number;
  parent_record_id?: number;
  work_category?: WorkCategory;
  batch_no?: number;
  batch_label?: string;
  milestone_type?: MilestoneType;
  description?: string;
  submission_type?: string;
  record_date?: string;
  deadline_date?: string;
  completed_date?: string;
  status?: WorkRecordStatus;
  sort_order?: number;
  notes?: string;
}

/** 作業歷程更新請求 */
export type WorkRecordUpdate = Partial<Omit<WorkRecordCreate, 'dispatch_order_id'>>;

/** 作業歷程列表回應 */
export interface WorkRecordListResponse {
  items: WorkRecord[];
  total: number;
  page: number;
  page_size: number;
}

/** 工程歷程總覽 */
export interface ProjectWorkflowSummary {
  project_id: number;
  sequence_no?: number;
  project_name: string;
  sub_case_name?: string;
  batch_close_no?: number;
  case_handler?: string;
  total_incoming_docs: number;
  total_outgoing_docs: number;
  milestones_completed: number;
  current_stage?: string;
  work_records: WorkRecord[];
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
