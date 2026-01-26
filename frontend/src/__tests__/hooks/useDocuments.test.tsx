/**
 * useDocuments Hook 單元測試
 * useDocuments Hook Unit Tests
 *
 * 測試公文管理 React Query Hooks
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDocuments
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { OfficialDocument } from '../../types/api';
import type { PaginatedResponse, DeleteResponse } from '../../api/types';

// ============================================================================
// Mock 資料工廠函數
// ============================================================================

/** 建立完整的公文 Mock 資料 */
const createMockDocument = (overrides: Partial<OfficialDocument> = {}): OfficialDocument => ({
  id: 1,
  doc_number: 'TEST-001',
  subject: '測試公文',
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

// Mock documentsApi
vi.mock('../../api/documentsApi', () => ({
  documentsApi: {
    getDocuments: vi.fn(),
    getDocument: vi.fn(),
    createDocument: vi.fn(),
    updateDocument: vi.fn(),
    deleteDocument: vi.fn(),
    getStatistics: vi.fn(),
    getYearOptions: vi.fn(),
    getContractProjectOptions: vi.fn(),
    getAgencyOptions: vi.fn(),
    getDocumentsByProject: vi.fn(),
  },
}));

// Mock queryConfig
vi.mock('../../config/queryConfig', () => ({
  queryKeys: {
    documents: {
      all: ['documents'],
      list: (params: Record<string, unknown>) => ['documents', 'list', params],
      detail: (id: number) => ['documents', 'detail', id],
      statistics: ['documents', 'statistics'],
      years: ['documents', 'years'],
    },
    projects: {
      documents: (id: number) => ['projects', 'documents', id],
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
  useDocuments,
  useDocument,
  useDocumentStatistics,
  useDocumentYearOptions,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useDocumentsPage,
} from '../../hooks/business/useDocuments';

import { documentsApi } from '../../api/documentsApi';

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
// useDocuments Hook 測試
// ============================================================================

describe('useDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得公文列表', async () => {
    const mockResponse = createMockPaginatedResponse([
      createMockDocument({ id: 1, doc_number: 'TEST-001', subject: '測試公文1' }),
      createMockDocument({ id: 2, doc_number: 'TEST-002', subject: '測試公文2' }),
    ], { total: 2 });

    vi.mocked(documentsApi.getDocuments).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items?.[0]?.doc_number).toBe('TEST-001');
  });

  it('應該正確傳遞查詢參數', async () => {
    vi.mocked(documentsApi.getDocuments).mockResolvedValue(
      createMockPaginatedResponse<OfficialDocument>([], { total: 0, limit: 10, total_pages: 0 })
    );

    const params = {
      page: 2,
      limit: 10,
      keyword: '測試',
      doc_type: '函',
    };

    renderHook(() => useDocuments(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(documentsApi.getDocuments).toHaveBeenCalledWith(params);
    });
  });

  it('應該處理 API 錯誤', async () => {
    const error = new Error('API Error');
    vi.mocked(documentsApi.getDocuments).mockRejectedValue(error);

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

// ============================================================================
// useDocument Hook 測試
// ============================================================================

describe('useDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得單一公文', async () => {
    const mockDocument = createMockDocument({
      id: 1,
      doc_number: 'TEST-001',
      subject: '測試公文',
      sender: '桃園市政府',
      receiver: '乾坤測繪',
    });

    vi.mocked(documentsApi.getDocument).mockResolvedValue(mockDocument);

    const { result } = renderHook(() => useDocument(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.doc_number).toBe('TEST-001');
  });

  it('當 documentId 為 null 時不應該發送請求', async () => {
    const { result } = renderHook(() => useDocument(null), {
      wrapper: createWrapper(),
    });

    // enabled: false 時不會發送請求
    expect(result.current.isFetching).toBe(false);
    expect(documentsApi.getDocument).not.toHaveBeenCalled();
  });

  it('當 documentId 為 undefined 時不應該發送請求', async () => {
    const { result } = renderHook(() => useDocument(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
    expect(documentsApi.getDocument).not.toHaveBeenCalled();
  });
});

// ============================================================================
// useDocumentStatistics Hook 測試
// ============================================================================

describe('useDocumentStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得統計資料', async () => {
    const mockStats = {
      total: 100,
      total_documents: 100,
      send: 40,
      send_count: 40,
      receive: 60,
      receive_count: 60,
      current_year_count: 25,
      current_year_send_count: 10,
      delivery_method_stats: {
        electronic: 70,
        paper: 30,
        both: 0,
      },
    };

    vi.mocked(documentsApi.getStatistics).mockResolvedValue(mockStats);

    const { result } = renderHook(() => useDocumentStatistics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.total).toBe(100);
    expect(result.current.data?.send).toBe(40);
    expect(result.current.data?.receive).toBe(60);
  });
});

// ============================================================================
// useDocumentYearOptions Hook 測試
// ============================================================================

describe('useDocumentYearOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功取得年度選項', async () => {
    const mockYears = [2026, 2025, 2024, 2023];

    vi.mocked(documentsApi.getYearOptions).mockResolvedValue(mockYears);

    const { result } = renderHook(() => useDocumentYearOptions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockYears);
    expect(result.current.data).toHaveLength(4);
  });
});

// ============================================================================
// Mutation Hooks 測試
// ============================================================================

describe('useCreateDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功建立公文', async () => {
    const newDocument = createMockDocument({
      id: 1,
      doc_number: 'NEW-001',
      subject: '新增公文',
      doc_type: '函',
      sender: '乾坤測繪',
      receiver: '桃園市政府',
    });

    vi.mocked(documentsApi.createDocument).mockResolvedValue(newDocument);

    const { result } = renderHook(() => useCreateDocument(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      doc_number: 'NEW-001',
      subject: '新增公文',
      doc_type: '函',
      sender: '乾坤測繪',
      receiver: '桃園市政府',
    });

    expect(documentsApi.createDocument).toHaveBeenCalled();
  });
});

describe('useUpdateDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功更新公文', async () => {
    const updatedDocument = createMockDocument({
      id: 1,
      doc_number: 'TEST-001',
      subject: '更新後的主旨',
    });

    vi.mocked(documentsApi.updateDocument).mockResolvedValue(updatedDocument);

    const { result } = renderHook(() => useUpdateDocument(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      documentId: 1,
      data: { subject: '更新後的主旨' },
    });

    expect(documentsApi.updateDocument).toHaveBeenCalledWith(1, {
      subject: '更新後的主旨',
    });
  });
});

describe('useDeleteDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功刪除公文', async () => {
    vi.mocked(documentsApi.deleteDocument).mockResolvedValue(
      createMockDeleteResponse(1)
    );

    const { result } = renderHook(() => useDeleteDocument(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync(1);

    expect(documentsApi.deleteDocument).toHaveBeenCalledWith(1);
  });
});

// ============================================================================
// useDocumentsPage Hook 測試
// ============================================================================

describe('useDocumentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // 設定預設 mock 回傳值
    vi.mocked(documentsApi.getDocuments).mockResolvedValue(
      createMockPaginatedResponse([
        createMockDocument({ id: 1, doc_number: 'TEST-001', subject: '測試' }),
      ], { total: 1 })
    );

    vi.mocked(documentsApi.getStatistics).mockResolvedValue({
      total: 100,
      total_documents: 100,
      send: 40,
      send_count: 40,
      receive: 60,
      receive_count: 60,
      current_year_count: 25,
      current_year_send_count: 10,
      delivery_method_stats: {
        electronic: 70,
        paper: 30,
        both: 0,
      },
    });

    vi.mocked(documentsApi.getYearOptions).mockResolvedValue([2026, 2025]);
    vi.mocked(documentsApi.createDocument).mockResolvedValue(
      createMockDocument({ id: 1, doc_number: 'NEW-001', subject: '新增' })
    );
  });

  it('應該整合多個查詢結果', async () => {
    const { result } = renderHook(() => useDocumentsPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 驗證列表資料
    expect(result.current.documents).toHaveLength(1);

    // 驗證統計資料
    expect(result.current.statistics?.total).toBe(100);

    // 驗證年度選項
    expect(result.current.availableYears).toEqual([2026, 2025]);
  });

  it('應該提供操作方法', async () => {
    const { result } = renderHook(() => useDocumentsPage(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 驗證操作方法存在
    expect(typeof result.current.createDocument).toBe('function');
    expect(typeof result.current.updateDocument).toBe('function');
    expect(typeof result.current.deleteDocument).toBe('function');
    expect(typeof result.current.refetch).toBe('function');
  });

  it('應該正確傳遞篩選參數', async () => {
    const params = { keyword: '測試', doc_type: '函' };

    renderHook(() => useDocumentsPage(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(documentsApi.getDocuments).toHaveBeenCalledWith(params);
    });
  });
});
