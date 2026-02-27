/**
 * documentsApi 單元測試
 * documentsApi Unit Tests
 *
 * 測試公文管理 API 服務層方法
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/documentsApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock logger（需在 documentsApi import 前）
vi.mock('../../services/logger', () => ({
  logger: {
    log: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
    postList: vi.fn(),
    postForm: vi.fn(),
    downloadPost: vi.fn(),
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
    DOCUMENTS: {
      LIST: '/documents-enhanced/list',
      CREATE: '/documents-enhanced/create',
      DETAIL: (id: number) => `/documents-enhanced/${id}/detail`,
      UPDATE: (id: number) => `/documents-enhanced/${id}/update`,
      DELETE: (id: number) => `/documents-enhanced/${id}/delete`,
      STATISTICS: '/documents-enhanced/statistics',
      FILTERED_STATISTICS: '/documents-enhanced/filtered-statistics',
      YEARS: '/documents-enhanced/years',
      CONTRACT_PROJECTS_DROPDOWN: '/documents-enhanced/contract-projects-dropdown',
      AGENCIES_DROPDOWN: '/documents-enhanced/agencies-dropdown',
      BY_PROJECT: '/documents-enhanced/by-project',
      EXPORT: '/documents-enhanced/export',
      INTEGRATED_SEARCH: '/documents-enhanced/integrated-search',
      NEXT_SEND_NUMBER: '/documents-enhanced/next-send-number',
      TRENDS: '/documents-enhanced/trends',
      EFFICIENCY: '/documents-enhanced/efficiency',
      AUDIT_LOGS: '/documents-enhanced/audit-logs',
      AUDIT_HISTORY: (id: number) => `/documents-enhanced/${id}/audit-history`,
    },
    CSV_IMPORT: {
      UPLOAD_AND_IMPORT: '/csv-import/upload-and-import',
    },
  },
}));

import { documentsApi } from '../documentsApi';
import { apiClient, ApiException } from '../client';

// ============================================================================
// Mock 資料
// ============================================================================

const mockDocument = {
  id: 1,
  doc_number: '乾坤測字第1150000001號',
  doc_type: '收文',
  subject: '測試公文主旨',
  sender: '台北市政府',
  receiver: '乾坤測量公司',
  doc_date: '2026-01-15',
  status: '處理中',
  category: '一般',
  notes: '備註',
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
};

const mockPaginatedResponse = {
  success: true as const,
  items: [mockDocument],
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
// documentsApi.getDocuments 測試
// ============================================================================

describe('documentsApi.getDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 postList 呼叫正確的端點（無參數）', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments();

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        page: 1,
        limit: 20,
        sort_by: 'updated_at',
        sort_order: 'desc',
      })
    );
  });

  it('應該正確傳遞搜尋與篩選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments({
      page: 2,
      limit: 10,
      keyword: '測試',
      doc_type: '收文',
      year: 115,
      status: '處理中',
      sender: '台北市政府',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        page: 2,
        limit: 10,
        keyword: '測試',
        doc_type: '收文',
        year: 115,
        status: '處理中',
        sender: '台北市政府',
        sort_by: 'updated_at',
        sort_order: 'desc',
      })
    );
  });

  it('keyword 應優先於 search 參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments({
      search: '搜尋值',
      keyword: '關鍵字值',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        keyword: '關鍵字值',
      })
    );
  });

  it('應該正確傳遞 doc_number 為獨立篩選參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments({
      doc_number: '乾坤測字第115',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        doc_number: '乾坤測字第115',
      })
    );
  });

  it('年度字串值應轉為數字', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments({ year: '115' });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        year: 115,
      })
    );
  });

  it('日期篩選應支援 doc_date_from/doc_date_to 格式', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments({
      doc_date_from: '2026-01-01',
      doc_date_to: '2026-12-31',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        doc_date_from: '2026-01-01',
        doc_date_to: '2026-12-31',
      })
    );
  });

  it('日期篩選應支援 date_from/date_to 格式 (fallback)', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocuments({
      date_from: '2026-01-01',
      date_to: '2026-06-30',
    });

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        doc_date_from: '2026-01-01',
        doc_date_to: '2026-06-30',
      })
    );
  });

  it('當 postList 返回 404 時應該回退到 GET API', async () => {
    const apiError = new ApiException('NOT_FOUND', 'Not Found', 404);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    const legacyResponse = {
      items: [mockDocument],
      total: 1,
      page: 1,
      limit: 100,
      total_pages: 1,
    };
    vi.mocked(apiClient.get).mockResolvedValue(legacyResponse);

    const result = await documentsApi.getDocuments();

    expect(apiClient.get).toHaveBeenCalledWith(
      '/documents-enhanced/integrated-search',
      expect.objectContaining({
        params: expect.objectContaining({
          skip: 0,
          limit: 100,
        }),
      })
    );
    expect(result).toHaveProperty('items');
    expect(result).toHaveProperty('pagination');
  });

  it('當非 404 錯誤時應該拋出錯誤', async () => {
    const apiError = new ApiException('INTERNAL_ERROR', 'Internal Server Error', 500);
    vi.mocked(apiClient.postList).mockRejectedValue(apiError);

    await expect(documentsApi.getDocuments()).rejects.toThrow('Internal Server Error');
  });
});

// ============================================================================
// documentsApi.getDocument 測試
// ============================================================================

describe('documentsApi.getDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫正確的詳情端點', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockDocument);

    const result = await documentsApi.getDocument(1);

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/1/detail');
    expect(result).toEqual(mockDocument);
  });

  it('應該正確拼接 documentId 到 URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockDocument);

    await documentsApi.getDocument(99);

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/99/detail');
  });
});

// ============================================================================
// documentsApi.createDocument 測試
// ============================================================================

describe('documentsApi.createDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫建立端點並傳遞資料', async () => {
    const createData = {
      doc_number: '乾坤測字第1150000010號',
      doc_type: '發文' as const,
      subject: '新公文',
      sender: '乾坤測量',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockDocument, ...createData, id: 10 });

    const result = await documentsApi.createDocument(createData);

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/create', createData);
    expect(result.subject).toBe('新公文');
  });
});

// ============================================================================
// documentsApi.updateDocument 測試
// ============================================================================

describe('documentsApi.updateDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫更新端點並傳遞資料', async () => {
    const updateData = { subject: '更新後主旨', status: '已結案' };

    vi.mocked(apiClient.post).mockResolvedValue({ ...mockDocument, ...updateData });

    const result = await documentsApi.updateDocument(1, updateData);

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/1/update', updateData);
    expect(result.subject).toBe('更新後主旨');
    expect(result.status).toBe('已結案');
  });
});

// ============================================================================
// documentsApi.deleteDocument 測試
// ============================================================================

describe('documentsApi.deleteDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 post 呼叫刪除端點', async () => {
    const deleteResponse = { success: true, message: '刪除成功', deleted_id: 1 };
    vi.mocked(apiClient.post).mockResolvedValue(deleteResponse);

    const result = await documentsApi.deleteDocument(1);

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/1/delete');
    expect(result.success).toBe(true);
  });
});

// ============================================================================
// documentsApi.getStatistics 測試
// ============================================================================

describe('documentsApi.getStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫統計端點並返回結果', async () => {
    const mockStats = {
      total: 100,
      send_count: 40,
      receive_count: 60,
      pending_count: 15,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockStats);

    const result = await documentsApi.getStatistics();

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/statistics');
    expect(result.total).toBe(100);
  });
});

// ============================================================================
// documentsApi.getNextSendNumber 測試
// ============================================================================

describe('documentsApi.getNextSendNumber', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該傳遞 prefix 和 year 參數', async () => {
    const mockResponse = {
      next_number: '乾坤測字第1150000002號',
      prefix: '乾坤測字第',
      year: 2026,
      sequence: 2,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await documentsApi.getNextSendNumber('乾坤測字第', 2026);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/next-send-number',
      { prefix: '乾坤測字第', year: 2026 }
    );
    expect((result as any).next_number).toBe('乾坤測字第1150000002號');
  });

  it('不傳參數時應該發送 undefined', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ next_number: '乾坤測字第1150000001號' });

    await documentsApi.getNextSendNumber();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/next-send-number',
      { prefix: undefined, year: undefined }
    );
  });
});

// ============================================================================
// documentsApi.getFilteredStatistics 測試
// ============================================================================

describe('documentsApi.getFilteredStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該傳遞篩選參數並返回統計結果', async () => {
    const mockResponse = {
      success: true,
      total: 30,
      send_count: 10,
      receive_count: 20,
      filters_applied: true,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await documentsApi.getFilteredStatistics({
      doc_type: '收文',
      year: 115,
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/filtered-statistics',
      expect.objectContaining({
        doc_type: '收文',
        year: 115,
      })
    );
    expect(result.filters_applied).toBe(true);
    expect(result.total).toBe(30);
  });

  it('keyword 應優先於 search', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, total: 0, send_count: 0, receive_count: 0, filters_applied: true });

    await documentsApi.getFilteredStatistics({
      search: '搜尋',
      keyword: '關鍵字',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/filtered-statistics',
      expect.objectContaining({
        keyword: '關鍵字',
      })
    );
  });
});

// ============================================================================
// documentsApi.getYearOptions 測試
// ============================================================================

describe('documentsApi.getYearOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從回應中提取 years 陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ years: [113, 114, 115] });

    const result = await documentsApi.getYearOptions();

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/years');
    expect(result).toEqual([113, 114, 115]);
  });

  it('回應中沒有 years 時應返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    const result = await documentsApi.getYearOptions();

    expect(result).toEqual([]);
  });
});

// ============================================================================
// documentsApi.getContractProjectOptions 測試
// ============================================================================

describe('documentsApi.getContractProjectOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該傳遞搜尋和 limit 參數', async () => {
    const mockOptions = [
      { value: '1', label: '案件A' },
      { value: '2', label: '案件B' },
    ];
    vi.mocked(apiClient.post).mockResolvedValue({ options: mockOptions });

    const result = await documentsApi.getContractProjectOptions('案件', 50);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/contract-projects-dropdown',
      { search: '案件', limit: 50 }
    );
    expect(result).toEqual(mockOptions);
  });

  it('不傳參數時 limit 預設為 100', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ options: [] });

    await documentsApi.getContractProjectOptions();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/contract-projects-dropdown',
      { search: undefined, limit: 100 }
    );
  });

  it('回應中沒有 options 時應返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    const result = await documentsApi.getContractProjectOptions();

    expect(result).toEqual([]);
  });
});

// ============================================================================
// documentsApi.getAgencyOptions 測試
// ============================================================================

describe('documentsApi.getAgencyOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該傳遞搜尋和 limit 參數', async () => {
    const mockOptions = [{ value: '1', label: '台北市政府' }];
    vi.mocked(apiClient.post).mockResolvedValue({ options: mockOptions });

    const result = await documentsApi.getAgencyOptions('台北', 30);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/agencies-dropdown',
      { search: '台北', limit: 30 }
    );
    expect(result).toEqual(mockOptions);
  });

  it('回應中沒有 options 時應返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    const result = await documentsApi.getAgencyOptions();

    expect(result).toEqual([]);
  });
});

// ============================================================================
// documentsApi.searchDocuments 測試
// ============================================================================

describe('documentsApi.searchDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該用關鍵字搜尋並返回公文列表', async () => {
    const searchResults = [
      { ...mockDocument, id: 1, subject: '測量公文A' },
      { ...mockDocument, id: 2, subject: '測量公文B' },
    ];
    vi.mocked(apiClient.postList).mockResolvedValue({
      ...mockPaginatedResponse,
      items: searchResults,
    });

    const result = await documentsApi.searchDocuments('測量');

    expect(result).toHaveLength(2);
    expect(result[0]?.subject).toBe('測量公文A');
  });

  it('應該使用預設 limit 為 10', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.searchDocuments('關鍵字');

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        keyword: '關鍵字',
        limit: 10,
      })
    );
  });

  it('應該支援自訂 limit', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.searchDocuments('公文', 50);

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/list',
      expect.objectContaining({
        keyword: '公文',
        limit: 50,
      })
    );
  });
});

// ============================================================================
// documentsApi.getDocumentsByProject 測試
// ============================================================================

describe('documentsApi.getDocumentsByProject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該傳遞 project_id、page 和 limit 參數', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocumentsByProject(5, 2, 25);

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/by-project',
      { project_id: 5, page: 2, limit: 25 }
    );
  });

  it('page 和 limit 應使用預設值', async () => {
    vi.mocked(apiClient.postList).mockResolvedValue(mockPaginatedResponse);

    await documentsApi.getDocumentsByProject(3);

    expect(apiClient.postList).toHaveBeenCalledWith(
      '/documents-enhanced/by-project',
      { project_id: 3, page: 1, limit: 50 }
    );
  });

  it('API 失敗時應返回空分頁回應（graceful degradation）', async () => {
    vi.mocked(apiClient.postList).mockRejectedValue(new Error('網路錯誤'));

    const result = await documentsApi.getDocumentsByProject(1);

    expect(result.success).toBe(true);
    expect(result.items).toEqual([]);
    expect(result.pagination.total).toBe(0);
  });
});

// ============================================================================
// documentsApi.exportDocuments 測試
// ============================================================================

describe('documentsApi.exportDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫 downloadPost 並傳遞匯出參數', async () => {
    vi.mocked(apiClient.downloadPost).mockResolvedValue(undefined);

    await documentsApi.exportDocuments({
      documentIds: [1, 2, 3],
      category: '一般',
      year: 115,
    });

    expect(apiClient.downloadPost).toHaveBeenCalledWith(
      '/documents-enhanced/export',
      {
        document_ids: [1, 2, 3],
        category: '一般',
        year: 115,
        format: 'csv',
      },
      expect.stringContaining('documents_export_')
    );
  });

  it('不傳參數時 document_ids/category/year 應為 null', async () => {
    vi.mocked(apiClient.downloadPost).mockResolvedValue(undefined);

    await documentsApi.exportDocuments();

    expect(apiClient.downloadPost).toHaveBeenCalledWith(
      '/documents-enhanced/export',
      {
        document_ids: null,
        category: null,
        year: null,
        format: 'csv',
      },
      expect.stringContaining('documents_export_')
    );
  });

  it('匯出檔名應包含當日日期', async () => {
    vi.mocked(apiClient.downloadPost).mockResolvedValue(undefined);

    await documentsApi.exportDocuments();

    const now = new Date();
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;

    expect(apiClient.downloadPost).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(Object),
      `documents_export_${dateStr}.csv`
    );
  });
});

// ============================================================================
// documentsApi.getDocumentTrends 測試
// ============================================================================

describe('documentsApi.getDocumentTrends', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫趨勢端點並返回結果', async () => {
    const mockTrends = {
      trends: [
        { month: '2026-01', send_count: 10, receive_count: 20 },
        { month: '2026-02', send_count: 15, receive_count: 25 },
      ],
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockTrends);

    const result = await documentsApi.getDocumentTrends();

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/trends', {});
    expect(result.trends).toHaveLength(2);
  });

  it('API 失敗時應返回空 trends（graceful degradation）', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('伺服器錯誤'));

    const result = await documentsApi.getDocumentTrends();

    expect(result).toEqual({ trends: [] });
  });
});

// ============================================================================
// documentsApi.getDocumentEfficiency 測試
// ============================================================================

describe('documentsApi.getDocumentEfficiency', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫效率端點並返回結果', async () => {
    const mockEfficiency = {
      status_distribution: [{ status: '處理中', count: 10 }],
      overdue_count: 5,
      overdue_rate: 0.1,
      total: 50,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockEfficiency);

    const result = await documentsApi.getDocumentEfficiency();

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/efficiency', {});
    expect(result.overdue_count).toBe(5);
    expect(result.total).toBe(50);
  });

  it('API 失敗時應返回預設值（graceful degradation）', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('timeout'));

    const result = await documentsApi.getDocumentEfficiency();

    expect(result).toEqual({
      status_distribution: [],
      overdue_count: 0,
      overdue_rate: 0,
      total: 0,
    });
  });
});

// ============================================================================
// documentsApi.importCSV 測試
// ============================================================================

describe('documentsApi.importCSV', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 postForm 上傳 CSV 檔案', async () => {
    const mockResult = {
      success: true,
      message: '匯入完成',
      total_rows: 10,
      success_count: 9,
      error_count: 1,
      errors: ['第 5 行: 公文字號重複'],
      processing_time: 1.5,
    };
    vi.mocked(apiClient.postForm).mockResolvedValue(mockResult);

    const file = new File(['csv,data'], 'test.csv', { type: 'text/csv' });
    const result = await documentsApi.importCSV(file);

    expect(apiClient.postForm).toHaveBeenCalledWith(
      '/csv-import/upload-and-import',
      expect.any(FormData)
    );
    expect(result.success).toBe(true);
    expect(result.success_count).toBe(9);
  });

  it('FormData 應正確包含 file 欄位', async () => {
    vi.mocked(apiClient.postForm).mockResolvedValue({ success: true, message: '', total_rows: 0, success_count: 0, error_count: 0, errors: [], processing_time: 0 });

    const file = new File(['data'], 'import.csv', { type: 'text/csv' });
    await documentsApi.importCSV(file);

    const calledFormData = vi.mocked(apiClient.postForm).mock.calls[0]?.[1] as FormData;
    expect(calledFormData.get('file')).toBeTruthy();
  });
});

// ============================================================================
// documentsApi.getAuditLogs 測試
// ============================================================================

describe('documentsApi.getAuditLogs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該傳遞查詢參數到審計日誌端點', async () => {
    const mockResponse = {
      success: true,
      items: [{ id: 1, action: 'CREATE', resource_type: 'document', resource_id: 1, user_id: 1, user_name: '管理員', details: {}, created_at: '2026-01-01T00:00:00Z' }],
      total: 1,
      page: 1,
      limit: 20,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await documentsApi.getAuditLogs({
      page: 1,
      limit: 20,
      action: 'CREATE',
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/audit-logs',
      { page: 1, limit: 20, action: 'CREATE' }
    );
    expect(result.items).toHaveLength(1);
  });

  it('不傳參數時應發送空物件', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, items: [], total: 0, page: 1, limit: 20 });

    await documentsApi.getAuditLogs();

    expect(apiClient.post).toHaveBeenCalledWith(
      '/documents-enhanced/audit-logs',
      {}
    );
  });
});

// ============================================================================
// documentsApi.getDocumentAuditHistory 測試
// ============================================================================

describe('documentsApi.getDocumentAuditHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該使用 documentId 呼叫審計歷史端點', async () => {
    const mockResponse = {
      success: true,
      document_id: 5,
      history: [
        { id: 1, action: 'CREATE', user_name: '管理員', details: {}, created_at: '2026-01-01T00:00:00Z' },
        { id: 2, action: 'UPDATE', user_name: '管理員', details: { subject: '修改' }, created_at: '2026-01-02T00:00:00Z' },
      ],
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await documentsApi.getDocumentAuditHistory(5);

    expect(apiClient.post).toHaveBeenCalledWith('/documents-enhanced/5/audit-history');
    expect(result.history).toHaveLength(2);
    expect(result.document_id).toBe(5);
  });
});
