/**
 * useDocumentRelations Hook 測試
 * 派工關聯 (useDispatchLinks) + 工程關聯 (useProjectLinks)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ── Mock antd App.useApp ──
const { mockMessage } = vi.hoisted(() => ({
  mockMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));
vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  return {
    ...actual,
    App: {
      ...actual.App,
      useApp: () => ({
        message: mockMessage,
        notification: { error: vi.fn(), warning: vi.fn() },
        modal: { confirm: vi.fn() },
      }),
    },
  };
});

// ── Mock React Query ──
const {
  mockInvalidateQueries,
  mockGetDispatchLinks,
  mockLinkDispatch,
  mockUnlinkDispatch,
  mockGetProjectLinks,
  mockLinkProject,
  mockUnlinkProject,
  mockGetDispatchList,
  mockGetProjectList,
} = vi.hoisted(() => ({
  mockInvalidateQueries: vi.fn(),
  mockGetDispatchLinks: vi.fn(),
  mockLinkDispatch: vi.fn(),
  mockUnlinkDispatch: vi.fn(),
  mockGetProjectLinks: vi.fn(),
  mockLinkProject: vi.fn(),
  mockUnlinkProject: vi.fn(),
  mockGetDispatchList: vi.fn(),
  mockGetProjectList: vi.fn(),
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: mockInvalidateQueries,
    }),
    useQuery: vi.fn(() => ({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    })),
  };
});

// ── Mock API modules ──
vi.mock('../../../api/taoyuanDispatchApi', () => ({
  documentLinksApi: {
    getDispatchLinks: mockGetDispatchLinks,
    linkDispatch: mockLinkDispatch,
    unlinkDispatch: mockUnlinkDispatch,
  },
  documentProjectLinksApi: {
    getProjectLinks: mockGetProjectLinks,
    linkProject: mockLinkProject,
    unlinkProject: mockUnlinkProject,
  },
  dispatchOrdersApi: {
    getList: mockGetDispatchList,
  },
  taoyuanProjectsApi: {
    getList: mockGetProjectList,
  },
}));

// ── Mock logger ──
vi.mock('../../../services/logger', () => ({
  logger: { error: vi.fn(), warn: vi.fn(), info: vi.fn(), debug: vi.fn() },
}));

// ── Mock queryConfig ──
vi.mock('../../../config/queryConfig', () => ({
  queryKeys: {
    documentRelations: {
      dispatchOrders: (keyword: string) => ['dispatch-orders', keyword],
      projects: (keyword: string) => ['projects', keyword],
      allDispatches: ['all-dispatches'],
      allProjects: ['all-projects'],
    },
  },
}));

import { useDispatchLinks, useProjectLinks } from '../useDocumentRelations';

describe('useDocumentRelations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ========================================================================
  // useDispatchLinks
  // ========================================================================

  describe('useDispatchLinks', () => {
    describe('初始狀態', () => {
      it('應有正確的初始值', () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 1 })
        );

        expect(result.current.links).toEqual([]);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.selectedDispatchId).toBeUndefined();
        expect(result.current.searchKeyword).toBe('');
        expect(result.current.isLinking).toBe(false);
        expect(result.current.availableDispatches).toEqual([]);
        expect(result.current.filteredDispatches).toEqual([]);
      });

      it('回傳的介面應包含所有必要函數', () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 1 })
        );

        expect(typeof result.current.setSelectedDispatchId).toBe('function');
        expect(typeof result.current.setSearchKeyword).toBe('function');
        expect(typeof result.current.linkDispatch).toBe('function');
        expect(typeof result.current.unlinkDispatch).toBe('function');
        expect(typeof result.current.refresh).toBe('function');
      });
    });

    describe('setSelectedDispatchId', () => {
      it('應更新 selectedDispatchId', () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 1 })
        );

        act(() => {
          result.current.setSelectedDispatchId(42);
        });

        expect(result.current.selectedDispatchId).toBe(42);
      });

      it('設為 undefined 應清除選取', () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 1 })
        );

        act(() => {
          result.current.setSelectedDispatchId(10);
        });
        act(() => {
          result.current.setSelectedDispatchId(undefined);
        });

        expect(result.current.selectedDispatchId).toBeUndefined();
      });
    });

    describe('setSearchKeyword', () => {
      it('應更新搜尋關鍵字', () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 1 })
        );

        act(() => {
          result.current.setSearchKeyword('派工');
        });

        expect(result.current.searchKeyword).toBe('派工');
      });
    });

    describe('refresh (loadLinks)', () => {
      it('documentId 為 null 時不應呼叫 API', async () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: null })
        );

        await act(async () => {
          await result.current.refresh();
        });

        expect(mockGetDispatchLinks).not.toHaveBeenCalled();
      });

      it('成功時應更新 links', async () => {
        const mockLinks = [
          { id: 1, dispatch_order_id: 10, link_type: 'main' },
          { id: 2, dispatch_order_id: 20, link_type: 'reference' },
        ];
        mockGetDispatchLinks.mockResolvedValue({ dispatch_orders: mockLinks });

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.refresh();
        });

        expect(mockGetDispatchLinks).toHaveBeenCalledWith(5);
        expect(result.current.links).toEqual(mockLinks);
        expect(result.current.isLoading).toBe(false);
      });

      it('API 錯誤時不應清空 links 並顯示錯誤', async () => {
        mockGetDispatchLinks.mockRejectedValue(new Error('Network Error'));

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.refresh();
        });

        expect(mockMessage.error).toHaveBeenCalledWith('載入派工關聯失敗，請重新整理頁面');
        expect(result.current.isLoading).toBe(false);
      });
    });

    describe('linkDispatch', () => {
      it('documentId 為 null 時不應呼叫 API', async () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: null })
        );

        await act(async () => {
          await result.current.linkDispatch(10, 'main' as never);
        });

        expect(mockLinkDispatch).not.toHaveBeenCalled();
      });

      it('成功時應顯示成功訊息並重新載入', async () => {
        mockLinkDispatch.mockResolvedValue({});
        mockGetDispatchLinks.mockResolvedValue({ dispatch_orders: [] });

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.linkDispatch(10, 'main' as never);
        });

        expect(mockLinkDispatch).toHaveBeenCalledWith(5, 10, 'main');
        expect(mockMessage.success).toHaveBeenCalledWith('關聯成功');
        expect(mockInvalidateQueries).toHaveBeenCalled();
        expect(result.current.isLinking).toBe(false);
      });

      it('失敗時應顯示錯誤訊息', async () => {
        mockLinkDispatch.mockRejectedValue(new Error('Duplicate link'));

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.linkDispatch(10, 'main' as never);
        });

        expect(mockMessage.error).toHaveBeenCalledWith('Duplicate link');
        expect(result.current.isLinking).toBe(false);
      });

      it('非 Error 例外應顯示「關聯失敗」', async () => {
        mockLinkDispatch.mockRejectedValue('string error');

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.linkDispatch(10, 'ref' as never);
        });

        expect(mockMessage.error).toHaveBeenCalledWith('關聯失敗');
      });
    });

    describe('unlinkDispatch', () => {
      it('documentId 為 null 時不應呼叫 API', async () => {
        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: null })
        );

        await act(async () => {
          await result.current.unlinkDispatch(1);
        });

        expect(mockUnlinkDispatch).not.toHaveBeenCalled();
      });

      it('成功時應顯示成功訊息並重新載入', async () => {
        mockUnlinkDispatch.mockResolvedValue({});
        mockGetDispatchLinks.mockResolvedValue({ dispatch_orders: [] });

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.unlinkDispatch(1);
        });

        expect(mockUnlinkDispatch).toHaveBeenCalledWith(5, 1);
        expect(mockMessage.success).toHaveBeenCalledWith('已移除關聯');
        expect(mockInvalidateQueries).toHaveBeenCalled();
      });

      it('失敗時應顯示錯誤訊息', async () => {
        mockUnlinkDispatch.mockRejectedValue(new Error('Not found'));

        const { result } = renderHook(() =>
          useDispatchLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.unlinkDispatch(1);
        });

        expect(mockMessage.error).toHaveBeenCalledWith('移除關聯失敗');
      });
    });
  });

  // ========================================================================
  // useProjectLinks
  // ========================================================================

  describe('useProjectLinks', () => {
    describe('初始狀態', () => {
      it('應有正確的初始值', () => {
        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 1 })
        );

        expect(result.current.links).toEqual([]);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.selectedProjectId).toBeUndefined();
        expect(result.current.searchKeyword).toBe('');
        expect(result.current.isLinking).toBe(false);
        expect(result.current.availableProjects).toEqual([]);
        expect(result.current.filteredProjects).toEqual([]);
      });
    });

    describe('refresh (loadLinks)', () => {
      it('documentId 為 null 時不應呼叫 API', async () => {
        const { result } = renderHook(() =>
          useProjectLinks({ documentId: null })
        );

        await act(async () => {
          await result.current.refresh();
        });

        expect(mockGetProjectLinks).not.toHaveBeenCalled();
      });

      it('成功時應更新 links', async () => {
        const mockLinks = [{ id: 1, project_id: 100, link_type: 'main' }];
        mockGetProjectLinks.mockResolvedValue({ projects: mockLinks });

        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 3 })
        );

        await act(async () => {
          await result.current.refresh();
        });

        expect(mockGetProjectLinks).toHaveBeenCalledWith(3);
        expect(result.current.links).toEqual(mockLinks);
      });

      it('API 錯誤時不應清空 links', async () => {
        mockGetProjectLinks.mockRejectedValue(new Error('Error'));

        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 3 })
        );

        await act(async () => {
          await result.current.refresh();
        });

        expect(mockMessage.error).toHaveBeenCalledWith('載入工程關聯失敗，請重新整理頁面');
      });
    });

    describe('linkProject', () => {
      it('documentId 為 null 時不應呼叫 API', async () => {
        const { result } = renderHook(() =>
          useProjectLinks({ documentId: null })
        );

        await act(async () => {
          await result.current.linkProject(10, 'main' as never);
        });

        expect(mockLinkProject).not.toHaveBeenCalled();
      });

      it('成功時應顯示成功訊息並傳遞 notes', async () => {
        mockLinkProject.mockResolvedValue({});
        mockGetProjectLinks.mockResolvedValue({ projects: [] });

        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.linkProject(10, 'main' as never, '備註說明');
        });

        expect(mockLinkProject).toHaveBeenCalledWith(5, 10, 'main', '備註說明');
        expect(mockMessage.success).toHaveBeenCalledWith('關聯成功');
        expect(mockInvalidateQueries).toHaveBeenCalled();
      });

      it('失敗時應顯示 Error message', async () => {
        mockLinkProject.mockRejectedValue(new Error('Already linked'));

        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.linkProject(10, 'ref' as never);
        });

        expect(mockMessage.error).toHaveBeenCalledWith('Already linked');
      });
    });

    describe('unlinkProject', () => {
      it('成功時應顯示成功訊息', async () => {
        mockUnlinkProject.mockResolvedValue({});
        mockGetProjectLinks.mockResolvedValue({ projects: [] });

        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.unlinkProject(1);
        });

        expect(mockUnlinkProject).toHaveBeenCalledWith(5, 1);
        expect(mockMessage.success).toHaveBeenCalledWith('已移除關聯');
      });

      it('失敗時應顯示錯誤訊息', async () => {
        mockUnlinkProject.mockRejectedValue(new Error('fail'));

        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 5 })
        );

        await act(async () => {
          await result.current.unlinkProject(1);
        });

        expect(mockMessage.error).toHaveBeenCalledWith('移除關聯失敗');
      });
    });

    describe('setSelectedProjectId', () => {
      it('應更新 selectedProjectId', () => {
        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 1 })
        );

        act(() => {
          result.current.setSelectedProjectId(99);
        });

        expect(result.current.selectedProjectId).toBe(99);
      });
    });

    describe('setSearchKeyword', () => {
      it('應更新搜尋關鍵字', () => {
        const { result } = renderHook(() =>
          useProjectLinks({ documentId: 1 })
        );

        act(() => {
          result.current.setSearchKeyword('工程');
        });

        expect(result.current.searchKeyword).toBe('工程');
      });
    });
  });
});
