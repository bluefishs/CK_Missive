export { ErrorBoundary } from './ErrorBoundary';
export { PageLoading } from './PageLoading';
export { NotificationCenter } from './NotificationCenter';
export { AgencyMatchInput } from './AgencyMatchInput';
export type { AgencyMatchInputProps } from './AgencyMatchInput';

// 通用詳情頁元件
export * from './DetailPage';

// 響應式設計元件
export {
  ShowOn,
  HideOn,
  ResponsiveSpace,
  ResponsiveRow,
  ResponsiveCardGrid,
  ResponsiveContent,
} from './ResponsiveContainer';

// 響應式表單行元件
export { ResponsiveFormRow } from './ResponsiveFormRow';

// 響應式表格元件
export { ResponsiveTable } from './ResponsiveTable';
export type { ResponsiveTableProps } from './ResponsiveTable';

// 附件相關共用元件（排除與 DetailPage 衝突的 formatFileSize）
export {
  AttachmentListItem,
  AttachmentList,
  AttachmentUploader,
  isPreviewable,
  getFileExtension,
  getFileIconConfig,
  validateFile,
  createPreviewUrl,
  downloadBlob,
  PREVIEWABLE_MIME_TYPES,
  PREVIEWABLE_EXTENSIONS,
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  // 重新命名以避免衝突
  formatFileSize as formatAttachmentFileSize,
} from './attachment';
export type {
  AttachmentListItemProps,
  AttachmentItem,
  AttachmentListProps,
  AttachmentUploaderProps,
  FileValidationResult,
  FileValidationOptions,
} from './attachment';