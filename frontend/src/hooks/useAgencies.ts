/**
 * 機關單位管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */
// @ts-ignore
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  agenciesApi,
  AgencyListParams,
  Agency,
  AgencyCreate,
  AgencyUpdate,
  AgencyWithStats,
  AgencyOption,
  AgencyStatistics,
} from '../api/agenciesApi';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得機關列表
 *
 * @param params 查詢參數
 * @returns React Query 結果
 */
export const useAgencies = (params?: AgencyListParams) => {
  return useQuery({
    queryKey: queryKeys.agencies.list(params || {}),
    queryFn: () => agenciesApi.getAgencies(params),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得單一機關詳情
 *
 * @param agencyId 機關 ID
 * @returns React Query 結果
 */
export const useAgency = (agencyId: number | null | undefined) => {
  return useQuery({
    queryKey: queryKeys.agencies.detail(agencyId ?? 0),
    queryFn: () => agenciesApi.getAgency(agencyId!),
    ...defaultQueryOptions.detail,
    enabled: !!agencyId,
  });
};

/**
 * 取得機關下拉選項
 *
 * @returns React Query 結果
 */
export const useAgencyOptions = () => {
  return useQuery({
    queryKey: queryKeys.agencies.dropdown,
    queryFn: () => agenciesApi.getAgencyOptions(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得機關統計資料
 *
 * @returns React Query 結果
 */
export const useAgencyStatistics = () => {
  return useQuery({
    queryKey: queryKeys.agencies.statistics,
    queryFn: () => agenciesApi.getStatistics(),
    ...defaultQueryOptions.detail,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 建立機關
 *
 * @returns useMutation 結果
 */
export const useCreateAgency = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AgencyCreate) => agenciesApi.createAgency(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agencies.all });
    },
  });
};

/**
 * 更新機關
 *
 * @returns useMutation 結果
 */
export const useUpdateAgency = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agencyId, data }: { agencyId: number; data: AgencyUpdate }) =>
      agenciesApi.updateAgency(agencyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agencies.all });
    },
  });
};

/**
 * 刪除機關
 *
 * @returns useMutation 結果
 */
export const useDeleteAgency = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agencyId: number) => agenciesApi.deleteAgency(agencyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agencies.all });
    },
  });
};

// ============================================================================
// 組合 Hooks
// ============================================================================

/**
 * 機關頁面 hook - 整合列表功能與統計資料
 *
 * @param params 查詢參數
 * @returns 機關列表、統計資料與操作方法
 */
export const useAgenciesPage = (params?: AgencyListParams) => {
  const agenciesQuery = useAgencies(params);
  const statisticsQuery = useAgencyStatistics();
  const createMutation = useCreateAgency();
  const updateMutation = useUpdateAgency();
  const deleteMutation = useDeleteAgency();

  return {
    // 列表相關
    agencies: agenciesQuery.data?.items ?? [],
    pagination: agenciesQuery.data?.pagination,
    isLoading: agenciesQuery.isLoading,
    isError: agenciesQuery.isError,
    error: agenciesQuery.error,
    refetch: agenciesQuery.refetch,

    // 統計資料
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,
    refetchStatistics: statisticsQuery.refetch,

    // 操作方法
    createAgency: createMutation.mutateAsync,
    updateAgency: updateMutation.mutateAsync,
    deleteAgency: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
