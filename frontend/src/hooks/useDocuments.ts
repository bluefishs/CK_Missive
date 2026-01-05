/**
 * 公文管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */
// @ts-ignore
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi, DocumentListParams, DocumentCreate, DocumentUpdate } from '../api/documentsApi';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';

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

  return useMutation({
    mutationFn: (documentId: number) => documentsApi.deleteDocument(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
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
