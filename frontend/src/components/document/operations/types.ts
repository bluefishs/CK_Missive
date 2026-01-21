/**
 * DocumentOperations 子組件共用型別定義
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import type { UploadFile } from 'antd/es/upload';
import { Document, DocumentAttachment, Project, User, ProjectStaff } from '../../../types';

// ============================================================================
// 關鍵欄位變更相關
// ============================================================================

/** 關鍵欄位定義 */
export const CRITICAL_FIELDS = {
  subject: { label: '主旨', icon: '📝' },
  doc_number: { label: '公文字號', icon: '🔢' },
  sender: { label: '發文單位', icon: '📤' },
  receiver: { label: '受文單位', icon: '📥' },
} as const;

export type CriticalFieldKey = keyof typeof CRITICAL_FIELDS;

/** 關鍵欄位變更項目 */
export interface CriticalChange {
  field: CriticalFieldKey;
  label: string;
  icon: string;
  oldValue: string;
  newValue: string;
}

/** 關鍵欄位變更確認 Modal 狀態 */
export interface CriticalChangeModalState {
  visible: boolean;
  changes: CriticalChange[];
  pendingData: Partial<Document> | null;
}

// ============================================================================
// 重複檔案相關
// ============================================================================

/** 重複檔案 Modal 狀態 */
export interface DuplicateModalState {
  visible: boolean;
  file: File | null;
  existingAttachment: DocumentAttachment | null;
}

// ============================================================================
// 檔案上傳相關
// ============================================================================

/** 檔案設定 */
export interface FileSettings {
  maxFileSizeMB: number;
  allowedExtensions: string[];
}

/** 檔案驗證結果 */
export interface FileValidationResult {
  valid: boolean;
  error?: string;
}

// ============================================================================
// 操作模式
// ============================================================================

export type OperationMode = 'view' | 'edit' | 'create' | 'copy';

// ============================================================================
// Props 定義
// ============================================================================

/** 關鍵欄位變更確認 Modal Props */
export interface CriticalChangeConfirmModalProps {
  visible: boolean;
  changes: CriticalChange[];
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** 重複檔案處理 Modal Props */
export interface DuplicateFileModalProps {
  visible: boolean;
  file: File | null;
  existingAttachment: DocumentAttachment | null;
  onOverwrite: () => void;
  onKeepBoth: () => void;
  onCancel: () => void;
}

/** 現有附件列表 Props */
export interface ExistingAttachmentsListProps {
  attachments: DocumentAttachment[];
  loading: boolean;
  readOnly: boolean;
  onDownload: (id: number, filename: string) => Promise<void>;
  onPreview: (id: number, filename: string) => void;
  onDelete: (id: number) => Promise<void>;
}

/** 檔案上傳區塊 Props */
export interface FileUploadSectionProps {
  fileList: UploadFile[];
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  maxFileSizeMB: number;
  allowedExtensions: string[];
  readOnly: boolean;
  onFileListChange: (fileList: UploadFile[]) => void;
  onRemove: (file: UploadFile) => void;
  onClearErrors?: () => void;
  validateFile: (file: File) => FileValidationResult;
  /** 檢查重複檔案的回調，回傳 true 表示已處理（顯示確認對話框），false 表示可繼續上傳 */
  onCheckDuplicate?: (file: File) => boolean;
}

/** 專案與人員 Tab Props */
export interface TabProjectAndStaffProps {
  cases: Project[];
  users: User[];
  casesLoading: boolean;
  usersLoading: boolean;
  selectedProjectId: number | null;
  projectStaffMap: Record<number, ProjectStaff[]>;
  staffLoading: boolean;
  readOnly: boolean;
  onProjectChange: (projectId: number | null) => void;
}
