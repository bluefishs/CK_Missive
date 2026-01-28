/**
 * 專案管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 2.0.0 - 使用 createEntityHookWithStore 工廠
 * @date 2026-01-28
 */

import { useProjectsStoreCompat } from '../../store/projects';
import {
  useProjects,
  useProject,
  useProjectStatistics,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  useProjectYearOptions,
  useProjectCategoryOptions,
  useProjectStatusOptions,
} from './useProjects';
import type { Project } from '../../types/api';
import type { ProjectListParams } from '../../api/projectsApi';
import { useEntityWithStoreCore, useEntityDetailCore } from './createEntityHookWithStore';

export const useProjectsWithStore = () => {
  const store = useProjectsStoreCompat();

  const apiParams: ProjectListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    year: store.filters.year,
    category: store.filters.category,
    status: store.filters.status,
  };

  const projectsQuery = useProjects(apiParams);
  const statisticsQuery = useProjectStatistics();
  const yearsQuery = useProjectYearOptions();
  const categoriesQuery = useProjectCategoryOptions();
  const statusesQuery = useProjectStatusOptions();
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();

  const core = useEntityWithStoreCore(store, projectsQuery, {
    create: createMutation,
    update: updateMutation,
    delete: deleteMutation,
  }, {
    buildUpdatePayload: (projectId, data) => ({ projectId, data }),
  });

  return {
    projects: core.items,
    selectedProject: core.selectedItem,
    filters: core.filters,
    pagination: core.pagination,
    loading: core.loading,
    isLoading: core.isLoading,
    isError: core.isError,
    error: core.error,
    isFetching: core.isFetching,
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,
    availableYears: yearsQuery.data ?? [],
    availableCategories: categoriesQuery.data ?? [],
    availableStatuses: statusesQuery.data ?? [],
    createProject: core.handleCreate,
    updateProject: core.handleUpdate,
    deleteProject: core.handleDelete,
    setPage: core.setPage,
    setFilters: core.setFilters,
    selectProject: core.selectItem as (project: Project | null) => void,
    resetFilters: core.resetFilters,
    refetch: core.refetch,
    isCreating: core.isCreating,
    isUpdating: core.isUpdating,
    isDeleting: core.isDeleting,
  };
};

export const useProjectDetailWithStore = (projectId: number | null | undefined) => {
  const store = useProjectsStoreCompat();
  const projectQuery = useProject(projectId);
  const detail = useEntityDetailCore(store, projectQuery);

  return {
    project: detail.data,
    isLoading: detail.isLoading,
    isError: detail.isError,
    error: detail.error,
    refetch: detail.refetch,
  };
};
