/**
 * 廠商管理 Store
 * 基於 Zustand 的廠商狀態管理
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Vendor } from '../types/api';

/** 廠商篩選條件 */
export interface VendorFilter {
  search?: string;
  business_type?: string;
}

interface VendorsState {
  // 廠商列表
  vendors: Vendor[];

  // 當前選中的廠商
  selectedVendor: Vendor | null;

  // 篩選條件
  filters: VendorFilter;

  // 分頁資訊
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };

  // 載入狀態
  loading: boolean;

  // Actions
  setVendors: (vendors: Vendor[]) => void;
  setSelectedVendor: (vendor: Vendor | null) => void;
  setFilters: (filters: Partial<VendorFilter>) => void;
  setPagination: (pagination: Partial<VendorsState['pagination']>) => void;
  setLoading: (loading: boolean) => void;
  addVendor: (vendor: Vendor) => void;
  updateVendor: (id: number, vendor: Partial<Vendor>) => void;
  removeVendor: (id: number) => void;
  resetFilters: () => void;
}

const initialFilters: VendorFilter = {
  search: '',
};

export const useVendorsStore = create<VendorsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      vendors: [],
      selectedVendor: null,
      filters: initialFilters,
      pagination: {
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 0,
      },
      loading: false,

      // Actions
      setVendors: (vendors) => set({ vendors }),

      setSelectedVendor: (selectedVendor) => set({ selectedVendor }),

      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
          pagination: { ...state.pagination, page: 1 },
        })),

      setPagination: (newPagination) =>
        set((state) => ({
          pagination: { ...state.pagination, ...newPagination },
        })),

      setLoading: (loading) => set({ loading }),

      addVendor: (vendor) =>
        set((state) => ({
          vendors: [vendor, ...state.vendors],
        })),

      updateVendor: (id, updates) =>
        set((state) => ({
          vendors: state.vendors.map((v) =>
            v.id === id ? ({ ...v, ...updates } as Vendor) : v
          ),
          selectedVendor:
            state.selectedVendor?.id === id
              ? ({ ...state.selectedVendor, ...updates } as Vendor)
              : state.selectedVendor,
        })),

      removeVendor: (id) =>
        set((state) => ({
          vendors: state.vendors.filter((v) => v.id !== id),
          selectedVendor:
            state.selectedVendor?.id === id ? null : state.selectedVendor,
        })),

      resetFilters: () =>
        set({
          filters: initialFilters,
          pagination: { ...get().pagination, page: 1 },
        }),
    }),
    { name: 'vendors-store' }
  )
);

export type { VendorsState };
