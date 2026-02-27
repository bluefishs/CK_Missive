/**
 * projectsApi 單元測試
 * projectsApi Unit Tests
 *
 * 測試專案管理 API 服務層方法
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/projectsApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
    postList: vi.fn(),
  },
  ApiException: class ApiException extends Error {
    code: string;
    statusCode: number;
    constructor(code: string, message: string, statusCode: number = 500) {
      super(message);
      this.code = code;
      this.statusCode = statusCode;
      this.name = 'ApiException';
    }
  },
}));

// Mock endpoints
vi.mock('../endpoints', () => ({
  API_ENDPOINTS: {
    PROJECTS: {
      LIST: '/projects/list',
      CREATE: '/projects',
      DETAIL: (id: number) => `/projects/${id}/detail`,
      UPDATE: (id: number) => `/projects/${id}/update`,
      DELETE: (id: number) => `/projects/${id}/delete`,
      STATISTICS: '/projects/statistics',
      YEARS: '/projects/years',
      CATEGORIES: '/projects/categories',
      STATUSES: '/projects/statuses',
    },
  },
}));

import { projectsApi } from '../projectsApi';
import { apiClient, ApiException } from '../client';

// ============================================================================
// Mock 資料
// ============================================================================

const mockProject = {
  id: 1,
  project_name: '測試專案',
  project_code: 'P2026-001',
  year: 2026,
  category: '測量',
  status: '進行中',
  contract_amount: 1000000,
  start_date: '2026-01-01',
  end_date: '2026-12-31',
  notes: '備註',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  success: true as const,
  items: [mockProject],
  pagination: {
    total: 1,
    page: 1,
    limit: 20,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  },
};

// ============================================================================
// projectsApi.getProjects 測試
// ============================================================================

describe('projectsApi.getProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 postList 呼叫正確的端點', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.getProjects();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        page: 1,
        limit: 20,
        sort_by: 'year',
        sort_order: 'desc',
      })
    );
  });

  it('應該正確傳遞搜尋和篩選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.getProjects({
      page: 2,
      limit: 10,
      search: '測量',
      year: 2026,
      category: '測量',
      status: '進行中',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        page: 2,
        limit: 10,
        search: '測量',
        year: 2026,
        category: '測量',
        status: '進行中',
        sort_by: 'year',
        sort_order: 'desc',
      })
    );
  });

  it('應該正確傳遞排序參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.getProjects({
      sort_by: 'project_name',
      sort_order: 'asc',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        sort_by: 'project_name',
        sort_order: 'asc',
      })
    );
  });

  it('不應該傳遞 undefined 的可選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.getProjects({ page: 1 });

    const calledParams = vi.mocked(apiClient.postList).mock.calls[0]![1] as Record<string, unknown>;
    expect(calledParams).not.toHaveProperty('search');
    expect(calledParams).not.toHaveProperty('year');
    expect(calledParams).not.toHaveProperty('category');
    expect(calledParams).not.toHaveProperty('status');
  });

  it('當 postList 返回 404 時應該回退到 POST API（舊版格式）', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      projects: [mockProject],
      total: 1,
      skip: 0,
      limit: 100,
    };
    vi.mocked(apiClient.post).mockResolvedValue(legacyResponse);

    const result = await projectsApi.getProjects();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        skip: 0,
        limit: 100,
      })
    );
    // 應回傳正規化後的分頁回應
    expect(result).toHaveProperty('items');
    expect(result).toHaveProperty('pagination');
  });

  it('當 postList 返回 404 且帶有搜尋參數時回退應傳遞搜尋參數', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      projects: [mockProject],
      total: 1,
      skip: 0,
      limit: 100,
    };
    vi.mocked(apiClient.post).mockResolvedValue(legacyResponse);

    await projectsApi.getProjects({
      page: 2,
      limit: 10,
      search: '測量',
      year: 2026,
      category: '測量',
      status: '進行中',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        skip: 10,
        limit: 10,
        search: '測量',
        year: 2026,
        category: '測量',
        status: '進行中',
      })
    );
  });

  it('當非 404 錯誤時應該拋出錯誤', async () => {
    const apiError = new ApiException('INTERNAL_ERROR', 'Internal Server Error', 500);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    await expect(projectsApi.getProjects()).rejects.toThrow('Internal Server Error');
  });
});

// ============================================================================
// projectsApi.getProject 測試
// ============================================================================

describe('projectsApi.getProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫正確的端點取得單一專案', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockProject);

    const result = await projectsApi.getProject(1);

    expect(apiClient.post).toHaveBeenCalledWith('/projects/1/detail');
    expect(result).toEqual(mockProject);
  });

  it('應該正確拼接 projectId 到 URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockProject);

    await projectsApi.getProject(99);

    expect(apiClient.post).toHaveBeenCalledWith('/projects/99/detail');
  });
});

// ============================================================================
// projectsApi.createProject 測試
// ============================================================================

describe('projectsApi.createProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫建立端點並傳遞資料', async () => {
    const createData = {
      project_name: '新專案',
      project_code: 'P2026-002',
      year: 2026,
      category: '查估',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockProject, ...createData, id: 10 });

    const result = await projectsApi.createProject(createData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/projects', createData);
    expect(result.project_name).toBe('新專案');
  });
});

// ============================================================================
// projectsApi.updateProject 測試
// ============================================================================

describe('projectsApi.updateProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫更新端點並傳遞資料', async () => {
    const updateData = { project_name: '更新名稱', status: '已完成' };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockProject, ...updateData });

    const result = await projectsApi.updateProject(1, updateData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/projects/1/update', updateData);
    expect(result.project_name).toBe('更新名稱');
    expect(result.status).toBe('已完成');
  });
});

// ============================================================================
// projectsApi.deleteProject 測試
// ============================================================================

describe('projectsApi.deleteProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫刪除端點', async () => {
    const deleteResponse = { success: true, message: '刪除成功', deleted_id: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(deleteResponse);

    const result = await projectsApi.deleteProject(1);

    expect(apiClient.post).toHaveBeenCalledWith('/projects/1/delete');
    expect(result.success).toBe(true);
  });
});

// ============================================================================
// projectsApi.getStatistics 測試
// ============================================================================

describe('projectsApi.getStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中提取 data 欄位', async () => {
    const mockStats = {
      total_projects: 50,
      status_breakdown: [
        { status: '進行中', count: 20 },
        { status: '已完成', count: 30 },
      ],
      year_breakdown: [
        { year: 2025, count: 25 },
        { year: 2026, count: 25 },
      ],
      average_contract_amount: 500000,
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockStats,
    });

    const result = await projectsApi.getStatistics();

    expect(apiClient.post).toHaveBeenCalledWith('/projects/statistics');
    expect(result.total_projects).toBe(50);
    expect(result.status_breakdown).toHaveLength(2);
    expect(result.year_breakdown).toHaveLength(2);
    expect(result.average_contract_amount).toBe(500000);
  });

  it('當 data 為 undefined 時應該返回預設值', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: undefined,
    });

    const result = await projectsApi.getStatistics();

    expect(result).toEqual({
      total_projects: 0,
      status_breakdown: [],
      year_breakdown: [],
      average_contract_amount: 0,
    });
  });
});

// ============================================================================
// projectsApi.getYearOptions 測試
// ============================================================================

describe('projectsApi.getYearOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中提取年度列表', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { years: [2024, 2025, 2026] },
    });

    const result = await projectsApi.getYearOptions();

    expect(apiClient.post).toHaveBeenCalledWith('/projects/years');
    expect(result).toEqual([2024, 2025, 2026]);
  });

  it('當 data 為 undefined 時應該返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: undefined,
    });

    const result = await projectsApi.getYearOptions();

    expect(result).toEqual([]);
  });
});

// ============================================================================
// projectsApi.getCategoryOptions 測試
// ============================================================================

describe('projectsApi.getCategoryOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中提取類別列表', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { categories: ['測量', '查估', '鑑價'] },
    });

    const result = await projectsApi.getCategoryOptions();

    expect(apiClient.post).toHaveBeenCalledWith('/projects/categories');
    expect(result).toEqual(['測量', '查估', '鑑價']);
  });

  it('當 data 為 undefined 時應該返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: undefined,
    });

    const result = await projectsApi.getCategoryOptions();

    expect(result).toEqual([]);
  });
});

// ============================================================================
// projectsApi.getStatusOptions 測試
// ============================================================================

describe('projectsApi.getStatusOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中提取狀態列表', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: { statuses: ['進行中', '已完成', '已暫停'] },
    });

    const result = await projectsApi.getStatusOptions();

    expect(apiClient.post).toHaveBeenCalledWith('/projects/statuses');
    expect(result).toEqual(['進行中', '已完成', '已暫停']);
  });

  it('當 data 為 undefined 時應該返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: undefined,
    });

    const result = await projectsApi.getStatusOptions();

    expect(result).toEqual([]);
  });
});

// ============================================================================
// projectsApi.getProjectOptions 測試
// ============================================================================

describe('projectsApi.getProjectOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從專案列表轉換為下拉選項格式', async () => {
    const projects = [
      { ...mockProject, id: 1, project_name: '專案A', project_code: 'A001', year: 2026 },
      { ...mockProject, id: 2, project_name: '專案B', project_code: undefined, year: undefined },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: projects,
      pagination: { ...mockPaginatedResponse.pagination, total: 2 },
    });

    const result = await projectsApi.getProjectOptions();

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ id: 1, project_name: '專案A', project_code: 'A001', year: 2026 });
    // project_code 和 year 為 undefined 時不應包含在選項中
    expect(result[1]).toEqual({ id: 2, project_name: '專案B' });
  });

  it('應該使用 limit 100 來取得完整清單', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.getProjectOptions();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        limit: 100,
      })
    );
  });

  it('應該支援年度篩選', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.getProjectOptions(2026);

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        limit: 100,
        year: 2026,
      })
    );
  });
});

// ============================================================================
// projectsApi.searchProjects 測試
// ============================================================================

describe('projectsApi.searchProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用關鍵字搜尋並返回專案列表', async () => {
    const searchResults = [
      { ...mockProject, id: 1, project_name: '測量專案A' },
      { ...mockProject, id: 2, project_name: '測量專案B' },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: searchResults,
    });

    const result = await projectsApi.searchProjects('測量', 5);

    expect(result).toHaveLength(2);
    expect(result[0]?.project_name).toBe('測量專案A');
  });

  it('應該使用預設 limit 10', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await projectsApi.searchProjects('測量');

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/projects/list',
      expect.objectContaining({
        search: '測量',
        limit: 10,
      })
    );
  });
});
