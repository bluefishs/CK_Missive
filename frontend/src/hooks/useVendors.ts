/**
 * 廠商管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */
// @ts-ignore
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { vendorsApi, VendorListParams, VendorStatistics } from '../api/vendorsApi';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';
import type { Vendor, VendorCreate, VendorUpdate, VendorOption } from '../types/api';

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得廠商列表
 *
 * @param params 查詢參數
 * @returns React Query 結果
 */
export const useVendors = (params?: VendorListParams) => {
  return useQuery({
    queryKey: queryKeys.vendors.list(params || {}),
    queryFn: () => vendorsApi.getVendors(params),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得單一廠商詳情
 *
 * @param vendorId 廠商 ID
 * @returns React Query 結果
 */
export const useVendor = (vendorId: number | null | undefined) => {
  return useQuery({
    queryKey: queryKeys.vendors.detail(vendorId ?? 0),
    queryFn: () => vendorsApi.getVendor(vendorId!),
    ...defaultQueryOptions.detail,
    enabled: !!vendorId,
  });
};

/**
 * 取得廠商下拉選項
 *
 * @returns React Query 結果
 */
export const useVendorOptions = () => {
  return useQuery({
    queryKey: queryKeys.vendors.dropdown,
    queryFn: () => vendorsApi.getVendorOptions(),
    ...defaultQueryOptions.dropdown,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 建立廠商
 *
 * @returns useMutation 結果
 */
export const useCreateVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: VendorCreate) => vendorsApi.createVendor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.vendors.all });
    },
  });
};

/**
 * 更新廠商
 *
 * @returns useMutation 結果
 */
export const useUpdateVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ vendorId, data }: { vendorId: number; data: VendorUpdate }) =>
      vendorsApi.updateVendor(vendorId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.vendors.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.vendors.detail(variables.vendorId),
      });
    },
  });
};

/**
 * 刪除廠商
 *
 * @returns useMutation 結果
 */
export const useDeleteVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vendorId: number) => vendorsApi.deleteVendor(vendorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.vendors.all });
    },
  });
};

/**
 * 批次刪除廠商
 *
 * @returns useMutation 結果
 */
export const useBatchDeleteVendors = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vendorIds: number[]) => vendorsApi.batchDelete(vendorIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.vendors.all });
    },
  });
};

// ============================================================================
// 組合 Hooks
// ============================================================================

/**
 * 廠商頁面 hook - 整合列表功能
 *
 * @param params 查詢參數
 * @returns 廠商列表與操作方法
 */
export const useVendorsPage = (params?: VendorListParams) => {
  const vendorsQuery = useVendors(params);
  const createMutation = useCreateVendor();
  const updateMutation = useUpdateVendor();
  const deleteMutation = useDeleteVendor();

  return {
    // 列表相關
    vendors: vendorsQuery.data?.items ?? [],
    pagination: vendorsQuery.data?.pagination,
    isLoading: vendorsQuery.isLoading,
    isError: vendorsQuery.isError,
    error: vendorsQuery.error,
    refetch: vendorsQuery.refetch,

    // 操作方法
    createVendor: createMutation.mutateAsync,
    updateVendor: updateMutation.mutateAsync,
    deleteVendor: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
