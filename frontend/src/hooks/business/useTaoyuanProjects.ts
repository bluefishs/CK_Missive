/**
 * 桃園派工專案 Hook
 *
 * 集中管理桃園派工專案的 useQuery 邏輯
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import { useQuery } from '@tanstack/react-query';
import { taoyuanProjectsApi } from '../../api/taoyuanDispatchApi';
import type { TaoyuanProject } from '../../types/api';

interface UseTaoyuanProjectsParams {
  skip?: number;
  limit?: number;
  search?: string;
  district?: string;
  review_year?: number;
  case_type?: string;
  contract_project_id?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

interface UseTaoyuanProjectsResult {
  projects: TaoyuanProject[];
  total: number;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * 桃園派工專案列表 Hook
 */
export const useTaoyuanProjects = (params: UseTaoyuanProjectsParams): UseTaoyuanProjectsResult => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['taoyuan-projects', params],
    queryFn: () => taoyuanProjectsApi.getList(params),
    staleTime: 30000,
  });

  return {
    projects: data?.items || [],
    total: data?.pagination?.total || 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};

/**
 * 單一桃園派工專案 Hook
 */
export const useTaoyuanProject = (projectId: number | undefined) => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['taoyuan-project', projectId],
    queryFn: () => taoyuanProjectsApi.getDetail(projectId!),
    enabled: !!projectId,
    staleTime: 30000,
  });

  return {
    project: data,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};
