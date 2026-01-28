/**
 * 機關管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 2.0.0 - 使用 createEntityHookWithStore 工廠
 * @date 2026-01-28
 */

import { useAgenciesStoreCompat } from '../../store/agencies';
import {
  useAgencies,
  useAgency,
  useCreateAgency,
  useUpdateAgency,
  useDeleteAgency,
} from './useAgencies';
import type { Agency } from '../../types/api';
import type { AgencyListParams } from '../../api/agenciesApi';
import { useEntityWithStoreCore, useEntityDetailCore } from './createEntityHookWithStore';

export const useAgenciesWithStore = () => {
  const store = useAgenciesStoreCompat();

  const apiParams: AgencyListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    agency_type: store.filters.agency_type,
  };

  const agenciesQuery = useAgencies(apiParams);
  const createMutation = useCreateAgency();
  const updateMutation = useUpdateAgency();
  const deleteMutation = useDeleteAgency();

  const core = useEntityWithStoreCore(store, agenciesQuery, {
    create: createMutation,
    update: updateMutation,
    delete: deleteMutation,
  }, {
    buildUpdatePayload: (agencyId, data) => ({ agencyId, data }),
  });

  return {
    agencies: core.items,
    selectedAgency: core.selectedItem,
    filters: core.filters,
    pagination: core.pagination,
    loading: core.loading,
    isLoading: core.isLoading,
    isError: core.isError,
    error: core.error,
    isFetching: core.isFetching,
    createAgency: core.handleCreate,
    updateAgency: core.handleUpdate,
    deleteAgency: core.handleDelete,
    setPage: core.setPage,
    setFilters: core.setFilters,
    selectAgency: core.selectItem as (agency: Agency | null) => void,
    resetFilters: core.resetFilters,
    refetch: core.refetch,
    isCreating: core.isCreating,
    isUpdating: core.isUpdating,
    isDeleting: core.isDeleting,
  };
};

export const useAgencyDetailWithStore = (agencyId: number | null | undefined) => {
  const store = useAgenciesStoreCompat();
  const agencyQuery = useAgency(agencyId);
  const detail = useEntityDetailCore(store, agencyQuery);

  return {
    agency: detail.data,
    isLoading: detail.isLoading,
    isError: detail.isError,
    error: detail.error,
    refetch: detail.refetch,
  };
};
