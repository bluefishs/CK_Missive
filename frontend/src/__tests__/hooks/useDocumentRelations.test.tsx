/**
 * useDocumentRelations Hook 單元測試
 *
 * 測試公文關聯管理的錯誤處理行為
 * 特別是「錯誤時不清空現有列表」的關鍵行為
 *
 * @version 1.0.0
 * @date 2026-02-04
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from 'antd';
import React from 'react';

// Mock API
const mockGetDispatchLinks = vi.fn();
const mockGetProjectLinks = vi.fn();

vi.mock('../../api/taoyuanDispatchApi', () => ({
  documentLinksApi: {
    getDispatchLinks: (...args: unknown[]) => mockGetDispatchLinks(...args),
    linkDispatch: vi.fn(),
    unlinkDispatch: vi.fn(),
  },
  documentProjectLinksApi: {
    getProjectLinks: (...args: unknown[]) => mockGetProjectLinks(...args),
    linkProject: vi.fn(),
    unlinkProject: vi.fn(),
  },
  dispatchOrdersApi: {
    getList: vi.fn().mockResolvedValue({ items: [] }),
  },
  taoyuanProjectsApi: {
    getList: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

// Mock logger
vi.mock('../../services/logger', () => ({
  logger: {
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));

// 引入被測試的 hooks
import { useDispatchLinks, useProjectLinks } from '../../hooks/system/useDocumentRelations';

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
    <QueryClientProvider client={queryClient}>
      <App>{children}</App>
    </QueryClientProvider>
  );
  return Wrapper;
};

// =============================================================================
// useDispatchLinks Hook 測試
// =============================================================================

describe('useDispatchLinks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功載入派工關聯', async () => {
    const mockLinks = [
      { id: 1, dispatch_order_id: 100, link_type: 'agency_doc' },
      { id: 2, dispatch_order_id: 200, link_type: 'company_doc' },
    ];
    mockGetDispatchLinks.mockResolvedValue({ dispatch_orders: mockLinks });

    const { result } = renderHook(
      () => useDispatchLinks({ documentId: 1 }),
      { wrapper: createWrapper() }
    );

    // 手動觸發載入
    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(2);
    });

    expect(result.current.links[0]?.dispatch_order_id).toBe(100);
  });

  /**
   * 關鍵測試：錯誤時不清空現有列表
   *
   * 這是 Bug 修復的核心測試 - 確保 API 錯誤不會導致資料消失
   */
  it('API 錯誤時應該保留現有資料，不清空列表', async () => {
    // 第一次成功載入
    const mockLinks = [
      { id: 1, dispatch_order_id: 100, link_type: 'agency_doc' },
    ];
    mockGetDispatchLinks.mockResolvedValueOnce({ dispatch_orders: mockLinks });

    const { result } = renderHook(
      () => useDispatchLinks({ documentId: 1 }),
      { wrapper: createWrapper() }
    );

    // 第一次載入成功
    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(1);
    });

    // 第二次 API 錯誤
    mockGetDispatchLinks.mockRejectedValueOnce(new Error('Network Error'));

    // 再次載入（模擬重新整理或操作後自動載入）
    await act(async () => {
      result.current.refresh();
    });

    // 等待 loading 結束
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 關鍵斷言：錯誤後資料仍然保留
    expect(result.current.links).toHaveLength(1);
    expect(result.current.links[0]?.dispatch_order_id).toBe(100);
  });

  it('documentId 為 null 時不應該發送請求', async () => {
    const { result } = renderHook(
      () => useDispatchLinks({ documentId: null }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      result.current.refresh();
    });

    expect(mockGetDispatchLinks).not.toHaveBeenCalled();
  });
});

// =============================================================================
// useProjectLinks Hook 測試
// =============================================================================

describe('useProjectLinks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該成功載入工程關聯', async () => {
    const mockLinks = [
      { id: 1, project_id: 100, link_type: 'agency_doc' },
    ];
    mockGetProjectLinks.mockResolvedValue({ projects: mockLinks });

    const { result } = renderHook(
      () => useProjectLinks({ documentId: 1 }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(1);
    });

    expect(result.current.links[0]?.project_id).toBe(100);
  });

  /**
   * 關鍵測試：錯誤時不清空現有列表
   */
  it('API 錯誤時應該保留現有資料，不清空列表', async () => {
    // 第一次成功載入
    const mockLinks = [
      { id: 1, project_id: 100, link_type: 'agency_doc' },
    ];
    mockGetProjectLinks.mockResolvedValueOnce({ projects: mockLinks });

    const { result } = renderHook(
      () => useProjectLinks({ documentId: 1 }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(1);
    });

    // 第二次 API 錯誤
    mockGetProjectLinks.mockRejectedValueOnce(new Error('Network Error'));

    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // 關鍵斷言：錯誤後資料仍然保留
    expect(result.current.links).toHaveLength(1);
    expect(result.current.links[0]?.project_id).toBe(100);
  });
});

// =============================================================================
// 回歸測試：防止未來重新引入「錯誤時清空列表」的 Bug
// =============================================================================

describe('回歸測試：錯誤處理行為', () => {
  it('連續多次 API 錯誤不應該清空已載入的資料', async () => {
    // 初始資料
    const mockLinks = [
      { id: 1, dispatch_order_id: 100, link_type: 'agency_doc' },
      { id: 2, dispatch_order_id: 200, link_type: 'company_doc' },
    ];
    mockGetDispatchLinks.mockResolvedValueOnce({ dispatch_orders: mockLinks });

    const { result } = renderHook(
      () => useDispatchLinks({ documentId: 1 }),
      { wrapper: createWrapper() }
    );

    // 初始載入成功
    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(2);
    });

    // 連續 3 次錯誤
    mockGetDispatchLinks
      .mockRejectedValueOnce(new Error('Error 1'))
      .mockRejectedValueOnce(new Error('Error 2'))
      .mockRejectedValueOnce(new Error('Error 3'));

    for (let i = 0; i < 3; i++) {
      await act(async () => {
        result.current.refresh();
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // 每次錯誤後資料都應該保留
      expect(result.current.links).toHaveLength(2);
    }
  });

  it('API 成功時應該更新資料', async () => {
    // 初始資料
    mockGetDispatchLinks.mockResolvedValueOnce({
      dispatch_orders: [{ id: 1, dispatch_order_id: 100 }],
    });

    const { result } = renderHook(
      () => useDispatchLinks({ documentId: 1 }),
      { wrapper: createWrapper() }
    );

    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(1);
    });

    // 第二次成功載入（新增了一筆）
    mockGetDispatchLinks.mockResolvedValueOnce({
      dispatch_orders: [
        { id: 1, dispatch_order_id: 100 },
        { id: 2, dispatch_order_id: 200 },
      ],
    });

    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.links).toHaveLength(2);
    });

    // 成功時應該更新為新資料
    expect(result.current.links[1]?.dispatch_order_id).toBe(200);
  });
});
