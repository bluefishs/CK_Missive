/**
 * 文件管理 Store
 *
 * 使用通用 Store Factory 建立，減少重複程式碼。
 *
 * @version 2.0.0
 * @date 2026-01-21
 */

import type { OfficialDocument as Document, DocumentFilter } from '../types/api';
import { createEntityStore, type EntityState } from './createEntityStore';

// ============================================================================
// 型別定義
// ============================================================================

/** 文件 Store 狀態型別 */
export type DocumentsState = EntityState<Document, DocumentFilter>;

// ============================================================================
// Store 建立
// ============================================================================

const initialFilters: DocumentFilter = {
  search: '',
};

/**
 * 文件 Store
 *
 * @example
 * ```typescript
 * const {
 *   items: documents,
 *   selectedItem: selectedDocument,
 *   filters,
 *   pagination,
 *   setItems,
 *   addItem,
 *   updateItem,
 *   removeItem,
 *   setFilters,
 *   resetFilters,
 * } = useDocumentsStore();
 * ```
 */
export const useDocumentsStore = createEntityStore<Document, DocumentFilter>({
  name: 'documents-store',
  initialFilters,
});

// ============================================================================
// 相容性別名（向後相容舊 API）
// ============================================================================

/**
 * 文件 Store 相容性包裝
 * 提供舊版 API 的別名，方便漸進式遷移
 *
 * 注意：舊版 API 的 updateDocument/removeDocument 接受 string id，
 * 這裡提供轉換以維持向後相容。
 */
export function useDocumentsStoreCompat() {
  const store = useDocumentsStore();
  return {
    // 舊版別名
    documents: store.items,
    selectedDocument: store.selectedItem,
    setDocuments: store.setItems,
    setSelectedDocument: store.setSelectedItem,
    addDocument: store.addItem,
    // 舊版接受 string id，轉換為 number
    updateDocument: (id: string | number, updates: Partial<Document>) =>
      store.updateItem(typeof id === 'string' ? Number(id) : id, updates),
    removeDocument: (id: string | number) =>
      store.removeItem(typeof id === 'string' ? Number(id) : id),
    // 新版 API
    ...store,
  };
}
