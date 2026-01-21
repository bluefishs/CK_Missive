/**
 * 專案管理整合 Hook
 *
 * 整合 React Query (Server State) 與 Zustand Store (UI State)
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { useEffect, useCallback } from 'react';
import { ProjectFilter } from '../../store';
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
import type { Project, ProjectCreate, ProjectUpdate } from '../../types/api';
import type { ProjectListParams } from '../../api/projectsApi';

/**
 * 專案列表整合 Hook
 *
 * 自動同步 React Query 資料到 Zustand Store，提供統一的狀態管理介面
 */
export const useProjectsWithStore = () => {
  const store = useProjectsStoreCompat();

  // 將 Store 的 filters 轉換為 API 參數
  const apiParams: ProjectListParams = {
    page: store.pagination.page,
    limit: store.pagination.limit,
    search: store.filters.search,
    year: store.filters.year,
    category: store.filters.category,
    status: store.filters.status,
  };

  // React Query hooks
  const projectsQuery = useProjects(apiParams);
  const statisticsQuery = useProjectStatistics();
  const yearsQuery = useProjectYearOptions();
  const categoriesQuery = useProjectCategoryOptions();
  const statusesQuery = useProjectStatusOptions();
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();

  // 同步 React Query 資料到 Store
  useEffect(() => {
    if (projectsQuery.data?.items) {
      store.setProjects(projectsQuery.data.items);
    }
    if (projectsQuery.data?.pagination) {
      store.setPagination({
        total: projectsQuery.data.pagination.total,
        totalPages: projectsQuery.data.pagination.total_pages,
      });
    }
  }, [projectsQuery.data]);

  // 同步載入狀態
  useEffect(() => {
    store.setLoading(projectsQuery.isLoading);
  }, [projectsQuery.isLoading]);

  // 操作方法
  const handleCreate = useCallback(
    async (data: ProjectCreate) => {
      const result = await createMutation.mutateAsync(data);
      if (result) {
        store.addProject(result);
      }
      return result;
    },
    [createMutation, store]
  );

  const handleUpdate = useCallback(
    async (projectId: number, data: ProjectUpdate) => {
      const result = await updateMutation.mutateAsync({ projectId, data });
      if (result) {
        store.updateProject(projectId, result);
      }
      return result;
    },
    [updateMutation, store]
  );

  const handleDelete = useCallback(
    async (projectId: number) => {
      await deleteMutation.mutateAsync(projectId);
      store.removeProject(projectId);
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
    (filters: Partial<ProjectFilter>) => {
      store.setFilters(filters);
    },
    [store]
  );

  const handleSelect = useCallback(
    (project: Project | null) => {
      store.setSelectedProject(project);
    },
    [store]
  );

  return {
    // Store 狀態 (UI State)
    projects: store.projects,
    selectedProject: store.selectedProject,
    filters: store.filters,
    pagination: store.pagination,
    loading: store.loading,

    // React Query 狀態 (Server State)
    isLoading: projectsQuery.isLoading,
    isError: projectsQuery.isError,
    error: projectsQuery.error,
    isFetching: projectsQuery.isFetching,

    // 統計資料
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,

    // 篩選選項
    availableYears: yearsQuery.data ?? [],
    availableCategories: categoriesQuery.data ?? [],
    availableStatuses: statusesQuery.data ?? [],

    // 操作方法
    createProject: handleCreate,
    updateProject: handleUpdate,
    deleteProject: handleDelete,

    // UI 操作
    setPage: handlePageChange,
    setFilters: handleFilterChange,
    selectProject: handleSelect,
    resetFilters: store.resetFilters,
    refetch: projectsQuery.refetch,

    // Mutation 狀態
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};

/**
 * 單一專案詳情 Hook（整合 Store）
 */
export const useProjectDetailWithStore = (projectId: number | null | undefined) => {
  const store = useProjectsStoreCompat();
  const projectQuery = useProject(projectId);

  // 同步到 Store
  useEffect(() => {
    if (projectQuery.data) {
      store.setSelectedProject(projectQuery.data);
    }
  }, [projectQuery.data]);

  return {
    project: projectQuery.data || store.selectedProject,
    isLoading: projectQuery.isLoading,
    isError: projectQuery.isError,
    error: projectQuery.error,
    refetch: projectQuery.refetch,
  };
};
