/**
 * useProjects Hook 單元測試
 * useProjects Hook Unit Tests
 *
 * 測試專案管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useProjects
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Project } from '../../types/api';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的專案 Mock 資料 */
const createMockProject = (overrides: Partial<Project> = {}): Project => ({
  id: 1,
  name: '測試專案',
  project_code: 'PRJ-001',
  status: '進行中',
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

// Mock projectsApi
vi.mock('../../api/projectsApi', () => ({
  projectsApi: {
    getProjects: vi.fn(),
    getProject: vi.fn(),
    getProjectOptions: vi.fn(),
    getStatistics: vi.fn(),
    getYearOptions: vi.fn(),
    getCategoryOptions: vi.fn(),
    getStatusOptions: vi.fn(),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}));

// Mock queryConfig
vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    projects: {
      all: ['projects'],
      list: (params: Record<string, unknown>) => ['projects', 'list', params],
      detail: (id: number) => ['projects', 'detail', id],
      statistics: ['projects', 'statistics'],
    },
  },
  defaultQueryOptions: {
    list: { staleTime: 5000 },
    detail: { staleTime: 10000 },
    statistics: { staleTime: 30000 },
    dropdown: { staleTime: 60000 },
  },
}));

// 引入被測試的 hooks
import {
  useProjects,
  useProject,
  useProjectStatistics,
  useProjectOptions,
  useProjectYearOptions,
  useProjectCategoryOptions,
  useProjectStatusOptions,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  useProjectsPage,
} from '../../hooks/business/useProjects';

import { projectsApi } from '../../api/projectsApi';

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
// useProjects Hook 測試
// ============================================================================

describe('useProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得專案列表', async () => {
    const mockResponse = createMockPaginatedResponse([
      createMockProject({ id: 1, name: '專案A', project_code: 'PRJ-001' }),
      createMockProject({ id: 2, name: '專案B', project_code: 'PRJ-002' }),
    ], { total: 2 });

    vi.mocked(projectsApi.getProjects).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items?.[0]?.name).toBe('專案A');
  });

  it('應該正確傳遞查詢參數', async () => {
    vi.mocked(projectsApi.getProjects).mockResolvedValue(
      createMockPaginatedResponse<Project>([], { total: 0 })
    );

    const params = {
      page: 2,
      limit: 10,
      keyword: '桃園',
      status: '進行中',
      year: 2026,
    };

    renderHook(() => useProjects(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(projectsApi.getProjects).toHaveBeenCalledWith(params);
    });
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('API Error');
    vi.mocked(projectsApi.getProjects).mockRejectedValue(error);

    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

// ============================================================================
// useProject Hook 測試
// ============================================================================

describe('useProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得單一專案', async () => {
    const mockProject = createMockProject({
      id: 1,
      name: '測試專案',
      project_code: 'PRJ-001',
      status: '進行中',
    });

    vi.mocked(projectsApi.getProject).mockResolvedValue(mockProject);

    const { result } = renderHook(() => useProject(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.name).toBe('測試專案');
  });

  it('當 projectId 為 null 時不應該發送請求', async () => {
    const { result } = renderHook(() => useProject(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(projectsApi.getProject).not.toHaveBeenCalled();
  });

  it('當 projectId 為 undefined 時不應該發送請求', async () => {
    const { result } = renderHook(() => useProject(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(projectsApi.getProject).not.toHaveBeenCalled();
  });
});

// ============================================================================
// useProjectStatistics Hook 測試
// ============================================================================

describe('useProjectStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得統計資料', async () => {
    const mockStats = {
      total: 100,
      by_status: {
        '進行中': 50,
        '已完成': 40,
        '暫停': 10,
      },
      by_year: {
        '2026': 30,
        '2025': 70,
      },
    };

    vi.mocked(projectsApi.getStatistics).mockResolvedValue(mockStats);

    const { result } = renderHook(() => useProjectStatistics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.total).toBe(100);
  });
});

// ============================================================================
// useProjectOptions Hook 測試
// ============================================================================

describe('useProjectOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得專案選項', async () => {
    const mockOptions = [
      { id: 1, name: '專案A' },
      { id: 2, name: '專案B' },
    ];

    vi.mocked(projectsApi.getProjectOptions).mockResolvedValue(mockOptions);

    const { result } = renderHook(() => useProjectOptions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(2);
  });

  it('應該支援年度篩選', async () => {
    vi.mocked(projectsApi.getProjectOptions).mockResolvedValue([]);

    renderHook(() => useProjectOptions(2026), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(projectsApi.getProjectOptions).toHaveBeenCalledWith(2026);
    });
  });
});

// ============================================================================
// useProjectYearOptions Hook 測試
// ============================================================================

describe('useProjectYearOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得年度選項', async () => {
    const mockYears = [2026, 2025, 2024];

    vi.mocked(projectsApi.getYearOptions).mockResolvedValue(mockYears);

    const { result } = renderHook(() => useProjectYearOptions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([2026, 2025, 2024]);
  });
});

// ============================================================================
// Mutation Hooks 測試
// ============================================================================

describe('useCreateProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功建立專案', async () => {
    const newProject = createMockProject({
      id: 1,
      name: '新專案',
      project_code: 'NEW-001',
    });

    vi.mocked(projectsApi.createProject).mockResolvedValue(newProject);

    const { result } = renderHook(() => useCreateProject(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      name: '新專案',
      project_code: 'NEW-001',
    });

    expect(projectsApi.createProject).toHaveBeenCalled();
  });
});

describe('useUpdateProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功更新專案', async () => {
    const updatedProject = createMockProject({
      id: 1,
      name: '更新後名稱',
    });

    vi.mocked(projectsApi.updateProject).mockResolvedValue(updatedProject);

    const { result } = renderHook(() => useUpdateProject(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      projectId: 1,
      data: { name: '更新後名稱' },
    });

    expect(projectsApi.updateProject).toHaveBeenCalledWith(1, {
      name: '更新後名稱',
    });
  });
});

describe('useDeleteProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功刪除專案', async () => {
    vi.mocked(projectsApi.deleteProject).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useDeleteProject(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync(1);

    expect(projectsApi.deleteProject).toHaveBeenCalledWith(1);
  });
});

// ============================================================================
// useProjectsPage Hook 測試
// ============================================================================

describe('useProjectsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(projectsApi.getProjects).mockResolvedValue(
      createMockPaginatedResponse([
        createMockProject({ id: 1, name: '專案A' }),
      ], { total: 1 })
    );

    vi.mocked(projectsApi.getStatistics).mockResolvedValue({
      total: 100,
      by_status: { '進行中': 50 },
    });

    vi.mocked(projectsApi.getYearOptions).mockResolvedValue([2026, 2025]);
    vi.mocked(projectsApi.getCategoryOptions).mockResolvedValue(['類別A', '類別B']);
    vi.mocked(projectsApi.getStatusOptions).mockResolvedValue(['進行中', '已完成']);

    vi.mocked(projectsApi.createProject).mockResolvedValue(
      createMockProject({ id: 1, name: '新專案' })
    );
  });

  it('應該整合多個查詢結果', async () => {
    const { result } = renderHook(() => useProjectsPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(1);
    expect(result.current.statistics?.total).toBe(100);
    expect(result.current.availableYears).toEqual([2026, 2025]);
    expect(result.current.availableCategories).toEqual(['類別A', '類別B']);
    expect(result.current.availableStatuses).toEqual(['進行中', '已完成']);
  });

  it('應該提供操作方法', async () => {
    const { result } = renderHook(() => useProjectsPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(typeof result.current.createProject).toBe('function');
    expect(typeof result.current.updateProject).toBe('function');
    expect(typeof result.current.deleteProject).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
  });

  it('應該正確傳遞篩選參數', async () => {
    const params = { keyword: '測試', status: '進行中' };

    renderHook(() => useProjectsPage(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(projectsApi.getProjects).toHaveBeenCalledWith(params);
    });
  });
});
