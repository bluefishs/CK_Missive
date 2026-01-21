/**
 * 廠商管理 Store
 *
 * 使用通用 Store Factory 建立，減少重複程式碼。
 *
 * @version 2.0.0
 * @date 2026-01-21
 */

import type { Vendor } from '../types/api';
import { createEntityStore, type BaseFilter, type EntityState } from './createEntityStore';

// ============================================================================
// 型別定義
// ============================================================================

/** 廠商篩選條件 */
export interface VendorFilter extends BaseFilter {
  search?: string;
  business_type?: string;
}

/** 廠商 Store 狀態型別 */
export type VendorsState = EntityState<Vendor, VendorFilter>;

// ============================================================================
// Store 建立
// ============================================================================

const initialFilters: VendorFilter = {
  search: '',
  business_type: undefined,
};

/**
 * 廠商 Store
 *
 * @example
 * ```typescript
 * const {
 *   items: vendors,
 *   selectedItem: selectedVendor,
 *   filters,
 *   pagination,
 *   setItems,
 *   addItem,
 *   updateItem,
 *   removeItem,
 *   setFilters,
 *   resetFilters,
 * } = useVendorsStore();
 * ```
 */
export const useVendorsStore = createEntityStore<Vendor, VendorFilter>({
  name: 'vendors-store',
  initialFilters,
});

// ============================================================================
// 相容性別名（向後相容舊 API）
// ============================================================================

/**
 * 廠商 Store 相容性包裝
 * 提供舊版 API 的別名，方便漸進式遷移
 */
export function useVendorsStoreCompat() {
  const store = useVendorsStore();
  return {
    // 舊版別名
    vendors: store.items,
    selectedVendor: store.selectedItem,
    setVendors: store.setItems,
    setSelectedVendor: store.setSelectedItem,
    addVendor: store.addItem,
    updateVendor: store.updateItem,
    removeVendor: store.removeItem,
    // 新版 API
    ...store,
  };
}
