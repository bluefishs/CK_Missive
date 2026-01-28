/**
 * 公文管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 2.0.0 - 使用 createEntityHookWithStore 工廠
 * @date 2026-01-28
 */

import { useDocumentsStoreCompat } from '../../store/documents';
import {
  useDocuments,
  useDocument,
  useDocumentStatistics,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useDocumentYearOptions,
  useContractProjectOptions,
} from './useDocuments';
import type { OfficialDocument as Document } from '../../types/api';
import type { DocumentListParams } from '../../api/documentsApi';
import { useEntityWithStoreCore, useEntityDetailCore } from './createEntityHookWithStore';

export const useDocumentsWithStore = () => {
  const store = useDocumentsStoreCompat();

  const apiParams: DocumentListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    doc_type: store.filters.doc_type,
    status: store.filters.status,
    year: store.filters.year,
    category: store.filters.category,
  };

  const documentsQuery = useDocuments(apiParams);
  const statisticsQuery = useDocumentStatistics();
  const yearsQuery = useDocumentYearOptions();
  const projectsQuery = useContractProjectOptions();
  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();
  const deleteMutation = useDeleteDocument();

  const core = useEntityWithStoreCore(store, documentsQuery, {
    create: createMutation,
    update: updateMutation,
    delete: deleteMutation,
  }, {
    syncLoading: false,
    buildUpdatePayload: (documentId, data) => ({ documentId, data }),
  });

  return {
    documents: core.items,
    selectedDocument: core.selectedItem,
    filters: core.filters,
    pagination: core.pagination,
    isLoading: core.isLoading,
    isError: core.isError,
    error: core.error,
    isFetching: core.isFetching,
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,
    availableYears: yearsQuery.data ?? [],
    availableProjects: projectsQuery.data ?? [],
    isCreating: core.isCreating,
    isUpdating: core.isUpdating,
    isDeleting: core.isDeleting,
    createDocument: core.handleCreate,
    updateDocument: core.handleUpdate,
    deleteDocument: core.handleDelete,
    setPage: core.setPage,
    setFilters: core.setFilters,
    selectDocument: core.selectItem as (document: Document | null) => void,
    resetFilters: core.resetFilters,
    refetch: core.refetch,
  };
};

export const useDocumentWithStore = (documentId: number | null | undefined) => {
  const store = useDocumentsStoreCompat();
  const documentQuery = useDocument(documentId);
  const detail = useEntityDetailCore(store, documentQuery);

  return {
    document: detail.data,
    isLoading: detail.isLoading,
    isError: detail.isError,
    error: detail.error,
    refetch: detail.refetch,
  };
};

export default useDocumentsWithStore;
