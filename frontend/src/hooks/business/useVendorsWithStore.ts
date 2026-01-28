/**
 * 廠商管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 2.0.0 - 使用 createEntityHookWithStore 工廠
 * @date 2026-01-28
 */

import { useVendorsStoreCompat } from '../../store/vendors';
import {
  useVendors,
  useVendor,
  useCreateVendor,
  useUpdateVendor,
  useDeleteVendor,
} from './useVendors';
import type { Vendor } from '../../types/api';
import type { VendorListParams } from '../../api/vendorsApi';
import { useEntityWithStoreCore, useEntityDetailCore } from './createEntityHookWithStore';

export const useVendorsWithStore = () => {
  const store = useVendorsStoreCompat();

  const apiParams: VendorListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    business_type: store.filters.business_type,
  };

  const vendorsQuery = useVendors(apiParams);
  const createMutation = useCreateVendor();
  const updateMutation = useUpdateVendor();
  const deleteMutation = useDeleteVendor();

  const core = useEntityWithStoreCore(store, vendorsQuery, {
    create: createMutation,
    update: updateMutation,
    delete: deleteMutation,
  }, {
    buildUpdatePayload: (vendorId, data) => ({ vendorId, data }),
  });

  return {
    vendors: core.items,
    selectedVendor: core.selectedItem,
    filters: core.filters,
    pagination: core.pagination,
    loading: core.loading,
    isLoading: core.isLoading,
    isError: core.isError,
    error: core.error,
    isFetching: core.isFetching,
    createVendor: core.handleCreate,
    updateVendor: core.handleUpdate,
    deleteVendor: core.handleDelete,
    setPage: core.setPage,
    setFilters: core.setFilters,
    selectVendor: core.selectItem as (vendor: Vendor | null) => void,
    resetFilters: core.resetFilters,
    refetch: core.refetch,
    isCreating: core.isCreating,
    isUpdating: core.isUpdating,
    isDeleting: core.isDeleting,
  };
};

export const useVendorDetailWithStore = (vendorId: number | null | undefined) => {
  const store = useVendorsStoreCompat();
  const vendorQuery = useVendor(vendorId);
  const detail = useEntityDetailCore(store, vendorQuery);

  return {
    vendor: detail.data,
    isLoading: detail.isLoading,
    isError: detail.isError,
    error: detail.error,
    refetch: detail.refetch,
  };
};
