/**
 * 機關管理 Store
 * 基於 Zustand 的機關狀態管理
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Agency, AgencyWithStats } from '../types/api';

/** 機關篩選條件 */
export interface AgencyFilter {
  search?: string;
  agency_type?: string;
}

interface AgenciesState {
  // 機關列表
  agencies: AgencyWithStats[];

  // 當前選中的機關
  selectedAgency: Agency | null;

  // 篩選條件
  filters: AgencyFilter;

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
  setAgencies: (agencies: AgencyWithStats[]) => void;
  setSelectedAgency: (agency: Agency | null) => void;
  setFilters: (filters: Partial<AgencyFilter>) => void;
  setPagination: (pagination: Partial<AgenciesState['pagination']>) => void;
  setLoading: (loading: boolean) => void;
  addAgency: (agency: AgencyWithStats) => void;
  updateAgency: (id: number, agency: Partial<Agency>) => void;
  removeAgency: (id: number) => void;
  resetFilters: () => void;
}

const initialFilters: AgencyFilter = {
  search: '',
};

export const useAgenciesStore = create<AgenciesState>()(
  devtools(
    (set, get) => ({
      // Initial state
      agencies: [],
      selectedAgency: null,
      filters: initialFilters,
      pagination: {
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 0,
      },
      loading: false,

      // Actions
      setAgencies: (agencies) => set({ agencies }),

      setSelectedAgency: (selectedAgency) => set({ selectedAgency }),

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

      addAgency: (agency) =>
        set((state) => ({
          agencies: [agency, ...state.agencies],
        })),

      updateAgency: (id, updates) =>
        set((state) => ({
          agencies: state.agencies.map((a) =>
            a.id === id ? ({ ...a, ...updates } as AgencyWithStats) : a
          ),
          selectedAgency:
            state.selectedAgency?.id === id
              ? ({ ...state.selectedAgency, ...updates } as Agency)
              : state.selectedAgency,
        })),

      removeAgency: (id) =>
        set((state) => ({
          agencies: state.agencies.filter((a) => a.id !== id),
          selectedAgency:
            state.selectedAgency?.id === id ? null : state.selectedAgency,
        })),

      resetFilters: () =>
        set({
          filters: initialFilters,
          pagination: { ...get().pagination, page: 1 },
        }),
    }),
    { name: 'agencies-store' }
  )
);

export type { AgenciesState };
