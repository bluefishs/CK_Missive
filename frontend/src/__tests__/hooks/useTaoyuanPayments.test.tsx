/**
 * useTaoyuanPayments Hook 單元測試
 * useTaoyuanPayments Hook Unit Tests
 *
 * 測試桃園派工請款 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useTaoyuanPayments
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type {
  ContractPayment,
  ContractPaymentListResponse,
  PaymentControlResponse,
  PaymentControlItem,
  PaginationMeta,
} from '../../types/api';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的契金紀錄 Mock 資料 */
const createMockPayment = (overrides: Partial<ContractPayment> = {}): ContractPayment => ({
  id: 1,
  dispatch_order_id: 100,
  work_01_date: '2026-01-15',
  work_01_amount: 50000,
  current_amount: 50000,
  cumulative_amount: 50000,
  remaining_amount: 150000,
  dispatch_no: 'D-2026-001',
  project_name: '中正路拓寬工程',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

/** 建立契金列表回應 Mock 資料 */
const createMockPaymentListResponse = (
  items: ContractPayment[],
  paginationOverrides: Partial<PaginationMeta> = {}
): ContractPaymentListResponse => ({
  success: true,
  items,
  pagination: {
    total: items.length,
    page: 1,
    limit: 20,
    total_pages: 1,
    has_next: false,
    has_prev: false,
    ...paginationOverrides,
  },
});

/** 建立契金管控回應 Mock 資料 */
const createMockPaymentControlResponse = (
  items: PaymentControlItem[],
  overrides: Partial<PaymentControlResponse> = {}
): PaymentControlResponse => ({
  success: true,
  items,
  total_budget: 1000000,
  total_dispatched: 500000,
  total_remaining: 500000,
  pagination: {
    total: items.length,
    page: 1,
    limit: 500,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  },
  ...overrides,
});

// Mock taoyuanDispatchApi
vi.mock('../../api/taoyuanDispatchApi', () => ({
  contractPaymentsApi: {
    getList: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    getControlList: vi.fn(),
  },
}));

// 引入被測試的 hooks
import {
  useTaoyuanPayments,
  useTaoyuanPaymentControl,
} from '../../hooks/business/useTaoyuanPayments';

import { contractPaymentsApi } from '../../api/taoyuanDispatchApi';

// 建立測試用 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

// 建立 wrapper
const createWrapper = () => {
  const queryClient = createTestQueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

// ============================================================================
// useTaoyuanPayments Hook 測試
// ============================================================================

describe('useTaoyuanPayments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得派工單的契金列表', async () => {
    const mockResponse = createMockPaymentListResponse([
      createMockPayment({ id: 1, dispatch_order_id: 100, current_amount: 50000 }),
      createMockPayment({ id: 2, dispatch_order_id: 100, current_amount: 30000 }),
    ], { total: 2 });

    vi.mocked(contractPaymentsApi.getList).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useTaoyuanPayments(100), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.payments).toHaveLength(2);
    expect(result.current.payments[0]?.current_amount).toBe(50000);
    expect(result.current.total).toBe(2);
  });

  it('當 dispatchOrderId 為 0 時不應該發送請求', async () => {
    const { result } = renderHook(() => useTaoyuanPayments(0), {
      wrapper: createWrapper(),
    });

    // enabled: !!dispatchOrderId 為 false 時不發送請求
    expect(result.current.isLoading).toBe(false);
    expect(contractPaymentsApi.getList).not.toHaveBeenCalled();
  });

  it('應該正確傳遞 dispatchOrderId 參數', async () => {
    vi.mocked(contractPaymentsApi.getList).mockResolvedValue(
      createMockPaymentListResponse([], { total: 0, total_pages: 0 })
    );

    renderHook(() => useTaoyuanPayments(200), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(contractPaymentsApi.getList).toHaveBeenCalledWith(200);
    });
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('契金資料載入失敗');
    vi.mocked(contractPaymentsApi.getList).mockRejectedValue(error);

    const { result } = renderHook(() => useTaoyuanPayments(100), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });

    expect(result.current.error?.message).toBe('契金資料載入失敗');
  });
});

// ============================================================================
// useTaoyuanPaymentControl Hook 測試
// ============================================================================

describe('useTaoyuanPaymentControl', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得契金管控列表', async () => {
    const mockItems: PaymentControlItem[] = [
      {
        dispatch_order_id: 1,
        dispatch_no: 'D-2026-001',
        project_name: '中正路工程',
        work_type: '鑑價',
        sub_case_name: '分案A',
      },
      {
        dispatch_order_id: 2,
        dispatch_no: 'D-2026-002',
        project_name: '中華路工程',
        work_type: '複估',
        sub_case_name: '分案B',
      },
    ];

    vi.mocked(contractPaymentsApi.getControlList).mockResolvedValue(
      createMockPaymentControlResponse(mockItems)
    );

    const { result } = renderHook(() => useTaoyuanPaymentControl(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.items).toHaveLength(2);
    expect(result.current.totalBudget).toBe(1000000);
    expect(result.current.totalDispatched).toBe(500000);
  });

  it('當 contractProjectId 為 0 時不應該發送請求', async () => {
    const { result } = renderHook(() => useTaoyuanPaymentControl(0), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(contractPaymentsApi.getControlList).not.toHaveBeenCalled();
  });
});
