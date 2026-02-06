/**
 * useTaoyuanProjects Hook 單元測試
 * useTaoyuanProjects Hook Unit Tests
 *
 * 測試桃園派工專案 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useTaoyuanProjects
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { TaoyuanProject, TaoyuanProjectListResponse, PaginationMeta } from '../../types/api';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的桃園專案 Mock 資料 */
const createMockTaoyuanProject = (overrides: Partial<TaoyuanProject> = {}): TaoyuanProject => ({
  id: 1,
  project_name: '測試工程',
  contract_project_id: 1,
  sequence_no: 1,
  review_year: 2026,
  case_type: '市區道路',
  district: '桃園區',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

/** 建立桃園專案列表回應 Mock 資料 */
const createMockProjectListResponse = (
  items: TaoyuanProject[],
  paginationOverrides: Partial<PaginationMeta> = {}
): TaoyuanProjectListResponse => ({
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

// Mock taoyuanDispatchApi
vi.mock('../../api/taoyuanDispatchApi', () => ({
  taoyuanProjectsApi: {
    getList: vi.fn(),
    getDetail: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

// 引入被測試的 hooks
import {
  useTaoyuanProjects,
  useTaoyuanProject,
} from '../../hooks/business/useTaoyuanProjects';

import { taoyuanProjectsApi } from '../../api/taoyuanDispatchApi';

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
// useTaoyuanProjects Hook 測試
// ============================================================================

describe('useTaoyuanProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得桃園專案列表', async () => {
    const mockResponse = createMockProjectListResponse([
      createMockTaoyuanProject({ id: 1, project_name: '中正路拓寬工程', district: '桃園區' }),
      createMockTaoyuanProject({ id: 2, project_name: '中華路排水改善', district: '中壢區' }),
    ], { total: 2 });

    vi.mocked(taoyuanProjectsApi.getList).mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () => useTaoyuanProjects({ skip: 0, limit: 20 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(2);
    expect(result.current.projects[0]?.project_name).toBe('中正路拓寬工程');
    expect(result.current.total).toBe(2);
  });

  it('應該正確傳遞篩選參數', async () => {
    vi.mocked(taoyuanProjectsApi.getList).mockResolvedValue(
      createMockProjectListResponse([], { total: 0, total_pages: 0 })
    );

    const params = {
      skip: 0,
      limit: 10,
      search: '桃園',
      district: '桃園區',
      review_year: 2026,
      case_type: '市區道路',
    };

    renderHook(() => useTaoyuanProjects(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(taoyuanProjectsApi.getList).toHaveBeenCalledWith(params);
    });
  });

  it('應該處理空結果', async () => {
    vi.mocked(taoyuanProjectsApi.getList).mockResolvedValue(
      createMockProjectListResponse([], { total: 0, total_pages: 0 })
    );

    const { result } = renderHook(
      () => useTaoyuanProjects({ skip: 0, limit: 20 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(0);
    expect(result.current.total).toBe(0);
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('伺服器連線失敗');
    vi.mocked(taoyuanProjectsApi.getList).mockRejectedValue(error);

    const { result } = renderHook(
      () => useTaoyuanProjects({ skip: 0, limit: 20 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });

    expect(result.current.error?.message).toBe('伺服器連線失敗');
  });
});

// ============================================================================
// useTaoyuanProject Hook 測試
// ============================================================================

describe('useTaoyuanProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得單一桃園專案', async () => {
    const mockProject = createMockTaoyuanProject({
      id: 1,
      project_name: '中正路拓寬工程',
      district: '桃園區',
      review_year: 2026,
      case_type: '市區道路',
    });

    vi.mocked(taoyuanProjectsApi.getDetail).mockResolvedValue(mockProject);

    const { result } = renderHook(() => useTaoyuanProject(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.project?.project_name).toBe('中正路拓寬工程');
    expect(result.current.project?.district).toBe('桃園區');
  });

  it('當 projectId 為 undefined 時不應該發送請求', async () => {
    const { result } = renderHook(() => useTaoyuanProject(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(taoyuanProjectsApi.getDetail).not.toHaveBeenCalled();
  });
});
