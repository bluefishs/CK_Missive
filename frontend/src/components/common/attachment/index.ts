/**
 * 附件相關共用元件統一匯出
 *
 * @version 1.0.0
 * @date 2026-01-27
 */

// 元件
export { AttachmentListItem } from './AttachmentListItem';
export type { AttachmentListItemProps, AttachmentItem } from './AttachmentListItem';

export { AttachmentList } from './AttachmentList';
export type { AttachmentListProps } from './AttachmentList';

export { AttachmentUploader } from './AttachmentUploader';
export type { AttachmentUploaderProps } from './AttachmentUploader';

// 工具函數
export {
  isPreviewable,
  formatFileSize,
  getFileExtension,
  getFileIconConfig,
  validateFile,
  createPreviewUrl,
  downloadBlob,
  // 常數
  PREVIEWABLE_MIME_TYPES,
  PREVIEWABLE_EXTENSIONS,
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
} from './attachmentUtils';

export type { FileValidationResult, FileValidationOptions } from './attachmentUtils';
