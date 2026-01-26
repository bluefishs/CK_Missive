/**
 * Document Components 統一匯出
 *
 * 提供公文管理相關元件的集中導出
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

// ============================================================================
// 主要元件
// ============================================================================

// 公文卡片
export { DocumentCard } from './DocumentCard';
export { default as DocumentCardDefault } from './DocumentCard';

// 公文列表
export { DocumentList } from './DocumentList';

// 公文篩選器
export { DocumentFilter } from './DocumentFilter';

// 公文分頁
export { DocumentPagination } from './DocumentPagination';

// 公文操作面板
export { DocumentOperations, DocumentSendModal } from './DocumentOperations';

// 公文動作按鈕
export { DocumentActions, BatchActions } from './DocumentActions';

// 公文 Tab 切換
export { DocumentTabs } from './DocumentTabs';

// 公文匯入
export { DocumentImport } from './DocumentImport';
export { default as DocumentImportDefault } from './DocumentImport';

// ============================================================================
// 子元件 (operations 子目錄)
// ============================================================================

// 從 operations 子目錄重新匯出
export {
  // 型別
  type CriticalChangeConfirmModalProps,
  type DuplicateFileModalProps,
  type ExistingAttachmentsListProps,
  type FileUploadSectionProps,
  // 元件
  CriticalChangeConfirmModal,
  DuplicateFileModal,
  ExistingAttachmentsList,
  FileUploadSection,
} from './operations';
