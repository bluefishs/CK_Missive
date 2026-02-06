/**
 * vendorsApi 單元測試
 * vendorsApi Unit Tests
 *
 * 測試廠商管理 API 服務層方法
 *
 * 執行方式:
 *   cd frontend && npm run test -- vendorsApi
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
    VENDORS: {
      LIST: '/vendors/list',
      CREATE: '/vendors',
      DETAIL: (id: number) => `/vendors/${id}/detail`,
      UPDATE: (id: number) => `/vendors/${id}/update`,
      DELETE: (id: number) => `/vendors/${id}/delete`,
      STATISTICS: '/vendors/statistics',
    },
  },
}));

import { vendorsApi } from '../vendorsApi';
import { apiClient, ApiException } from '../client';

// ============================================================================
// Mock 資料
// ============================================================================

const mockVendor = {
  id: 1,
  vendor_name: '測試廠商',
  vendor_code: 'V001',
  contact_person: '張三',
  phone: '02-12345678',
  email: 'test@example.com',
  address: '台北市信義區',
  business_type: '測量業務',
  rating: 4.5,
  notes: '備註',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  success: true as const,
  items: [mockVendor],
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
// vendorsApi.getVendors 測試
// ============================================================================

describe('vendorsApi.getVendors', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 postList 呼叫正確的端點', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await vendorsApi.getVendors();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/vendors/list',
      expect.objectContaining({
        page: 1,
        limit: 20,
        sort_by: 'vendor_name',
        sort_order: 'asc',
      })
    );
  });

  it('應該正確傳遞搜尋和業種參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await vendorsApi.getVendors({
      page: 2,
      limit: 10,
      search: '測量',
      business_type: '測量業務',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/vendors/list',
      expect.objectContaining({
        page: 2,
        limit: 10,
        search: '測量',
        business_type: '測量業務',
        sort_by: 'vendor_name',
        sort_order: 'asc',
      })
    );
  });

  it('當 postList 返回 404 時應該回退到 GET API', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      items: [mockVendor],
      total: 1,
      page: 1,
      limit: 100,
    };
    vi.mocked(apiClient.get).mockResolvedValue(legacyResponse);

    const result = await vendorsApi.getVendors();

    expect(apiClient.get).toHaveBeenCalledWith(
      '/vendors',
      expect.objectContaining({
        params: expect.objectContaining({
          skip: 0,
          limit: 100,
        }),
      })
    );
    // 應回傳正規化後的分頁回應
    expect(result).toHaveProperty('items');
    expect(result).toHaveProperty('pagination');
  });

  it('當非 404 錯誤時應該拋出錯誤', async () => {
    const apiError = new ApiException('INTERNAL_ERROR', 'Internal Server Error', 500);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    await expect(vendorsApi.getVendors()).rejects.toThrow('Internal Server Error');
  });
});

// ============================================================================
// vendorsApi.getVendor 測試
// ============================================================================

describe('vendorsApi.getVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫正確的端點取得單一廠商', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockVendor);

    const result = await vendorsApi.getVendor(1);

    expect(apiClient.post).toHaveBeenCalledWith('/vendors/1/detail');
    expect(result).toEqual(mockVendor);
  });

  it('應該正確拼接 vendorId 到 URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockVendor);

    await vendorsApi.getVendor(99);

    expect(apiClient.post).toHaveBeenCalledWith('/vendors/99/detail');
  });
});

// ============================================================================
// vendorsApi.createVendor 測試
// ============================================================================

describe('vendorsApi.createVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫建立端點並傳遞資料', async () => {
    const createData = {
      vendor_name: '新廠商',
      vendor_code: 'NEW001',
      business_type: '查估業務',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockVendor, ...createData, id: 10 });

    const result = await vendorsApi.createVendor(createData);

    expect(apiClient.post).toHaveBeenCalledWith('/vendors', createData);
    expect(result.vendor_name).toBe('新廠商');
  });
});

// ============================================================================
// vendorsApi.updateVendor 測試
// ============================================================================

describe('vendorsApi.updateVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫更新端點並傳遞資料', async () => {
    const updateData = { vendor_name: '更新名稱', rating: 5 };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockVendor, ...updateData });

    const result = await vendorsApi.updateVendor(1, updateData);

    expect(apiClient.post).toHaveBeenCalledWith('/vendors/1/update', updateData);
    expect(result.vendor_name).toBe('更新名稱');
    expect(result.rating).toBe(5);
  });
});

// ============================================================================
// vendorsApi.deleteVendor 測試
// ============================================================================

describe('vendorsApi.deleteVendor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫刪除端點', async () => {
    const deleteResponse = { success: true, message: '刪除成功', deleted_id: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(deleteResponse);

    const result = await vendorsApi.deleteVendor(1);

    expect(apiClient.post).toHaveBeenCalledWith('/vendors/1/delete');
    expect(result.success).toBe(true);
  });
});

// ============================================================================
// vendorsApi.getStatistics 測試
// ============================================================================

describe('vendorsApi.getStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中提取 data 欄位', async () => {
    const mockStats = {
      total_vendors: 50,
      business_types: [
        { business_type: '測量業務', count: 20 },
        { business_type: '查估業務', count: 15 },
        { business_type: '系統業務', count: 10 },
        { business_type: '其他類別', count: 5 },
      ],
      average_rating: 4.2,
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      data: mockStats,
    });

    const result = await vendorsApi.getStatistics();

    expect(apiClient.post).toHaveBeenCalledWith('/vendors/statistics');
    expect(result.total_vendors).toBe(50);
    expect(result.business_types).toHaveLength(4);
    expect(result.average_rating).toBe(4.2);
  });
});

// ============================================================================
// vendorsApi.getVendorOptions 測試
// ============================================================================

describe('vendorsApi.getVendorOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從廠商列表轉換為下拉選項格式', async () => {
    const vendors = [
      { ...mockVendor, id: 1, vendor_name: '廠商A', vendor_code: 'A001' },
      { ...mockVendor, id: 2, vendor_name: '廠商B', vendor_code: undefined },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: vendors,
      pagination: { ...mockPaginatedResponse.pagination, total: 2 },
    });

    const result = await vendorsApi.getVendorOptions();

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ id: 1, vendor_name: '廠商A', vendor_code: 'A001' });
    // vendor_code 為 undefined 時不應包含在選項中
    expect(result[1]).toEqual({ id: 2, vendor_name: '廠商B' });
  });
});

// ============================================================================
// vendorsApi.searchVendors 測試
// ============================================================================

describe('vendorsApi.searchVendors', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用關鍵字搜尋並返回廠商列表', async () => {
    const searchResults = [
      { ...mockVendor, id: 1, vendor_name: '測量廠商A' },
      { ...mockVendor, id: 2, vendor_name: '測量廠商B' },
    ];

    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: searchResults,
    });

    const result = await vendorsApi.searchVendors('測量', 5);

    expect(result).toHaveLength(2);
    expect(result[0]?.vendor_name).toBe('測量廠商A');
  });
});

// ============================================================================
// vendorsApi.batchDelete 測試
// ============================================================================

describe('vendorsApi.batchDelete', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該批次刪除廠商並回報結果', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, message: '刪除成功', deleted_id: 1 });

    const result = await vendorsApi.batchDelete([1, 2, 3]);

    expect(apiClient.post).toHaveBeenCalledTimes(3);
    expect(result.success_count).toBe(3);
    expect(result.failed_count).toBe(0);
  });

  it('應該正確處理部分刪除失敗', async () => {
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({ success: true, message: '刪除成功', deleted_id: 1 })
      .mockRejectedValueOnce(new Error('刪除失敗'))
      .mockResolvedValueOnce({ success: true, message: '刪除成功', deleted_id: 3 });

    const result = await vendorsApi.batchDelete([1, 2, 3]);

    expect(result.success_count).toBe(2);
    expect(result.failed_count).toBe(1);
    expect(result.failed_ids).toEqual([2]);
    expect(result.errors).toHaveLength(1);
  });
});
