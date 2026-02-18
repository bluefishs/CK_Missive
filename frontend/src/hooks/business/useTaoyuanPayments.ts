/**
 * 桃園派工請款 Hook
 *
 * 集中管理桃園派工請款的 useQuery 邏輯
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import { useQuery } from '@tanstack/react-query';
import { contractPaymentsApi } from '../../api/taoyuanDispatchApi';
import type { ContractPayment, PaymentControlItem } from '../../types/api';
import { queryKeys } from '../../config/queryConfig';

interface UseTaoyuanPaymentsResult {
  payments: ContractPayment[];
  total: number;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * 桃園派工請款列表 Hook
 */
export const useTaoyuanPayments = (dispatchOrderId: number): UseTaoyuanPaymentsResult => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.taoyuanPayments.byDispatch(dispatchOrderId),
    queryFn: () => contractPaymentsApi.getList(dispatchOrderId),
    staleTime: 30000,
    enabled: !!dispatchOrderId,
  });

  return {
    payments: data?.items || [],
    total: data?.pagination?.total || 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};

/**
 * 契金管控列表 Hook (用於 PaymentsTab)
 */
export const useTaoyuanPaymentControl = (contractProjectId: number) => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.taoyuanPayments.paymentControl(contractProjectId),
    queryFn: () => contractPaymentsApi.getControlList(contractProjectId),
    staleTime: 30000,
    enabled: !!contractProjectId,
  });

  return {
    items: data?.items || [] as PaymentControlItem[],
    totalBudget: data?.total_budget || 0,
    totalDispatched: data?.total_dispatched || 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};
