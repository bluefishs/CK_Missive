/**
 * 桃園派工派工單 Hook
 *
 * 集中管理桃園派工派工單的 useQuery 邏輯
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';
import type { DispatchOrder } from '../../types/api';
import { queryKeys, defaultQueryOptions } from '../../config/queryConfig';
import { setDispatchProjectIds } from '../../config/projectModules';

interface UseTaoyuanDispatchParams {
  skip?: number;
  limit?: number;
  project_id?: number;
  contract_project_id?: number;
  search?: string;
  status?: string;
  work_type?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

interface UseTaoyuanDispatchResult {
  dispatchOrders: DispatchOrder[];
  total: number;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * 桃園派工派工單列表 Hook
 */
export const useTaoyuanDispatchOrders = (params: UseTaoyuanDispatchParams): UseTaoyuanDispatchResult => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.taoyuanDispatch.orders(params),
    queryFn: () => dispatchOrdersApi.getList(params),
    staleTime: 120_000,
  });

  return {
    dispatchOrders: data?.items || [],
    total: data?.pagination?.total ?? 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};

/**
 * 桃園派工承攬案件列表 Hook（專案切換下拉選單用）
 */
export const useTaoyuanContractProjects = () => {
  return useQuery({
    queryKey: [...queryKeys.taoyuanDispatch.all, 'contract-projects'],
    queryFn: () => dispatchOrdersApi.getContractProjects(),
    ...defaultQueryOptions.dropdown,
  });
};

/**
 * 初始化派工案件 ID 快取
 *
 * 從 API 載入已啟用派工管理的承攬案件列表，
 * 並同步至 projectModules 的全域快取。
 * 應在 App 頂層或 Layout 中呼叫一次。
 */
export const useDispatchProjectIds = () => {
  const { data: projects } = useTaoyuanContractProjects();

  useEffect(() => {
    if (projects && projects.length > 0) {
      setDispatchProjectIds(projects.map(p => p.id));
    }
  }, [projects]);
};

/**
 * 單一派工單 Hook
 */
export const useTaoyuanDispatchOrder = (orderId: number | undefined) => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.taoyuanDispatch.order(orderId),
    queryFn: () => dispatchOrdersApi.getDetail(orderId!),
    enabled: !!orderId,
    staleTime: 120_000,
  });

  return {
    dispatchOrder: data,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};
