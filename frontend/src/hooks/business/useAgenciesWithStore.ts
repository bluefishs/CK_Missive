/**
 * 機關管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { useEffect, useCallback } from 'react';
import { AgencyFilter } from '../../store';
import { useAgenciesStoreCompat } from '../../store/agencies';
import {
  useAgencies,
  useAgency,
  useCreateAgency,
  useUpdateAgency,
  useDeleteAgency,
} from './useAgencies';
import type { Agency, AgencyCreate, AgencyUpdate, AgencyWithStats } from '../../types/api';
import type { AgencyListParams } from '../../api/agenciesApi';

/**
 * 機關列表整合 Hook
 *
 * 自動同步 React Query 資料到 Zustand Store
 */
export const useAgenciesWithStore = () => {
  const store = useAgenciesStoreCompat();

  // 將 Store 的 filters 轉換為 API 參數
  const apiParams: AgencyListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    agency_type: store.filters.agency_type,
  };

  // React Query hooks
  const agenciesQuery = useAgencies(apiParams);
  const createMutation = useCreateAgency();
  const updateMutation = useUpdateAgency();
  const deleteMutation = useDeleteAgency();

  // 同步 React Query 資料到 Store
  useEffect(() => {
    if (agenciesQuery.data?.items) {
      store.setAgencies(agenciesQuery.data.items as AgencyWithStats[]);
    }
    if (agenciesQuery.data?.pagination) {
      store.setPagination({
        total: agenciesQuery.data.pagination.total,
        totalPages: agenciesQuery.data.pagination.total_pages,
      });
    }
  }, [agenciesQuery.data]);

  // 同步載入狀態
  useEffect(() => {
    store.setLoading(agenciesQuery.isLoading);
  }, [agenciesQuery.isLoading]);

  // 操作方法
  const handleCreate = useCallback(
    async (data: AgencyCreate) => {
      const result = await createMutation.mutateAsync(data);
      if (result) {
        store.addAgency(result as AgencyWithStats);
      }
      return result;
    },
    [createMutation, store]
  );

  const handleUpdate = useCallback(
    async (agencyId: number, data: AgencyUpdate) => {
      const result = await updateMutation.mutateAsync({ agencyId, data });
      if (result) {
        store.updateAgency(agencyId, result);
      }
      return result;
    },
    [updateMutation, store]
  );

  const handleDelete = useCallback(
    async (agencyId: number) => {
      await deleteMutation.mutateAsync(agencyId);
      store.removeAgency(agencyId);
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
    (filters: Partial<AgencyFilter>) => {
      store.setFilters(filters);
    },
    [store]
  );

  const handleSelect = useCallback(
    (agency: Agency | null) => {
      store.setSelectedAgency(agency);
    },
    [store]
  );

  return {
    // Store 狀態 (UI State)
    agencies: store.agencies,
    selectedAgency: store.selectedAgency,
    filters: store.filters,
    pagination: store.pagination,
    loading: store.loading,

    // React Query 狀態 (Server State)
    isLoading: agenciesQuery.isLoading,
    isError: agenciesQuery.isError,
    error: agenciesQuery.error,
    isFetching: agenciesQuery.isFetching,

    // 操作方法
    createAgency: handleCreate,
    updateAgency: handleUpdate,
    deleteAgency: handleDelete,

    // UI 操作
    setPage: handlePageChange,
    setFilters: handleFilterChange,
    selectAgency: handleSelect,
    resetFilters: store.resetFilters,
    refetch: agenciesQuery.refetch,

    // Mutation 狀態
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

/**
 * 單一機關詳情 Hook（整合 Store）
 */
export const useAgencyDetailWithStore = (agencyId: number | null | undefined) => {
  const store = useAgenciesStoreCompat();
  const agencyQuery = useAgency(agencyId);

  // 同步到 Store
  useEffect(() => {
    if (agencyQuery.data) {
      store.setSelectedAgency(agencyQuery.data);
    }
  }, [agencyQuery.data]);

  return {
    agency: agencyQuery.data || store.selectedAgency,
    isLoading: agencyQuery.isLoading,
    isError: agencyQuery.isError,
    error: agencyQuery.error,
    refetch: agencyQuery.refetch,
  };
};
