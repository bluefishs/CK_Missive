/**
 * DocumentOperations 子組件匯出
 *
 * @version 2.0.0
 * @date 2026-01-26
 *
 * 重構摘要：
 * - useDocumentOperations: 狀態管理與附件操作邏輯
 * - useDocumentForm: 表單初始化與提交邏輯
 * - DocumentOperationsTabs: Tab 子元件 (BasicInfoTab, DateStatusTab, etc.)
 * - DocumentSendModal: 公文發送對話框
 */

// 型別定義
export * from './types';

// 工具函數
export {
  // 常數
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  MIN_PROGRESS_DISPLAY_MS,
  // 關鍵欄位檢測
  detectCriticalChanges,
  // 檔案驗證
  createFileValidator,
  checkDuplicateFile,
  // Assignee 處理
  parseAssignee,
  formatAssignee,
  // 操作文字
  getOperationText,
  getModalTitleText,
  // 日期處理
  formatDateToString,
  // 檔案大小
  formatFileSize,
  // 錯誤處理
  getErrorMessage,
} from './documentOperationsUtils';

// Hooks
export { useDocumentOperations } from './useDocumentOperations';
export type { UseDocumentOperationsReturn, UseDocumentOperationsProps } from './useDocumentOperations';
export { useDocumentForm } from './useDocumentForm';
export type { UseDocumentFormReturn, UseDocumentFormProps, DocumentFormValues } from './useDocumentForm';

// Tab 子組件
export {
  BasicInfoTab,
  DateStatusTab,
  ProjectStaffTab,
  AttachmentTab,
  SystemInfoTab,
} from './DocumentOperationsTabs';
export type {
  BasicInfoTabProps,
  ProjectStaffTabProps,
  AttachmentTabProps,
  SystemInfoTabProps,
} from './DocumentOperationsTabs';

// Modal 組件
export { CriticalChangeConfirmModal } from './CriticalChangeConfirmModal';
export { DuplicateFileModal } from './DuplicateFileModal';
export { DocumentSendModal } from './DocumentSendModal';
export type { DocumentSendModalProps } from './DocumentSendModal';

// 其他組件
export { ExistingAttachmentsList } from './ExistingAttachmentsList';
export { FileUploadSection } from './FileUploadSection';

// 預設匯出
export { default as CriticalChangeConfirmModalDefault } from './CriticalChangeConfirmModal';
export { default as DuplicateFileModalDefault } from './DuplicateFileModal';
export { default as ExistingAttachmentsListDefault } from './ExistingAttachmentsList';
export { default as FileUploadSectionDefault } from './FileUploadSection';
