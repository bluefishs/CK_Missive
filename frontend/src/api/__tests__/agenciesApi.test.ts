/**
 * agenciesApi 單元測試
 * agenciesApi Unit Tests
 *
 * 測試機關單位管理 API 服務層方法
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/agenciesApi.test.ts
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
    AGENCIES: {
      LIST: '/agencies/list',
      CREATE: '/agencies',
      DETAIL: (id: number) => `/agencies/${id}/detail`,
      UPDATE: (id: number) => `/agencies/${id}/update`,
      DELETE: (id: number) => `/agencies/${id}/delete`,
      STATISTICS: '/agencies/statistics',
    },
  },
}));

import { agenciesApi } from '../agenciesApi';
import { apiClient, ApiException } from '../client';

// ============================================================================
// Mock 資料
// ============================================================================

const mockAgency = {
  id: 1,
  agency_name: '測試機關',
  agency_code: 'AG001',
  agency_type: '政府機關',
  address: '台北市中正區',
  phone: '02-12345678',
  email: 'agency@example.com',
  contact_person: '李四',
  notes: '備註',
  document_count: 10,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  success: true as const,
  items: [mockAgency],
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
// agenciesApi.getAgencies 測試
// ============================================================================

describe('agenciesApi.getAgencies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 postList 呼叫正確的端點', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await agenciesApi.getAgencies();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/agencies/list',
      expect.objectContaining({
        page: 1,
        limit: 20,
        include_stats: true,
        sort_by: 'agency_name',
        sort_order: 'asc',
      })
    );
  });

  it('應該正確傳遞搜尋和機關類型參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await agenciesApi.getAgencies({
      page: 2,
      limit: 10,
      search: '台北',
      agency_type: '政府機關',
      include_stats: false,
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/agencies/list',
      expect.objectContaining({
        page: 2,
        limit: 10,
        search: '台北',
        agency_type: '政府機關',
        include_stats: false,
        sort_by: 'agency_name',
        sort_order: 'asc',
      })
    );
  });

  it('應該正確傳遞排序參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await agenciesApi.getAgencies({
      sort_by: 'agency_code',
      sort_order: 'desc',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/agencies/list',
      expect.objectContaining({
        sort_by: 'agency_code',
        sort_order: 'desc',
      })
    );
  });

  it('不應該傳遞 undefined 的可選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await agenciesApi.getAgencies({ page: 1 });

    const calledParams = vi.mocked(apiClient.postList).mock.calls[0]![1] as Record<string, unknown>;
    expect(calledParams).not.toHaveProperty('search');
    expect(calledParams).not.toHaveProperty('agency_type');
  });

  it('當 postList 返回 404 時應該回退到 GET API（舊版格式）', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      agencies: [mockAgency],
      total: 1,
      returned: 1,
    };
    vi.mocked(apiClient.get).mockResolvedValue(legacyResponse);

    const result = await agenciesApi.getAgencies();

    expect(apiClient.get).toHaveBeenCalledWith(
      '/agencies',
      expect.objectContaining({
        params: expect.objectContaining({
          skip: 0,
          limit: 100,
          include_stats: true,
        }),
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
      agencies: [mockAgency],
      total: 1,
      returned: 1,
    };
    vi.mocked(apiClient.get).mockResolvedValue(legacyResponse);

    await agenciesApi.getAgencies({
      page: 3,
      limit: 10,
      search: '台北',
      include_stats: false,
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      '/agencies',
      expect.objectContaining({
        params: expect.objectContaining({
          skip: 20,
          limit: 10,
          include_stats: false,
          search: '台北',
        }),
      })
    );
  });

  it('當非 404 錯誤時應該拋出錯誤', async () => {
    const apiError = new ApiException('INTERNAL_ERROR', 'Internal Server Error', 500);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    await expect(agenciesApi.getAgencies()).rejects.toThrow('Internal Server Error');
  });
});

// ============================================================================
// agenciesApi.getAgency 測試
// ============================================================================

describe('agenciesApi.getAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫正確的端點取得單一機關', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockAgency);

    const result = await agenciesApi.getAgency(1);

    expect(apiClient.post).toHaveBeenCalledWith('/agencies/1/detail');
    expect(result).toEqual(mockAgency);
  });

  it('應該正確拼接 agencyId 到 URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockAgency);

    await agenciesApi.getAgency(55);

    expect(apiClient.post).toHaveBeenCalledWith('/agencies/55/detail');
  });
});

// ============================================================================
// agenciesApi.createAgency 測試
// ============================================================================

describe('agenciesApi.createAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫建立端點並傳遞資料', async () => {
    const createData = {
      agency_name: '新機關',
      agency_code: 'NEW001',
      agency_type: '政府機關',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockAgency, ...createData, id: 10 });

    const result = await agenciesApi.createAgency(createData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/agencies', createData);
    expect(result.agency_name).toBe('新機關');
  });
});

// ============================================================================
// agenciesApi.updateAgency 測試
// ============================================================================

describe('agenciesApi.updateAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫更新端點並傳遞資料', async () => {
    const updateData = { agency_name: '更新名稱', phone: '02-99999999' };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockAgency, ...updateData });

    const result = await agenciesApi.updateAgency(1, updateData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/agencies/1/update', updateData);
    expect(result.agency_name).toBe('更新名稱');
    expect(result.phone).toBe('02-99999999');
  });
});

// ============================================================================
// agenciesApi.deleteAgency 測試
// ============================================================================

describe('agenciesApi.deleteAgency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫刪除端點', async () => {
    const deleteResponse = { success: true, message: '刪除成功', deleted_id: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(deleteResponse);

    const result = await agenciesApi.deleteAgency(1);

    expect(apiClient.post).toHaveBeenCalledWith('/agencies/1/delete');
    expect(result.success).toBe(true);
  });
});

// ============================================================================
// agenciesApi.getStatistics 測試
// ============================================================================

describe('agenciesApi.getStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中取得統計資料', async () => {
    const mockStats = {
      total_agencies: 30,
      category_stats: [
        { agency_type: '政府機關', count: 15 },
        { agency_type: '公營事業', count: 10 },
        { agency_type: '其他', count: 5 },
      ],
    };

    vi.mocked(apiClient.post).mockResolvedValue(mockStats);

    const result = await agenciesApi.getStatistics();

    expect(apiClient.post).toHaveBeenCalledWith('/agencies/statistics');
    expect(result.total_agencies).toBe(30);
    expect((result as any).category_stats).toHaveLength(3);
  });
});

// ============================================================================
// agenciesApi.getAgencyOptions 測試
// ============================================================================

describe('agenciesApi.getAgencyOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從機關列表轉換為下拉選項格式', async () => {
    const agencies = [
      { ...mockAgency, id: 1, agency_name: '機關A', agency_code: 'A001' },
      { ...mockAgency, id: 2, agency_name: '機關B', agency_code: undefined },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: agencies,
      pagination: { ...mockPaginatedResponse.pagination, total: 2 },
    });

    const result = await agenciesApi.getAgencyOptions();

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ id: 1, agency_name: '機關A', agency_code: 'A001' });
    // agency_code 為 undefined 時不應包含在選項中
    expect(result[1]).toEqual({ id: 2, agency_name: '機關B' });
  });

  it('應該使用 limit 100 且 include_stats 為 false', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await agenciesApi.getAgencyOptions();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/agencies/list',
      expect.objectContaining({
        limit: 100,
        include_stats: false,
      })
    );
  });
});

// ============================================================================
// agenciesApi.searchAgencies 測試
// ============================================================================

describe('agenciesApi.searchAgencies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用關鍵字搜尋並返回機關列表', async () => {
    const searchResults = [
      { ...mockAgency, id: 1, agency_name: '台北市政府' },
      { ...mockAgency, id: 2, agency_name: '台北市議會' },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: searchResults,
    });

    const result = await agenciesApi.searchAgencies('台北', 5);

    expect(result).toHaveLength(2);
    expect(result[0]?.agency_name).toBe('台北市政府');
  });

  it('應該使用預設 limit 10', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await agenciesApi.searchAgencies('台北');

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/agencies/list',
      expect.objectContaining({
        search: '台北',
        limit: 10,
      })
    );
  });
});
