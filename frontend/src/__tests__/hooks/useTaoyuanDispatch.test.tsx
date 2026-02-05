/**
 * useTaoyuanDispatch Hook 單元測試
 * useTaoyuanDispatch Hook Unit Tests
 *
 * 測試桃園派工派工單 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useTaoyuanDispatch
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { DispatchOrder } from '../../types/api';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的派工單 Mock 資料 */
const createMockDispatchOrder = (overrides: Partial<DispatchOrder> = {}): DispatchOrder => ({
  id: 1,
  case_name: '測試派工案件',
  work_type: '鑑價',
  status: '待派工',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

/** 建立分頁回應 Mock 資料 */
interface PaginatedResponse<T> {
  items: T[];
  pagination: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

function createMockPaginatedResponse<T>(
  items: T[],
  paginationOverrides: Partial<PaginatedResponse<T>['pagination']> = {}
): PaginatedResponse<T> {
  return {
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
  };
}

// Mock dispatchOrdersApi
vi.mock('../../api/taoyuanDispatchApi', () => ({
  dispatchOrdersApi: {
    getList: vi.fn(),
    getDetail: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

// 引入被測試的 hooks
import {
  useTaoyuanDispatchOrders,
  useTaoyuanDispatchOrder,
} from '../../hooks/business/useTaoyuanDispatch';

import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';

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
// useTaoyuanDispatchOrders Hook 測試
// ============================================================================

describe('useTaoyuanDispatchOrders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得派工單列表', async () => {
    const mockResponse = createMockPaginatedResponse([
      createMockDispatchOrder({ id: 1, case_name: '派工案件A' }),
      createMockDispatchOrder({ id: 2, case_name: '派工案件B' }),
    ], { total: 2 });

    vi.mocked(dispatchOrdersApi.getList).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useTaoyuanDispatchOrders({}), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.dispatchOrders).toHaveLength(2);
    expect(result.current.dispatchOrders[0]?.case_name).toBe('派工案件A');
    expect(result.current.total).toBe(2);
  });

  it('應該正確傳遞查詢參數', async () => {
    vi.mocked(dispatchOrdersApi.getList).mockResolvedValue(
      createMockPaginatedResponse<DispatchOrder>([], { total: 0 })
    );

    const params = {
      skip: 20,
      limit: 10,
      search: '測試',
      status: '已完成',
      work_type: '鑑價',
    };

    renderHook(() => useTaoyuanDispatchOrders(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(dispatchOrdersApi.getList).toHaveBeenCalledWith(params);
    });
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('API Error');
    vi.mocked(dispatchOrdersApi.getList).mockRejectedValue(error);

    const { result } = renderHook(() => useTaoyuanDispatchOrders({}), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.error).toBe(error);
    });
  });

  it('當列表為空時應該返回空陣列', async () => {
    vi.mocked(dispatchOrdersApi.getList).mockResolvedValue(
      createMockPaginatedResponse<DispatchOrder>([], { total: 0 })
    );

    const { result } = renderHook(() => useTaoyuanDispatchOrders({}), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.dispatchOrders).toEqual([]);
    expect(result.current.total).toBe(0);
  });

  it('應該支援 project_id 篩選', async () => {
    vi.mocked(dispatchOrdersApi.getList).mockResolvedValue(
      createMockPaginatedResponse([
        createMockDispatchOrder({ id: 1, case_name: '專案A派工' }),
      ])
    );

    renderHook(() => useTaoyuanDispatchOrders({ project_id: 123 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(dispatchOrdersApi.getList).toHaveBeenCalledWith(
        expect.objectContaining({ project_id: 123 })
      );
    });
  });

  it('應該支援排序參數', async () => {
    vi.mocked(dispatchOrdersApi.getList).mockResolvedValue(
      createMockPaginatedResponse<DispatchOrder>([])
    );

    renderHook(() => useTaoyuanDispatchOrders({
      sort_by: 'created_at',
      sort_order: 'desc',
    }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(dispatchOrdersApi.getList).toHaveBeenCalledWith(
        expect.objectContaining({
          sort_by: 'created_at',
          sort_order: 'desc',
        })
      );
    });
  });
});

// ============================================================================
// useTaoyuanDispatchOrder Hook 測試
// ============================================================================

describe('useTaoyuanDispatchOrder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得單一派工單', async () => {
    const mockDispatch = createMockDispatchOrder({
      id: 1,
      case_name: '測試派工',
      work_type: '鑑價',
      status: '處理中',
    });

    vi.mocked(dispatchOrdersApi.getDetail).mockResolvedValue(mockDispatch);

    const { result } = renderHook(() => useTaoyuanDispatchOrder(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.dispatchOrder?.case_name).toBe('測試派工');
    expect(result.current.dispatchOrder?.work_type).toBe('鑑價');
  });

  it('當 orderId 為 undefined 時不應該發送請求', async () => {
    const { result } = renderHook(() => useTaoyuanDispatchOrder(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(dispatchOrdersApi.getDetail).not.toHaveBeenCalled();
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('Not Found');
    vi.mocked(dispatchOrdersApi.getDetail).mockRejectedValue(error);

    const { result } = renderHook(() => useTaoyuanDispatchOrder(999), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.error).toBe(error);
    });
  });

  it('應該提供 refetch 方法', async () => {
    const mockDispatch = createMockDispatchOrder({ id: 1 });
    vi.mocked(dispatchOrdersApi.getDetail).mockResolvedValue(mockDispatch);

    const { result } = renderHook(() => useTaoyuanDispatchOrder(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(typeof result.current.refetch).toBe('function');
  });
});
