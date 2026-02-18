/**
 * 桃園派工派工單 Hook
 *
 * 集中管理桃園派工派工單的 useQuery 邏輯
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import { useQuery } from '@tanstack/react-query';
import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';
import type { DispatchOrder } from '../../types/api';
import { queryKeys } from '../../config/queryConfig';

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
    staleTime: 30000,
  });

  return {
    dispatchOrders: data?.items || [],
    total: data?.pagination?.total || 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
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
    staleTime: 30000,
  });

  return {
    dispatchOrder: data,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};
