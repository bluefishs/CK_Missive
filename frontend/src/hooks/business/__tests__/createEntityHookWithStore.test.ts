/**
 * createEntityHookWithStore 工廠函數測試
 * Factory Hook Tests — useEntityWithStoreCore + useEntityDetailCore
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useEntityWithStoreCore, useEntityDetailCore } from '../createEntityHookWithStore';

// ── Mock Store 工廠 ──

interface MockStore<T = { id: number; name: string }, F = { search: string }> {
  items: T[];
  selectedItem: T | null;
  filters: F;
  pagination: { page: number; limit: number; total: number; totalPages: number };
  loading: boolean;
  setItems: ReturnType<typeof vi.fn>;
  setSelectedItem: ReturnType<typeof vi.fn>;
  addItem: ReturnType<typeof vi.fn>;
  updateItem: ReturnType<typeof vi.fn>;
  removeItem: ReturnType<typeof vi.fn>;
  setFilters: ReturnType<typeof vi.fn>;
  setPagination: ReturnType<typeof vi.fn>;
  resetFilters: ReturnType<typeof vi.fn>;
  setLoading: ReturnType<typeof vi.fn>;
}

function createMockStore<T = { id: number; name: string }, F = { search: string }>(): MockStore<T, F> {
  return {
    items: [] as T[],
    selectedItem: null as T | null,
    filters: { search: '' } as F,
    pagination: { page: 1, limit: 20, total: 0, totalPages: 0 },
    loading: false,
    setItems: vi.fn(function (this: MockStore<T, F>, items: T[]) {
      this.items = items;
    }) as ReturnType<typeof vi.fn>,
    setSelectedItem: vi.fn(function (this: MockStore<T, F>, item: T | null) {
      this.selectedItem = item;
    }) as ReturnType<typeof vi.fn>,
    addItem: vi.fn(),
    updateItem: vi.fn(),
    removeItem: vi.fn(),
    setFilters: vi.fn(),
    setPagination: vi.fn(),
    resetFilters: vi.fn(),
    setLoading: vi.fn(),
  };
}

// ── Mock Query 工廠 ──

function createMockListQuery<T>(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    data: undefined as { items: T[]; pagination?: { total: number; total_pages: number } } | undefined,
    isLoading: false,
    isError: false,
    error: null as Error | null,
    isFetching: false,
    refetch: vi.fn(),
    ...overrides,
  } as never;
}

function createMockMutation(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    mutateAsync: vi.fn(),
    isPending: false,
    ...overrides,
  } as never;
}

// ── 測試 ──

describe('createEntityHookWithStore', () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  describe('useEntityWithStoreCore — 基本結構', () => {
    it('應回傳完整的 EntityWithStoreCore 介面', () => {
      const listQuery = createMockListQuery();
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, listQuery, mutations)
      );

      // Store 狀態
      expect(result.current).toHaveProperty('items');
      expect(result.current).toHaveProperty('selectedItem');
      expect(result.current).toHaveProperty('filters');
      expect(result.current).toHaveProperty('pagination');
      expect(result.current).toHaveProperty('loading');
      // Query 狀態
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('isError');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('isFetching');
      // CRUD
      expect(typeof result.current.handleCreate).toBe('function');
      expect(typeof result.current.handleUpdate).toBe('function');
      expect(typeof result.current.handleDelete).toBe('function');
      // Mutation 狀態
      expect(result.current).toHaveProperty('isCreating');
      expect(result.current).toHaveProperty('isUpdating');
      expect(result.current).toHaveProperty('isDeleting');
      // UI 操作
      expect(typeof result.current.setPage).toBe('function');
      expect(typeof result.current.setFilters).toBe('function');
      expect(typeof result.current.selectItem).toBe('function');
      expect(typeof result.current.resetFilters).toBe('function');
      expect(typeof result.current.refetch).toBe('function');
    });
  });

  describe('useEntityWithStoreCore — items 同步', () => {
    it('查詢有資料時應同步 items 到 store', () => {
      const items = [{ id: 1, name: 'A' }, { id: 2, name: 'B' }];
      const listQuery = createMockListQuery({
        data: { items, pagination: { total: 2, total_pages: 1 } },
      });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      renderHook(() => useEntityWithStoreCore(store, listQuery, mutations));

      expect(store.setItems).toHaveBeenCalledWith(items);
      expect(store.setPagination).toHaveBeenCalledWith({
        total: 2,
        totalPages: 1,
      });
    });

    it('查詢無分頁資訊時不應呼叫 setPagination', () => {
      const items = [{ id: 1, name: 'A' }];
      const listQuery = createMockListQuery({
        data: { items },
      });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      renderHook(() => useEntityWithStoreCore(store, listQuery, mutations));

      expect(store.setItems).toHaveBeenCalledWith(items);
      expect(store.setPagination).not.toHaveBeenCalled();
    });

    it('查詢資料為 undefined 時不應呼叫 setItems', () => {
      const listQuery = createMockListQuery({ data: undefined });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      renderHook(() => useEntityWithStoreCore(store, listQuery, mutations));

      expect(store.setItems).not.toHaveBeenCalled();
    });

    it('itemsTransform 應在同步前轉換 items', () => {
      const items = [{ id: 1, name: 'raw' }];
      const listQuery = createMockListQuery({ data: { items } });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };
      const transform = vi.fn((items: { id: number; name: string }[]) =>
        items.map(i => ({ ...i, name: i.name.toUpperCase() }))
      );

      renderHook(() =>
        useEntityWithStoreCore(store, listQuery, mutations, {
          itemsTransform: transform as never,
        })
      );

      expect(transform).toHaveBeenCalledWith(items);
      expect(store.setItems).toHaveBeenCalledWith([{ id: 1, name: 'RAW' }]);
    });
  });

  describe('useEntityWithStoreCore — loading 同步', () => {
    it('預設應同步 loading 狀態到 store', () => {
      const listQuery = createMockListQuery({ isLoading: true });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      renderHook(() => useEntityWithStoreCore(store, listQuery, mutations));

      expect(store.setLoading).toHaveBeenCalledWith(true);
    });

    it('syncLoading=false 時不應同步 loading', () => {
      const listQuery = createMockListQuery({ isLoading: true });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      renderHook(() =>
        useEntityWithStoreCore(store, listQuery, mutations, {
          syncLoading: false,
        })
      );

      expect(store.setLoading).not.toHaveBeenCalled();
    });
  });

  describe('useEntityWithStoreCore — CRUD 操作', () => {
    it('handleCreate 應呼叫 mutation 並 addItem', async () => {
      const newItem = { id: 3, name: 'New' };
      const createMut = createMockMutation();
      (createMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(newItem);
      const mutations = {
        create: createMut,
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      let created: unknown;
      await act(async () => {
        created = await result.current.handleCreate({ name: 'New' } as never);
      });

      expect(created).toEqual(newItem);
      expect(store.addItem).toHaveBeenCalledWith(newItem);
    });

    it('handleCreate 結果為 falsy 時不應 addItem', async () => {
      const createMut = createMockMutation();
      (createMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(null);
      const mutations = {
        create: createMut,
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      await act(async () => {
        await result.current.handleCreate({} as never);
      });

      expect(store.addItem).not.toHaveBeenCalled();
    });

    it('handleUpdate 應呼叫 mutation 並 updateItem', async () => {
      const updated = { id: 1, name: 'Updated' };
      const updateMut = createMockMutation();
      (updateMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(updated);
      const mutations = {
        create: createMockMutation(),
        update: updateMut,
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      await act(async () => {
        await result.current.handleUpdate(1, { name: 'Updated' } as never);
      });

      expect(
        (updateMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync
      ).toHaveBeenCalledWith({ id: 1, data: { name: 'Updated' } });
      expect(store.updateItem).toHaveBeenCalledWith(1, updated);
    });

    it('handleUpdate 使用 buildUpdatePayload 時應自訂 payload', async () => {
      const updated = { id: 1, name: 'Updated' };
      const updateMut = createMockMutation();
      (updateMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(updated);
      const mutations = {
        create: createMockMutation(),
        update: updateMut,
        delete: createMockMutation(),
      };
      const buildUpdatePayload = vi.fn((id: number, data: unknown) => ({
        custom_id: id,
        payload: data,
      }));

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations, {
          buildUpdatePayload,
        })
      );

      await act(async () => {
        await result.current.handleUpdate(1, { name: 'X' } as never);
      });

      expect(buildUpdatePayload).toHaveBeenCalledWith(1, { name: 'X' });
      expect(
        (updateMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync
      ).toHaveBeenCalledWith({ custom_id: 1, payload: { name: 'X' } });
    });

    it('handleUpdate 使用 storeIdTransform 時應轉換 ID', async () => {
      const updated = { id: 5, name: 'Transformed' };
      const updateMut = createMockMutation();
      (updateMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(updated);
      const mutations = {
        create: createMockMutation(),
        update: updateMut,
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations, {
          storeIdTransform: (id) => id * 10,
        })
      );

      await act(async () => {
        await result.current.handleUpdate(5, {} as never);
      });

      expect(store.updateItem).toHaveBeenCalledWith(50, updated);
    });

    it('handleDelete 應呼叫 mutation 並 removeItem', async () => {
      const deleteMut = createMockMutation();
      (deleteMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(undefined);
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: deleteMut,
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      await act(async () => {
        await result.current.handleDelete(7);
      });

      expect(
        (deleteMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync
      ).toHaveBeenCalledWith(7);
      expect(store.removeItem).toHaveBeenCalledWith(7);
    });

    it('handleDelete 使用 storeIdTransform 時應轉換 ID', async () => {
      const deleteMut = createMockMutation();
      (deleteMut as unknown as { mutateAsync: ReturnType<typeof vi.fn> }).mutateAsync.mockResolvedValue(undefined);
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: deleteMut,
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations, {
          storeIdTransform: (id) => id + 100,
        })
      );

      await act(async () => {
        await result.current.handleDelete(3);
      });

      expect(store.removeItem).toHaveBeenCalledWith(103);
    });
  });

  describe('useEntityWithStoreCore — UI 操作', () => {
    it('setPage 應更新 pagination', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      act(() => {
        result.current.setPage(3);
      });

      expect(store.setPagination).toHaveBeenCalledWith({ page: 3, limit: 20 });
    });

    it('setPage 帶 pageSize 應同時更新 limit', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      act(() => {
        result.current.setPage(2, 50);
      });

      expect(store.setPagination).toHaveBeenCalledWith({ page: 2, limit: 50 });
    });

    it('setFilters 應委託給 store', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      act(() => {
        result.current.setFilters({ search: 'hello' } as never);
      });

      expect(store.setFilters).toHaveBeenCalledWith({ search: 'hello' });
    });

    it('selectItem 應委託給 store', () => {
      const item = { id: 1, name: 'Test' };
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      act(() => {
        result.current.selectItem(item as never);
      });

      expect(store.setSelectedItem).toHaveBeenCalledWith(item);
    });

    it('selectItem(null) 應清除選取', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      act(() => {
        result.current.selectItem(null);
      });

      expect(store.setSelectedItem).toHaveBeenCalledWith(null);
    });

    it('resetFilters 應委託給 store', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      act(() => {
        result.current.resetFilters();
      });

      expect(store.resetFilters).toHaveBeenCalled();
    });
  });

  describe('useEntityWithStoreCore — Mutation 狀態映射', () => {
    it('isCreating 應映射 create mutation isPending', () => {
      const mutations = {
        create: createMockMutation({ isPending: true }),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      expect(result.current.isCreating).toBe(true);
      expect(result.current.isUpdating).toBe(false);
      expect(result.current.isDeleting).toBe(false);
    });

    it('isUpdating 應映射 update mutation isPending', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation({ isPending: true }),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      expect(result.current.isUpdating).toBe(true);
    });

    it('isDeleting 應映射 delete mutation isPending', () => {
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation({ isPending: true }),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, createMockListQuery(), mutations)
      );

      expect(result.current.isDeleting).toBe(true);
    });
  });

  describe('useEntityWithStoreCore — Query 狀態映射', () => {
    it('isError 和 error 應映射 listQuery', () => {
      const queryError = new Error('Query failed');
      const listQuery = createMockListQuery({
        isError: true,
        error: queryError,
      });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, listQuery, mutations)
      );

      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBe(queryError);
    });

    it('isFetching 應映射 listQuery', () => {
      const listQuery = createMockListQuery({ isFetching: true });
      const mutations = {
        create: createMockMutation(),
        update: createMockMutation(),
        delete: createMockMutation(),
      };

      const { result } = renderHook(() =>
        useEntityWithStoreCore(store, listQuery, mutations)
      );

      expect(result.current.isFetching).toBe(true);
    });
  });

  // ========================================================================
  // useEntityDetailCore
  // ========================================================================

  describe('useEntityDetailCore — 基本結構', () => {
    it('應回傳完整的 detail 介面', () => {
      const detailStore = {
        setSelectedItem: vi.fn(),
        selectedItem: null,
      };
      const detailQuery = createMockListQuery() as never;

      const { result } = renderHook(() =>
        useEntityDetailCore(detailStore, detailQuery)
      );

      expect(result.current).toHaveProperty('data');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('isError');
      expect(result.current).toHaveProperty('error');
      expect(typeof result.current.refetch).toBe('function');
    });
  });

  describe('useEntityDetailCore — 資料同步', () => {
    it('查詢有資料時應同步到 store 並回傳', () => {
      const entity = { id: 1, name: 'Detail' };
      const detailStore = {
        setSelectedItem: vi.fn(),
        selectedItem: null,
      };
      const detailQuery = createMockListQuery({ data: entity }) as never;

      const { result } = renderHook(() =>
        useEntityDetailCore(detailStore, detailQuery)
      );

      expect(detailStore.setSelectedItem).toHaveBeenCalledWith(entity);
      expect(result.current.data).toEqual(entity);
    });

    it('查詢無資料時應回退到 store.selectedItem', () => {
      const cached = { id: 2, name: 'Cached' };
      const detailStore = {
        setSelectedItem: vi.fn(),
        selectedItem: cached,
      };
      const detailQuery = createMockListQuery({ data: undefined }) as never;

      const { result } = renderHook(() =>
        useEntityDetailCore(detailStore, detailQuery)
      );

      expect(result.current.data).toEqual(cached);
    });

    it('查詢與 store 都無資料時應回傳 null', () => {
      const detailStore = {
        setSelectedItem: vi.fn(),
        selectedItem: null,
      };
      const detailQuery = createMockListQuery({ data: undefined }) as never;

      const { result } = renderHook(() =>
        useEntityDetailCore(detailStore, detailQuery)
      );

      expect(result.current.data).toBeNull();
    });
  });

  describe('useEntityDetailCore — 狀態映射', () => {
    it('應映射 query 的 loading/error 狀態', () => {
      const detailStore = {
        setSelectedItem: vi.fn(),
        selectedItem: null,
      };
      const detailQuery = createMockListQuery({
        isLoading: true,
        isError: true,
        error: new Error('fail'),
      }) as never;

      const { result } = renderHook(() =>
        useEntityDetailCore(detailStore, detailQuery)
      );

      expect(result.current.isLoading).toBe(true);
      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeInstanceOf(Error);
    });
  });
});
