/**
 * 專案管理 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */
// @ts-ignore
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi, ProjectListParams, ProjectStatistics } from '../api/projectsApi';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';
import type { Project, ProjectCreate, ProjectUpdate } from '../types/api';
import type { PaginatedResponse } from '../api/types';

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得專案列表
 *
 * @param params 查詢參數
 * @returns React Query 結果
 */
export const useProjects = (params?: ProjectListParams) => {
  return useQuery({
    queryKey: queryKeys.projects.list(params || {}),
    queryFn: () => projectsApi.getProjects(params),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得單一專案詳情
 *
 * @param projectId 專案 ID
 * @returns React Query 結果
 */
export const useProject = (projectId: number | null | undefined) => {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId ?? 0),
    queryFn: () => projectsApi.getProject(projectId!),
    ...defaultQueryOptions.detail,
    enabled: !!projectId,
  });
};

/**
 * 取得專案統計資料
 *
 * @returns React Query 結果
 */
export const useProjectStatistics = () => {
  return useQuery({
    queryKey: queryKeys.projects.statistics,
    queryFn: () => projectsApi.getStatistics(),
    ...defaultQueryOptions.statistics,
  });
};

/**
 * 取得專案下拉選項
 *
 * @param year 可選的年度篩選
 * @returns React Query 結果
 */
export const useProjectOptions = (year?: number) => {
  return useQuery({
    queryKey: [...queryKeys.projects.all, 'options', year],
    queryFn: () => projectsApi.getProjectOptions(year),
    ...defaultQueryOptions.dropdown,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 建立專案
 *
 * @returns useMutation 結果
 */
export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) => projectsApi.createProject(data),
    onSuccess: () => {
      // 使相關查詢失效
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
};

/**
 * 更新專案
 *
 * @returns useMutation 結果
 */
export const useUpdateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: number; data: ProjectUpdate }) =>
      projectsApi.updateProject(projectId, data),
    onSuccess: (_, variables) => {
      // 使相關查詢失效
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.detail(variables.projectId),
      });
    },
  });
};

/**
 * 刪除專案
 *
 * @returns useMutation 結果
 */
export const useDeleteProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: number) => projectsApi.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
};

// ============================================================================
// 組合 Hooks
// ============================================================================

/**
 * 取得專案年度選項
 *
 * @returns React Query 結果
 */
export const useProjectYearOptions = () => {
  return useQuery({
    queryKey: [...queryKeys.projects.all, 'years'],
    queryFn: () => projectsApi.getYearOptions(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得專案類別選項
 *
 * @returns React Query 結果
 */
export const useProjectCategoryOptions = () => {
  return useQuery({
    queryKey: [...queryKeys.projects.all, 'categories'],
    queryFn: () => projectsApi.getCategoryOptions(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 取得專案狀態選項
 *
 * @returns React Query 結果
 */
export const useProjectStatusOptions = () => {
  return useQuery({
    queryKey: [...queryKeys.projects.all, 'statuses'],
    queryFn: () => projectsApi.getStatusOptions(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 專案頁面 hook - 整合列表、統計與操作方法
 *
 * @param params 查詢參數
 * @returns 專案列表、統計資料與操作方法
 */
export const useProjectsPage = (params?: ProjectListParams) => {
  const projectsQuery = useProjects(params);
  const statisticsQuery = useProjectStatistics();
  const yearsQuery = useProjectYearOptions();
  const categoriesQuery = useProjectCategoryOptions();
  const statusesQuery = useProjectStatusOptions();
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();

  return {
    // 列表相關
    projects: projectsQuery.data?.items ?? [],
    pagination: projectsQuery.data?.pagination,
    isLoading: projectsQuery.isLoading,
    isError: projectsQuery.isError,
    error: projectsQuery.error,
    refetch: projectsQuery.refetch,

    // 統計相關
    statistics: statisticsQuery.data,
    isStatisticsLoading: statisticsQuery.isLoading,
    refetchStatistics: statisticsQuery.refetch,

    // 篩選選項
    availableYears: yearsQuery.data ?? [],
    availableCategories: categoriesQuery.data ?? [],
    availableStatuses: statusesQuery.data ?? [],
    isOptionsLoading: yearsQuery.isLoading || categoriesQuery.isLoading || statusesQuery.isLoading,

    // 操作方法
    createProject: createMutation.mutateAsync,
    updateProject: updateMutation.mutateAsync,
    deleteProject: deleteMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
};
