/**
 * useVendors Hook 單元測試
 * useVendors Hook Unit Tests
 *
 * 測試廠商管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useVendors
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Vendor, VendorOption } from '../../types/api';
import type { PaginatedResponse, DeleteResponse } from '../../api/types';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的廠商 Mock 資料 */
const createMockVendor = (overrides: Partial<Vendor> = {}): Vendor => ({
  id: 1,
  vendor_name: '測試廠商',
  vendor_code: 'V001',
  contact_person: '張三',
  phone: '02-12345678',
  email: 'test@example.com',
  address: '台北市信義區',
  business_type: '測量業務',
  rating: 4.5,
  notes: '測試備註',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

/** 建立分頁回應 Mock 資料 */
function createMockPaginatedResponse<T>(
  items: T[],
  paginationOverrides: Partial<PaginatedResponse<T>['pagination']> = {}
): PaginatedResponse<T> {
  return {
    success: true as const,
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

/** 建立刪除回應 Mock 資料 */
const createMockDeleteResponse = (deletedId: number): DeleteResponse => ({
  success: true,
  message: '刪除成功',
  deleted_id: deletedId,
});

// Mock vendorsApi
vi.mock('../../api/vendorsApi', () => ({
  vendorsApi: {
    getVendors: vi.fn(),
    getVendor: vi.fn(),
    createVendor: vi.fn(),
    updateVendor: vi.fn(),
    deleteVendor: vi.fn(),
    getStatistics: vi.fn(),
    getVendorOptions: vi.fn(),
    searchVendors: vi.fn(),
    batchDelete: vi.fn(),
  },
}));

// Mock queryConfig
vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    vendors: {
      all: ['vendors'],
      lists: () => ['vendors', 'list'],
      list: (params: Record<string, unknown>) => ['vendors', 'list', params],
      details: () => ['vendors', 'detail'],
      detail: (id: number) => ['vendors', 'detail', id],
      dropdown: ['vendors', 'dropdown'],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 0, gcTime: 0, refetchOnWindowFocus: false },
    detail: { staleTime: 0, gcTime: 0 },
    dropdown: { staleTime: 0, gcTime: 0, refetchOnWindowFocus: false, refetchOnMount: false },
    statistics: { staleTime: 0, gcTime: 0, refetchOnWindowFocus: false },
  },
}));

// 引入被測試的 hooks
import {
  useVendors,
  useVendor,
  useVendorOptions,
  useCreateVendor,
  useUpdateVendor,
  useDeleteVendor,
  useBatchDeleteVendors,
  useVendorsPage,
} from '../../hooks/business/useVendors';

import { vendorsApi } from '../../api/vendorsApi';

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
// useVendors Hook 測試
// ============================================================================

describe('useVendors', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得廠商列表', async () => {
    const mockResponse = createMockPaginatedResponse([
      createMockVendor({ id: 1, vendor_name: '測試廠商A', vendor_code: 'V001' }),
      createMockVendor({ id: 2, vendor_name: '測試廠商B', vendor_code: 'V002' }),
    ], { total: 2 });

    vi.mocked(vendorsApi.getVendors).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useVendors(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items?.[0]?.vendor_name).toBe('測試廠商A');
  });

  it('應該正確傳遞查詢參數', async () => {
    vi.mocked(vendorsApi.getVendors).mockResolvedValue(
      createMockPaginatedResponse<Vendor>([], { total: 0, limit: 10, total_pages: 0 })
    );

    const params = {
      page: 2,
      limit: 10,
      search: '測量',
      business_type: '測量業務',
    };

    renderHook(() => useVendors(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(vendorsApi.getVendors).toHaveBeenCalledWith(params);
    });
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('API Error');
    vi.mocked(vendorsApi.getVendors).mockRejectedValue(error);

    const { result } = renderHook(() => useVendors(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

// ============================================================================
// useVendor Hook 測試
// ============================================================================

describe('useVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得單一廠商', async () => {
    const mockVendor = createMockVendor({
      id: 1,
      vendor_name: '乾坤測繪',
      vendor_code: 'CK001',
      business_type: '測量業務',
    });

    vi.mocked(vendorsApi.getVendor).mockResolvedValue(mockVendor);

    const { result } = renderHook(() => useVendor(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.vendor_name).toBe('乾坤測繪');
    expect(result.current.data?.vendor_code).toBe('CK001');
  });

  it('當 vendorId 為 null 時不應該發送請求', async () => {
    const { result } = renderHook(() => useVendor(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(vendorsApi.getVendor).not.toHaveBeenCalled();
  });

  it('當 vendorId 為 undefined 時不應該發送請求', async () => {
    const { result } = renderHook(() => useVendor(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(vendorsApi.getVendor).not.toHaveBeenCalled();
  });
});

// ============================================================================
// useVendorOptions Hook 測試
// ============================================================================

describe('useVendorOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得廠商下拉選項', async () => {
    const mockOptions: VendorOption[] = [
      { id: 1, vendor_name: '廠商A', vendor_code: 'V001' },
      { id: 2, vendor_name: '廠商B', vendor_code: 'V002' },
      { id: 3, vendor_name: '廠商C' },
    ];

    vi.mocked(vendorsApi.getVendorOptions).mockResolvedValue(mockOptions);

    const { result } = renderHook(() => useVendorOptions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(3);
    expect(result.current.data?.[0]?.vendor_name).toBe('廠商A');
  });
});

// ============================================================================
// Mutation Hooks 測試
// ============================================================================

describe('useCreateVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功建立廠商', async () => {
    const newVendor = createMockVendor({
      id: 10,
      vendor_name: '新增廠商',
      vendor_code: 'NEW001',
      business_type: '查估業務',
    });

    vi.mocked(vendorsApi.createVendor).mockResolvedValue(newVendor);

    const { result } = renderHook(() => useCreateVendor(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      vendor_name: '新增廠商',
      vendor_code: 'NEW001',
      business_type: '查估業務',
    });

    expect(vendorsApi.createVendor).toHaveBeenCalledWith({
      vendor_name: '新增廠商',
      vendor_code: 'NEW001',
      business_type: '查估業務',
    });
  });
});

describe('useUpdateVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功更新廠商', async () => {
    const updatedVendor = createMockVendor({
      id: 1,
      vendor_name: '更新後的廠商名稱',
      rating: 5,
    });

    vi.mocked(vendorsApi.updateVendor).mockResolvedValue(updatedVendor);

    const { result } = renderHook(() => useUpdateVendor(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      vendorId: 1,
      data: { vendor_name: '更新後的廠商名稱', rating: 5 },
    });

    expect(vendorsApi.updateVendor).toHaveBeenCalledWith(1, {
      vendor_name: '更新後的廠商名稱',
      rating: 5,
    });
  });
});

describe('useDeleteVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功刪除廠商', async () => {
    vi.mocked(vendorsApi.deleteVendor).mockResolvedValue(
      createMockDeleteResponse(1)
    );

    const { result } = renderHook(() => useDeleteVendor(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync(1);

    expect(vendorsApi.deleteVendor).toHaveBeenCalledWith(1);
  });
});

describe('useBatchDeleteVendors', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功批次刪除廠商', async () => {
    vi.mocked(vendorsApi.batchDelete).mockResolvedValue({
      success_count: 3,
      failed_count: 0,
      failed_ids: [],
      errors: [],
    });

    const { result } = renderHook(() => useBatchDeleteVendors(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync([1, 2, 3]);

    expect(vendorsApi.batchDelete).toHaveBeenCalledWith([1, 2, 3]);
  });
});

// ============================================================================
// useVendorsPage Hook 測試
// ============================================================================

describe('useVendorsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 設定預設 mock 回傳值
    vi.mocked(vendorsApi.getVendors).mockResolvedValue(
      createMockPaginatedResponse([
        createMockVendor({ id: 1, vendor_name: '測試廠商', vendor_code: 'V001' }),
      ], { total: 1 })
    );

    vi.mocked(vendorsApi.createVendor).mockResolvedValue(
      createMockVendor({ id: 10, vendor_name: '新增廠商', vendor_code: 'NEW001' })
    );
  });

  it('應該整合多個查詢結果', async () => {
    const { result } = renderHook(() => useVendorsPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 驗證列表資料
    expect(result.current.vendors).toHaveLength(1);
    expect(result.current.vendors[0]?.vendor_name).toBe('測試廠商');

    // 驗證分頁資料
    expect(result.current.pagination?.total).toBe(1);
  });

  it('應該提供操作方法', async () => {
    const { result } = renderHook(() => useVendorsPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 驗證操作方法存在
    expect(typeof result.current.createVendor).toBe('function');
    expect(typeof result.current.updateVendor).toBe('function');
    expect(typeof result.current.deleteVendor).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
  });

  it('應該正確傳遞篩選參數', async () => {
    const params = { search: '測量', business_type: '測量業務' };

    renderHook(() => useVendorsPage(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(vendorsApi.getVendors).toHaveBeenCalledWith(params);
    });
  });
});
