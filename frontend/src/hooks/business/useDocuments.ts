/**
 * 公文管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi, DocumentListParams, DocumentCreate, DocumentUpdate } from '../../api/documentsApi';
import { queryKeys, defaultQueryOptions } from '../../config/queryConfig';
import { useDispatchCacheInvalidator } from '../taoyuan/useDispatchCacheInvalidator';

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得公文列表
 *
 * @param params 查詢參數
 * @returns React Query 結果
 */
export const useDocuments = (params?: DocumentListParams) => {
  return useQuery({
    queryKey: queryKeys.documents.list((params || {}) as Record<string, unknown>),
    queryFn: () => documentsApi.getDocuments(params),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得單一公文詳情
 *
 * @param documentId 公文 ID
 * @returns React Query 結果
 */
export const useDocument = (documentId: number | null | undefined) => {
  return useQuery({
    queryKey: queryKeys.documents.detail(documentId ?? 0),
    queryFn: () => documentsApi.getDocument(documentId!),
    ...defaultQueryOptions.detail,
    enabled: !!documentId,
  });
};

/**
 * 取得公文統計資料
 *
 * @returns React Query 結果
 */
export const useDocumentStatistics = () => {
  return useQuery({
    queryKey: queryKeys.documents.statistics,
    queryFn: () => documentsApi.getStatistics(),
    ...defaultQueryOptions.statistics,
  });
};

/**
 * 取得年度選項
 *
 * @returns React Query 結果
 */
export const useDocumentYearOptions = () => {
  return useQuery({
    queryKey: queryKeys.documents.years,
    queryFn: () => documentsApi.getYearOptions(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得承攬案件下拉選項
 *
 * @param search 搜尋關鍵字
 * @returns React Query 結果
 */
export const useContractProjectOptions = (search?: string) => {
  return useQuery({
    queryKey: [...queryKeys.documents.all, 'contract-projects', search],
    queryFn: () => documentsApi.getContractProjectOptions(search),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得機關下拉選項
 *
 * @param search 搜尋關鍵字
 * @returns React Query 結果
 */
export const useAgencyDropdownOptions = (search?: string) => {
  return useQuery({
    queryKey: [...queryKeys.documents.all, 'agencies', search],
    queryFn: () => documentsApi.getAgencyOptions(search),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得專案關聯公文
 *
 * @param projectId 專案 ID
 * @param page 頁碼
 * @param limit 每頁筆數
 * @returns React Query 結果
 */
export const useDocumentsByProject = (
  projectId: number | null | undefined,
  page = 1,
  limit = 50
) => {
  return useQuery({
    queryKey: queryKeys.projects.documents(projectId ?? 0),
    queryFn: () => documentsApi.getDocumentsByProject(projectId!, page, limit),
    ...defaultQueryOptions.list,
    enabled: !!projectId,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 建立公文
 *
 * @returns useMutation 結果
 */
export const useCreateDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DocumentCreate) => documentsApi.createDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    },
  });
};

/**
 * 更新公文
 *
 * @returns useMutation 結果
 */
export const useUpdateDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ documentId, data }: { documentId: number; data: DocumentUpdate }) =>
      documentsApi.updateDocument(documentId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.detail(variables.documentId),
      });
    },
  });
};

/**
 * 刪除公文
 *
 * @returns useMutation 結果
 */
export const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  const dispatchCache = useDispatchCacheInvalidator();

  return useMutation({
    mutationFn: (documentId: number) => documentsApi.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
      // 2026-05-18 fix（158 案例同類根因）：後端 cascade 刪
      // taoyuan_dispatch_document_link → 派工列表的 linked_documents 變空，
      // 但前端派工族 query 不在 documents.all 樹下，必須額外清。
      // 2026-07-08 fix（fitness step 8 dispatch cache contract）：改走
      // useDispatchCacheInvalidator SSOT（涵蓋 morning-status/kanban/列表/詳情
      // 全族），取代散落直接 invalidate（L39 queryKey drift 防復發）。
      dispatchCache.invalidateDispatchAggregate();
      // 公文側關聯 query（非派工族，hook 不涵蓋）
      queryClient.invalidateQueries({ queryKey: ['dispatch-documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-dispatch-links'] });
    },
  });
};

// ============================================================================
// 組合 Hooks
// ============================================================================

/**
 * 公文頁面 hook - 整合列表、統計與操作方法
 *
 * @param params 查詢參數
 * @returns 公文列表、統計資料與操作方法
 */
export const useDocumentsPage = (params?: DocumentListParams) => {
  const documentsQuery = useDocuments(params);
  const statisticsQuery = useDocumentStatistics();
  const yearsQuery = useDocumentYearOptions();
  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();
  const deleteMutation = useDeleteDocument();

  return {
    // 列表相關
    documents: documentsQuery.data?.items ?? [],
    pagination: documentsQuery.data?.pagination,
    isLoading: documentsQuery.isLoading,
    isError: documentsQuery.isError,
    error: documentsQuery.error,
    refetch: documentsQuery.refetch,

    // 統計相關
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,
    refetchStatistics: statisticsQuery.refetch,

    // 篩選選項
    availableYears: yearsQuery.data ?? [],
    isOptionsLoading: yearsQuery.isLoading,

    // 操作方法
    createDocument: createMutation.mutateAsync,
    updateDocument: updateMutation.mutateAsync,
    deleteDocument: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
