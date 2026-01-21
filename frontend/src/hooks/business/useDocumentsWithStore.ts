/**
 * 公文管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 1.0.0
 * @date 2026-01-20
 */

import { useEffect, useCallback } from 'react';
import { useDocumentsStore } from '../../store/documents';
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
import type { OfficialDocument as Document, DocumentFilter } from '../../types/api';
import type { DocumentListParams, DocumentCreate, DocumentUpdate } from '../../api/documentsApi';

/**
 * 公文列表整合 Hook
 *
 * 自動同步 React Query 資料到 Zustand Store，提供統一的狀態管理介面
 */
export const useDocumentsWithStore = () => {
  const store = useDocumentsStore();

  // 將 Store 的 filters 轉換為 API 參數
  const apiParams: DocumentListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    doc_type: store.filters.doc_type,
    status: store.filters.status,
    year: store.filters.year,
    category: store.filters.category,
  };

  // React Query hooks
  const documentsQuery = useDocuments(apiParams);
  const statisticsQuery = useDocumentStatistics();
  const yearsQuery = useDocumentYearOptions();
  const projectsQuery = useContractProjectOptions();
  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();
  const deleteMutation = useDeleteDocument();

  // 同步 React Query 資料到 Store
  useEffect(() => {
    if (documentsQuery.data?.items) {
      store.setDocuments(documentsQuery.data.items);
    }
    if (documentsQuery.data?.pagination) {
      store.setPagination({
        total: documentsQuery.data.pagination.total,
        totalPages: documentsQuery.data.pagination.total_pages,
      });
    }
  }, [documentsQuery.data]);

  // 操作方法
  const handleCreate = useCallback(
    async (data: DocumentCreate) => {
      const result = await createMutation.mutateAsync(data);
      if (result) {
        store.addDocument(result);
      }
      return result;
    },
    [createMutation, store]
  );

  const handleUpdate = useCallback(
    async (documentId: number, data: DocumentUpdate) => {
      const result = await updateMutation.mutateAsync({ documentId, data });
      if (result) {
        store.updateDocument(String(documentId), result);
      }
      return result;
    },
    [updateMutation, store]
  );

  const handleDelete = useCallback(
    async (documentId: number) => {
      await deleteMutation.mutateAsync(documentId);
      store.removeDocument(String(documentId));
    },
    [deleteMutation, store]
  );

  const handlePageChange = useCallback(
    (page: number, pageSize?: number) => {
      store.setPagination({ page, limit: pageSize || store.pagination.limit });
    },
    [store]
  );

  const handleFilterChange = useCallback(
    (filters: Partial<DocumentFilter>) => {
      store.setFilters(filters);
    },
    [store]
  );

  const handleSelect = useCallback(
    (document: Document | null) => {
      store.setSelectedDocument(document);
    },
    [store]
  );

  const handleResetFilters = useCallback(() => {
    store.resetFilters();
  }, [store]);

  return {
    // Store 狀態 (UI State)
    documents: store.documents,
    selectedDocument: store.selectedDocument,
    filters: store.filters,
    pagination: store.pagination,

    // React Query 狀態 (Server State)
    isLoading: documentsQuery.isLoading,
    isError: documentsQuery.isError,
    error: documentsQuery.error,
    isFetching: documentsQuery.isFetching,

    // 統計資料
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,

    // 篩選選項
    availableYears: yearsQuery.data ?? [],
    availableProjects: projectsQuery.data ?? [],

    // Mutation 狀態
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,

    // 操作方法
    createDocument: handleCreate,
    updateDocument: handleUpdate,
    deleteDocument: handleDelete,

    // UI 操作
    setPage: handlePageChange,
    setFilters: handleFilterChange,
    selectDocument: handleSelect,
    resetFilters: handleResetFilters,

    // 資料重新整理
    refetch: documentsQuery.refetch,
  };
};

/**
 * 單一公文詳情整合 Hook
 */
export const useDocumentWithStore = (documentId: number | null | undefined) => {
  const store = useDocumentsStore();
  const documentQuery = useDocument(documentId);

  // 同步到 Store
  useEffect(() => {
    if (documentQuery.data) {
      store.setSelectedDocument(documentQuery.data);
    }
  }, [documentQuery.data]);

  return {
    document: documentQuery.data,
    isLoading: documentQuery.isLoading,
    isError: documentQuery.isError,
    error: documentQuery.error,
    refetch: documentQuery.refetch,
  };
};

export default useDocumentsWithStore;
