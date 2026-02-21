/**
 * WithStore Hook 工廠函數
 *
 * 將 React Query (Server State) 與 Zustand Store (UI State)
 * 整合的共用核心邏輯提取為泛型工廠。
 *
 * @version 1.0.0
 * @date 2026-01-28
 */

import { useEffect, useCallback } from 'react';
import type { UseQueryResult, UseMutationResult } from '@tanstack/react-query';

/** 標準化的 Store 介面（對應 EntityState 的 new API） */
interface StoreInterface<T, F> {
  items: T[];
  selectedItem: T | null;
  filters: F;
  pagination: { page: number; limit: number; total: number; totalPages: number };
  loading: boolean;
  setItems: (items: T[]) => void;
  setSelectedItem: (item: T | null) => void;
  addItem: (item: T) => void;
  updateItem: (id: number, updates: Partial<T>) => void;
  removeItem: (id: number) => void;
  setFilters: (filters: Partial<F>) => void;
  setPagination: (pagination: Partial<{ page: number; limit: number; total: number; totalPages: number }>) => void;
  resetFilters: () => void;
  setLoading: (loading: boolean) => void;
}

/** 列表查詢回傳結構 */
interface ListQueryData<T> {
  items: T[];
  pagination?: {
    total: number;
    total_pages: number;
  };
}

/** 工廠配置 */
interface EntityWithStoreConfig<T, U> {
  /** 是否同步 loading 狀態到 store（Documents 不需要） */
  syncLoading?: boolean;
  /** 建構 update mutation payload (預設 { id, data }) */
  buildUpdatePayload?: (id: number, data: U) => unknown;
  /** store 中的 id 轉換（Documents 需要 String()） */
  storeIdTransform?: (id: number) => number | string;
  /** items 同步前的型別轉換 */
  itemsTransform?: (items: T[]) => T[];
}

/** 工廠回傳的核心結果 */
export interface EntityWithStoreCore<T, C, U, F> {
  // Store 狀態
  items: T[];
  selectedItem: T | null;
  filters: F;
  pagination: { page: number; limit: number; total: number; totalPages: number };
  loading: boolean;
  // Query 狀態
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isFetching: boolean;
  // CRUD
  handleCreate: (data: C) => Promise<T>;
  handleUpdate: (id: number, data: U) => Promise<T>;
  handleDelete: (id: number) => Promise<void>;
  // Mutation 狀態
  isCreating: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
  // UI 操作
  setPage: (page: number, pageSize?: number) => void;
  setFilters: (filters: Partial<F>) => void;
  selectItem: (item: T | null) => void;
  resetFilters: () => void;
  refetch: () => void;
}

/**
 * 建立 WithStore Hook 的核心邏輯
 *
 * 使用方式：
 * ```ts
 * const core = useEntityWithStoreCore(store, listQuery, mutations, config);
 * return { vendors: core.items, createVendor: core.handleCreate, ... };
 * ```
 */
export function useEntityWithStoreCore<T, C, U, F>(
  store: StoreInterface<T, F>,
  listQuery: UseQueryResult<ListQueryData<T>>,
  mutations: {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic factory requires flexible mutation types
    create: UseMutationResult<any, Error, C>;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic factory requires flexible mutation types
    update: UseMutationResult<any, Error, any>;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic factory requires flexible mutation types
    delete: UseMutationResult<any, Error, number>;
  },
  config: EntityWithStoreConfig<T, U> = {},
): EntityWithStoreCore<T, C, U, F> {
  const {
    syncLoading = true,
    buildUpdatePayload,
    storeIdTransform,
    itemsTransform,
  } = config;

  // 同步 items + pagination
  useEffect(() => {
    if (listQuery.data?.items) {
      const items = itemsTransform
        ? itemsTransform(listQuery.data.items)
        : listQuery.data.items;
      store.setItems(items);
    }
    if (listQuery.data?.pagination) {
      store.setPagination({
        total: listQuery.data.pagination.total,
        totalPages: listQuery.data.pagination.total_pages,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- store and itemsTransform are stable references from caller
  }, [listQuery.data]);

  // 可選：同步 loading 狀態
  useEffect(() => {
    if (syncLoading) {
      store.setLoading(listQuery.isLoading);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- store is a stable Zustand store reference
  }, [listQuery.isLoading, syncLoading]);

  // CRUD handlers
  const handleCreate = useCallback(
    async (data: C) => {
      const result = await mutations.create.mutateAsync(data);
      if (result) {
        store.addItem(result);
      }
      return result;
    },
    [mutations.create, store]
  );

  const handleUpdate = useCallback(
    async (id: number, data: U) => {
      const payload = buildUpdatePayload ? buildUpdatePayload(id, data) : { id, data };
      const result = await mutations.update.mutateAsync(payload);
      if (result) {
        const storeId = storeIdTransform ? storeIdTransform(id) : id;
        store.updateItem(storeId as number, result as Partial<T>);
      }
      return result;
    },
    [mutations.update, store, buildUpdatePayload, storeIdTransform]
  );

  const handleDelete = useCallback(
    async (id: number) => {
      await mutations.delete.mutateAsync(id);
      const storeId = storeIdTransform ? storeIdTransform(id) : id;
      store.removeItem(storeId as number);
    },
    [mutations.delete, store, storeIdTransform]
  );

  // UI handlers
  const setPage = useCallback(
    (page: number, pageSize?: number) => {
      store.setPagination({ page, limit: pageSize || store.pagination.limit });
    },
    [store]
  );

  const setFilters = useCallback(
    (filters: Partial<F>) => {
      store.setFilters(filters);
    },
    [store]
  );

  const selectItem = useCallback(
    (item: T | null) => {
      store.setSelectedItem(item);
    },
    [store]
  );

  return {
    items: store.items,
    selectedItem: store.selectedItem,
    filters: store.filters,
    pagination: store.pagination,
    loading: store.loading,
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    error: listQuery.error,
    isFetching: listQuery.isFetching,
    handleCreate,
    handleUpdate,
    handleDelete,
    isCreating: mutations.create.isPending,
    isUpdating: mutations.update.isPending,
    isDeleting: mutations.delete.isPending,
    setPage,
    setFilters,
    selectItem,
    resetFilters: store.resetFilters,
    refetch: listQuery.refetch as () => void,
  };
}

/**
 * 建立 Detail Hook 的核心邏輯
 *
 * TStore: Store 中的實體型別
 * TQuery: Query 回傳的實體型別（可能是子集）
 */
export function useEntityDetailCore<TStore, TQuery = TStore>(
  store: { setSelectedItem: (item: TStore | null) => void; selectedItem: TStore | null },
  detailQuery: UseQueryResult<TQuery>,
) {
  useEffect(() => {
    if (detailQuery.data) {
      store.setSelectedItem(detailQuery.data as unknown as TStore);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- store is a stable Zustand store reference
  }, [detailQuery.data]);

  return {
    data: (detailQuery.data as unknown as TStore) || store.selectedItem,
    isLoading: detailQuery.isLoading,
    isError: detailQuery.isError,
    error: detailQuery.error,
    refetch: detailQuery.refetch,
  };
}
