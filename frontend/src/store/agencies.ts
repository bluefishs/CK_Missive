/**
 * 機關管理 Store
 *
 * 使用通用 Store Factory 建立，減少重複程式碼。
 *
 * @version 2.0.0
 * @date 2026-01-21
 */

import type { Agency, AgencyWithStats } from '../types/api';
import { createEntityStore, type BaseFilter, type EntityState } from './createEntityStore';

// ============================================================================
// 型別定義
// ============================================================================

/** 機關篩選條件 */
export interface AgencyFilter extends BaseFilter {
  search?: string;
  agency_type?: string;
}

/** 機關 Store 狀態型別 */
export type AgenciesState = EntityState<AgencyWithStats, AgencyFilter>;

// ============================================================================
// Store 建立
// ============================================================================

const initialFilters: AgencyFilter = {
  search: '',
  agency_type: undefined,
};

/**
 * 機關 Store
 *
 * @example
 * ```typescript
 * const {
 *   items: agencies,
 *   selectedItem: selectedAgency,
 *   filters,
 *   pagination,
 *   setItems,
 *   addItem,
 *   updateItem,
 *   removeItem,
 *   setFilters,
 *   resetFilters,
 * } = useAgenciesStore();
 * ```
 */
export const useAgenciesStore = createEntityStore<AgencyWithStats, AgencyFilter>({
  name: 'agencies-store',
  initialFilters,
});

// ============================================================================
// 相容性別名（向後相容舊 API）
// ============================================================================

/**
 * 機關 Store 相容性包裝
 * 提供舊版 API 的別名，方便漸進式遷移
 */
export function useAgenciesStoreCompat() {
  const store = useAgenciesStore();
  return {
    // 舊版別名
    agencies: store.items,
    selectedAgency: store.selectedItem as Agency | null,
    setAgencies: store.setItems,
    setSelectedAgency: (agency: Agency | null) => store.setSelectedItem(agency as AgencyWithStats | null),
    addAgency: store.addItem,
    updateAgency: store.updateItem,
    removeAgency: store.removeItem,
    // 新版 API
    ...store,
  };
}
