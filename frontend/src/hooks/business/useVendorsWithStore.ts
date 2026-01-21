/**
 * 廠商管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { useEffect, useCallback } from 'react';
import { useVendorsStore, VendorFilter } from '../../store';
import {
  useVendors,
  useVendor,
  useCreateVendor,
  useUpdateVendor,
  useDeleteVendor,
} from './useVendors';
import type { Vendor, VendorCreate, VendorUpdate } from '../../types/api';
import type { VendorListParams } from '../../api/vendorsApi';

/**
 * 廠商列表整合 Hook
 *
 * 自動同步 React Query 資料到 Zustand Store
 */
export const useVendorsWithStore = () => {
  const store = useVendorsStore();

  // 將 Store 的 filters 轉換為 API 參數
  const apiParams: VendorListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    business_type: store.filters.business_type,
  };

  // React Query hooks
  const vendorsQuery = useVendors(apiParams);
  const createMutation = useCreateVendor();
  const updateMutation = useUpdateVendor();
  const deleteMutation = useDeleteVendor();

  // 同步 React Query 資料到 Store
  useEffect(() => {
    if (vendorsQuery.data?.items) {
      store.setVendors(vendorsQuery.data.items);
    }
    if (vendorsQuery.data?.pagination) {
      store.setPagination({
        total: vendorsQuery.data.pagination.total,
        totalPages: vendorsQuery.data.pagination.total_pages,
      });
    }
  }, [vendorsQuery.data]);

  // 同步載入狀態
  useEffect(() => {
    store.setLoading(vendorsQuery.isLoading);
  }, [vendorsQuery.isLoading]);

  // 操作方法
  const handleCreate = useCallback(
    async (data: VendorCreate) => {
      const result = await createMutation.mutateAsync(data);
      if (result) {
        store.addVendor(result);
      }
      return result;
    },
    [createMutation, store]
  );

  const handleUpdate = useCallback(
    async (vendorId: number, data: VendorUpdate) => {
      const result = await updateMutation.mutateAsync({ vendorId, data });
      if (result) {
        store.updateVendor(vendorId, result);
      }
      return result;
    },
    [updateMutation, store]
  );

  const handleDelete = useCallback(
    async (vendorId: number) => {
      await deleteMutation.mutateAsync(vendorId);
      store.removeVendor(vendorId);
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
    (filters: Partial<VendorFilter>) => {
      store.setFilters(filters);
    },
    [store]
  );

  const handleSelect = useCallback(
    (vendor: Vendor | null) => {
      store.setSelectedVendor(vendor);
    },
    [store]
  );

  return {
    // Store 狀態 (UI State)
    vendors: store.vendors,
    selectedVendor: store.selectedVendor,
    filters: store.filters,
    pagination: store.pagination,
    loading: store.loading,

    // React Query 狀態 (Server State)
    isLoading: vendorsQuery.isLoading,
    isError: vendorsQuery.isError,
    error: vendorsQuery.error,
    isFetching: vendorsQuery.isFetching,

    // 操作方法
    createVendor: handleCreate,
    updateVendor: handleUpdate,
    deleteVendor: handleDelete,

    // UI 操作
    setPage: handlePageChange,
    setFilters: handleFilterChange,
    selectVendor: handleSelect,
    resetFilters: store.resetFilters,
    refetch: vendorsQuery.refetch,

    // Mutation 狀態
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

/**
 * 單一廠商詳情 Hook（整合 Store）
 */
export const useVendorDetailWithStore = (vendorId: number | null | undefined) => {
  const store = useVendorsStore();
  const vendorQuery = useVendor(vendorId);

  // 同步到 Store
  useEffect(() => {
    if (vendorQuery.data) {
      store.setSelectedVendor(vendorQuery.data);
    }
  }, [vendorQuery.data]);

  return {
    vendor: vendorQuery.data || store.selectedVendor,
    isLoading: vendorQuery.isLoading,
    isError: vendorQuery.isError,
    error: vendorQuery.error,
    refetch: vendorQuery.refetch,
  };
};
