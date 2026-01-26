/**
 * ContractCaseDetailPage Tab 元件型別定義
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import type { FormInstance } from 'antd';
import type dayjs from 'dayjs';
import type { Project, OfficialDocument, ProjectVendorAssociation } from '../../../types/api';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';

// ============================================================================
// 專案資料型別
// ============================================================================

/**
 * 專案資料型別 - 擴展 Project 以支援中文狀態值
 * 注意：後端回傳中文狀態，但 types/api.ts 定義為英文 enum
 */
export interface ProjectData extends Omit<Project, 'status'> {
  status?: string;  // 中文狀態值：待執行/執行中/已結案/暫停
}

/** 關聯文件型別 - 使用 OfficialDocument 的子集 */
export type RelatedDocument = Pick<OfficialDocument,
  'id' | 'doc_number' | 'doc_type' | 'subject' | 'doc_date' |
  'sender' | 'receiver' | 'category' | 'delivery_method' | 'has_attachment'
>;

/**
 * 附件型別 - 此頁面專用的附件呈現結構
 * 包含所屬公文資訊，用於專案附件彙整顯示
 */
export interface Attachment {
  id: number;
  document_id: number;
  filename: string;
  original_filename?: string;
  file_size: number;
  file_type: string;
  content_type?: string;
  uploaded_at?: string;
  uploaded_by: string;  // 上傳者名稱（顯示用）
  document_number: string;
  document_subject: string;
}

/** 按公文分組的附件 - 此頁面專用 */
export interface LocalGroupedAttachment {
  document_id: number;
  document_number: string;
  document_subject: string;
  file_count: number;
  total_size: number;
  last_updated: string;
  attachments: Attachment[];
}

/** 協力廠商關聯型別 - 使用 ProjectVendorAssociation */
export type VendorAssociation = ProjectVendorAssociation;

/** 專案同仁型別 - 在此頁面的呈現結構 */
export interface Staff {
  id: number;
  user_id: number;
  name: string;
  role: string;
  department?: string;
  phone?: string;
  email?: string;
  join_date?: string;
  status: string;
}

// ============================================================================
// 表單值型別定義
// ============================================================================

/** 新增同仁表單值 */
export interface StaffFormValues {
  user_id: number;
  role: string;
}

/** 新增廠商表單值 */
export interface VendorFormValues {
  vendor_id: number;
  role: string;
  contract_amount?: number;
  start_date?: dayjs.Dayjs;
  end_date?: dayjs.Dayjs;
}

/** 案件資訊表單值 */
export interface CaseInfoFormValues {
  project_name: string;
  year: number;
  client_agency?: string;
  contract_doc_number?: string;
  project_code?: string;
  category?: string;
  case_nature?: string;
  contract_amount?: number;
  winning_amount?: number;
  date_range?: [dayjs.Dayjs, dayjs.Dayjs];
  status?: string;
  progress?: number;
  project_path?: string;
  notes?: string;
}

/** 機關承辦表單值 */
export interface AgencyContactFormValues {
  contact_name: string;
  position?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  is_primary?: boolean;
  notes?: string;
}

/** Pydantic 驗證錯誤項目 */
export interface PydanticValidationError {
  msg?: string;
  message?: string;
  loc?: string[];
  type?: string;
}

/** API 錯誤回應 */
export interface ApiErrorResponse {
  detail?: string | PydanticValidationError[];
}

// ============================================================================
// Tab Props 型別定義
// ============================================================================

/** 案件資訊 Tab Props */
export interface CaseInfoTabProps {
  data: ProjectData;
  isEditing: boolean;
  setIsEditing: (editing: boolean) => void;
  form: FormInstance<CaseInfoFormValues>;
  onSave: (values: CaseInfoFormValues) => Promise<void>;
  calculateProgress: () => number;
}

/** 機關承辦 Tab Props */
export interface AgencyContactTabProps {
  agencyContacts: ProjectAgencyContact[];
  modalVisible: boolean;
  setModalVisible: (visible: boolean) => void;
  editingId: number | null;
  setEditingId: (id: number | null) => void;
  form: FormInstance<AgencyContactFormValues>;
  onSubmit: (values: AgencyContactFormValues) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

/** 承辦同仁 Tab Props */
export interface StaffTabProps {
  staffList: Staff[];
  editingStaffId: number | null;
  setEditingStaffId: (id: number | null) => void;
  onRoleChange: (staffId: number, newRole: string) => Promise<void>;
  onDelete: (staffId: number) => Promise<void>;
  modalVisible: boolean;
  setModalVisible: (visible: boolean) => void;
  form: FormInstance<StaffFormValues>;
  onAddStaff: (values: StaffFormValues) => Promise<void>;
  userOptions: { id: number; name: string; email: string }[];
  loadUserOptions: () => Promise<void>;
}

/** 協力廠商 Tab Props */
export interface VendorsTabProps {
  vendorList: VendorAssociation[];
  editingVendorId: number | null;
  setEditingVendorId: (id: number | null) => void;
  onRoleChange: (vendorId: number, newRole: string) => Promise<void>;
  onDelete: (vendorId: number) => Promise<void>;
  modalVisible: boolean;
  setModalVisible: (visible: boolean) => void;
  form: FormInstance<VendorFormValues>;
  onAddVendor: (values: VendorFormValues) => Promise<void>;
  vendorOptions: { id: number; name: string; code: string }[];
  loadVendorOptions: () => Promise<void>;
}

/** 附件紀錄 Tab Props */
export interface AttachmentsTabProps {
  attachments: Attachment[];
  groupedAttachments: LocalGroupedAttachment[];
  loading: boolean;
  onRefresh: () => void;
  onDownload: (attachmentId: number, filename: string) => Promise<void>;
  onPreview: (attachmentId: number, filename: string) => Promise<void>;
  onDownloadAll: (group: LocalGroupedAttachment) => Promise<void>;
  relatedDocsCount: number;
}

/** 關聯公文 Tab Props */
export interface RelatedDocumentsTabProps {
  relatedDocs: RelatedDocument[];
  onRefresh: () => void;
}
