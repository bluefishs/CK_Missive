/**
 * useAgencies Hook 單元測試
 * useAgencies Hook Unit Tests
 *
 * 測試機關管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAgencies
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { AgencyWithStats, AgencyOption, AgencyCreate } from '../../types/api';
import type { AgencyStatistics } from '../../api/agenciesApi';
import type { PaginatedResponse, DeleteResponse } from '../../api/types';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的機關 Mock 資料 */
const createMockAgency = (overrides: Partial<AgencyWithStats> = {}): AgencyWithStats => ({
  id: 1,
  agency_name: '桃園市政府',
  agency_short_name: '桃市府',
  agency_code: 'TYC-001',
  agency_type: '政府機關',
  contact_person: '王小明',
  phone: '03-3322101',
  email: 'contact@tyc.gov.tw',
  address: '桃園市桃園區縣府路1號',
  notes: '',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  document_count: 10,
  sent_count: 5,
  received_count: 5,
  last_activity: '2026-01-01T00:00:00Z',
  primary_type: 'both',
  category: '地方政府',
  ...overrides,
});

/** 建立機關選項 Mock 資料 */
const createMockAgencyOption = (overrides: Partial<AgencyOption> = {}): AgencyOption => ({
  id: 1,
  agency_name: '桃園市政府',
  agency_short_name: '桃市府',
  agency_code: 'TYC-001',
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

// Mock agenciesApi
vi.mock('../../api/agenciesApi', () => ({
  agenciesApi: {
    getAgencies: vi.fn(),
    getAgency: vi.fn(),
    getAgencyOptions: vi.fn(),
    getStatistics: vi.fn(),
    createAgency: vi.fn(),
    updateAgency: vi.fn(),
    deleteAgency: vi.fn(),
  },
}));

// Mock queryConfig
vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    agencies: {
      all: ['agencies'],
      list: (params: Record<string, unknown>) => ['agencies', 'list', params],
      detail: (id: number) => ['agencies', 'detail', id],
      dropdown: ['agencies', 'dropdown'],
      statistics: ['agencies', 'statistics'],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 5000 },
    detail: { staleTime: 10000 },
    dropdown: { staleTime: 60000 },
  },
}));

// 引入被測試的 hooks
import {
  useAgencies,
  useAgency,
  useAgencyOptions,
  useAgencyStatistics,
  useCreateAgency,
  useUpdateAgency,
  useDeleteAgency,
  useAgenciesPage,
} from '../../hooks/business/useAgencies';

import { agenciesApi } from '../../api/agenciesApi';

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
// useAgencies Hook 測試
// ============================================================================

describe('useAgencies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得機關列表', async () => {
    const mockResponse = createMockPaginatedResponse([
      createMockAgency({ id: 1, agency_name: '桃園市政府' }),
      createMockAgency({ id: 2, agency_name: '新北市政府' }),
    ], { total: 2 });

    vi.mocked(agenciesApi.getAgencies).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAgencies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items?.[0]?.agency_name).toBe('桃園市政府');
  });

  it('應該正確傳遞查詢參數', async () => {
    vi.mocked(agenciesApi.getAgencies).mockResolvedValue(
      createMockPaginatedResponse<AgencyWithStats>([], { total: 0 })
    );

    const params = {
      page: 2,
      limit: 10,
      keyword: '桃園',
      agency_type: '政府機關',
    };

    renderHook(() => useAgencies(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(agenciesApi.getAgencies).toHaveBeenCalledWith(params);
    });
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('API Error');
    vi.mocked(agenciesApi.getAgencies).mockRejectedValue(error);

    const { result } = renderHook(() => useAgencies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

// ============================================================================
// useAgency Hook 測試
// ============================================================================

describe('useAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得單一機關', async () => {
    const mockAgency = createMockAgency({
      id: 1,
      agency_name: '桃園市政府',
      agency_code: 'TYC-001',
      address: '桃園市桃園區縣府路1號',
    });

    vi.mocked(agenciesApi.getAgency).mockResolvedValue(mockAgency);

    const { result } = renderHook(() => useAgency(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.agency_name).toBe('桃園市政府');
  });

  it('當 agencyId 為 null 時不應該發送請求', async () => {
    const { result } = renderHook(() => useAgency(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(agenciesApi.getAgency).not.toHaveBeenCalled();
  });

  it('當 agencyId 為 undefined 時不應該發送請求', async () => {
    const { result } = renderHook(() => useAgency(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(agenciesApi.getAgency).not.toHaveBeenCalled();
  });
});

// ============================================================================
// useAgencyOptions Hook 測試
// ============================================================================

describe('useAgencyOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得機關選項', async () => {
    const mockOptions: AgencyOption[] = [
      createMockAgencyOption({ id: 1, agency_name: '桃園市政府' }),
      createMockAgencyOption({ id: 2, agency_name: '新北市政府' }),
    ];

    vi.mocked(agenciesApi.getAgencyOptions).mockResolvedValue(mockOptions);

    const { result } = renderHook(() => useAgencyOptions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(2);
  });
});

// ============================================================================
// useAgencyStatistics Hook 測試
// ============================================================================

describe('useAgencyStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得統計資料', async () => {
    const mockStats: AgencyStatistics = {
      total_agencies: 50,
      categories: [
        { category: '政府機關', count: 30, percentage: 60 },
        { category: '民間企業', count: 20, percentage: 40 },
      ],
    };

    vi.mocked(agenciesApi.getStatistics).mockResolvedValue(mockStats);

    const { result } = renderHook(() => useAgencyStatistics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.total_agencies).toBe(50);
  });
});

// ============================================================================
// Mutation Hooks 測試
// ============================================================================

describe('useCreateAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功建立機關', async () => {
    const newAgency = createMockAgency({
      id: 1,
      agency_name: '新機關',
      agency_code: 'NEW-001',
    });

    vi.mocked(agenciesApi.createAgency).mockResolvedValue(newAgency);

    const { result } = renderHook(() => useCreateAgency(), {
      wrapper: createWrapper(),
    });

    const createData: AgencyCreate = {
      agency_name: '新機關',
      agency_code: 'NEW-001',
    };

    await result.current.mutateAsync(createData);

    expect(agenciesApi.createAgency).toHaveBeenCalled();
  });
});

describe('useUpdateAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功更新機關', async () => {
    const updatedAgency = createMockAgency({
      id: 1,
      agency_name: '更新後名稱',
    });

    vi.mocked(agenciesApi.updateAgency).mockResolvedValue(updatedAgency);

    const { result } = renderHook(() => useUpdateAgency(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      agencyId: 1,
      data: { agency_name: '更新後名稱' },
    });

    expect(agenciesApi.updateAgency).toHaveBeenCalledWith(1, {
      agency_name: '更新後名稱',
    });
  });
});

describe('useDeleteAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功刪除機關', async () => {
    vi.mocked(agenciesApi.deleteAgency).mockResolvedValue(
      createMockDeleteResponse(1)
    );

    const { result } = renderHook(() => useDeleteAgency(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync(1);

    expect(agenciesApi.deleteAgency).toHaveBeenCalledWith(1);
  });
});

// ============================================================================
// useAgenciesPage Hook 測試
// ============================================================================

describe('useAgenciesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(agenciesApi.getAgencies).mockResolvedValue(
      createMockPaginatedResponse([
        createMockAgency({ id: 1, agency_name: '桃園市政府' }),
      ], { total: 1 })
    );

    vi.mocked(agenciesApi.getStatistics).mockResolvedValue({
      total_agencies: 50,
      categories: [{ category: '政府機關', count: 30, percentage: 60 }],
    });

    vi.mocked(agenciesApi.createAgency).mockResolvedValue(
      createMockAgency({ id: 1, agency_name: '新機關' })
    );
  });

  it('應該整合多個查詢結果', async () => {
    const { result } = renderHook(() => useAgenciesPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.agencies).toHaveLength(1);
    expect(result.current.statistics?.total_agencies).toBe(50);
  });

  it('應該提供操作方法', async () => {
    const { result } = renderHook(() => useAgenciesPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(typeof result.current.createAgency).toBe('function');
    expect(typeof result.current.updateAgency).toBe('function');
    expect(typeof result.current.deleteAgency).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
  });
});
