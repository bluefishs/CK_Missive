/**
 * 通用實體 Store Factory
 *
 * 提供統一的 CRUD 狀態管理模式，消除各實體 Store 的重複程式碼。
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import { create, StateCreator } from 'zustand';
import { devtools } from 'zustand/middleware';

// ============================================================================
// 型別定義
// ============================================================================

/** 基礎實體型別（必須有 id 欄位） */
export interface BaseEntity {
  id: number;
}

/** 分頁資訊 */
export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

/** 通用篩選條件基礎型別 */
export interface BaseFilter {
  search?: string;
}

/** 實體 Store 狀態 */
export interface EntityState<T extends BaseEntity, F extends BaseFilter = BaseFilter> {
  // 資料
  items: T[];
  selectedItem: T | null;

  // 篩選與分頁
  filters: F;
  pagination: PaginationState;

  // 狀態
  loading: boolean;

  // Actions - 資料操作
  setItems: (items: T[]) => void;
  setSelectedItem: (item: T | null) => void;
  addItem: (item: T) => void;
  updateItem: (id: number, updates: Partial<T>) => void;
  removeItem: (id: number) => void;

  // Actions - 篩選與分頁
  setFilters: (filters: Partial<F>) => void;
  setPagination: (pagination: Partial<PaginationState>) => void;
  resetFilters: () => void;

  // Actions - 狀態
  setLoading: (loading: boolean) => void;

  // Actions - 批次操作
  clearAll: () => void;
}

/** Store Factory 配置選項 */
export interface EntityStoreConfig<F extends BaseFilter> {
  /** Store 名稱（用於 devtools） */
  name: string;
  /** 初始篩選條件 */
  initialFilters: F;
  /** 初始分頁設定 */
  initialPagination?: Partial<PaginationState>;
}

// ============================================================================
// 預設值
// ============================================================================

const DEFAULT_PAGINATION: PaginationState = {
  page: 1,
  limit: 10,
  total: 0,
  totalPages: 0,
};

// ============================================================================
// Store Factory
// ============================================================================

/**
 * 建立通用實體 Store
 *
 * @example
 * ```typescript
 * // 定義篩選條件型別
 * interface VendorFilter extends BaseFilter {
 *   business_type?: string;
 * }
 *
 * // 建立 Store
 * export const useVendorsStore = createEntityStore<Vendor, VendorFilter>({
 *   name: 'vendors-store',
 *   initialFilters: { search: '' },
 * });
 *
 * // 使用 Store
 * const { items, setItems, addItem, updateItem, removeItem } = useVendorsStore();
 * ```
 */
export function createEntityStore<
  T extends BaseEntity,
  F extends BaseFilter = BaseFilter
>(config: EntityStoreConfig<F>) {
  const { name, initialFilters, initialPagination } = config;

  const storeCreator: StateCreator<EntityState<T, F>> = (set, get) => ({
    // Initial state
    items: [],
    selectedItem: null,
    filters: initialFilters,
    pagination: { ...DEFAULT_PAGINATION, ...initialPagination },
    loading: false,

    // Actions - 資料操作
    setItems: (items) => set({ items }),

    setSelectedItem: (selectedItem) => set({ selectedItem }),

    addItem: (item) =>
      set((state) => ({
        items: [item, ...state.items],
        pagination: {
          ...state.pagination,
          total: state.pagination.total + 1,
        },
      })),

    updateItem: (id, updates) =>
      set((state) => ({
        items: state.items.map((item) =>
          item.id === id ? ({ ...item, ...updates } as T) : item
        ),
        selectedItem:
          state.selectedItem?.id === id
            ? ({ ...state.selectedItem, ...updates } as T)
            : state.selectedItem,
      })),

    removeItem: (id) =>
      set((state) => ({
        items: state.items.filter((item) => item.id !== id),
        selectedItem: state.selectedItem?.id === id ? null : state.selectedItem,
        pagination: {
          ...state.pagination,
          total: Math.max(0, state.pagination.total - 1),
        },
      })),

    // Actions - 篩選與分頁
    setFilters: (newFilters) =>
      set((state) => ({
        filters: { ...state.filters, ...newFilters } as F,
        pagination: { ...state.pagination, page: 1 }, // 重置頁碼
      })),

    setPagination: (newPagination) =>
      set((state) => ({
        pagination: { ...state.pagination, ...newPagination },
      })),

    resetFilters: () =>
      set({
        filters: initialFilters,
        pagination: { ...get().pagination, page: 1 },
      }),

    // Actions - 狀態
    setLoading: (loading) => set({ loading }),

    // Actions - 批次操作
    clearAll: () =>
      set({
        items: [],
        selectedItem: null,
        filters: initialFilters,
        pagination: { ...DEFAULT_PAGINATION, ...initialPagination },
        loading: false,
      }),
  });

  return create<EntityState<T, F>>()(devtools(storeCreator, { name }));
}

// ============================================================================
// 匯出
// ============================================================================

export type { PaginationState as Pagination };
