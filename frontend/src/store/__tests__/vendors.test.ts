/**
 * Vendors Store Unit Tests
 *
 * Tests the vendors store created via createEntityStore factory,
 * including vendor-specific initial filters and the compat wrapper.
 *
 * @version 1.0.0
 * @date 2026-02-06
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useVendorsStore } from '../vendors';
import { createMockVendor } from '../../test/testUtils';

describe('useVendorsStore', () => {
  beforeEach(() => {
    useVendorsStore.getState().clearAll();
  });

  it('應該使用正確的初始篩選條件建立 Store', () => {
    const { filters } = useVendorsStore.getState();

    expect(filters).toEqual({
      search: '',
      business_type: undefined,
    });
  });

  it('應該正確管理廠商列表', () => {
    const vendor1 = createMockVendor({ id: 1, vendor_name: '大地測量公司' });
    const vendor2 = createMockVendor({ id: 2, vendor_name: '精密測量公司' });

    useVendorsStore.getState().setItems([vendor1, vendor2]);

    expect(useVendorsStore.getState().items).toHaveLength(2);
    expect(useVendorsStore.getState().items[0]!.vendor_name).toBe('大地測量公司');
  });

  it('應該支援 business_type 篩選', () => {
    useVendorsStore.getState().setFilters({ business_type: '測量業務' });

    expect(useVendorsStore.getState().filters.business_type).toBe('測量業務');
    expect(useVendorsStore.getState().pagination.page).toBe(1);
  });

  it('應該正確更新廠商資料', () => {
    const vendor = createMockVendor({ id: 10, vendor_name: '舊名稱', rating: 3 });
    useVendorsStore.getState().setItems([vendor]);

    useVendorsStore.getState().updateItem(10, { vendor_name: '新名稱', rating: 5 });

    const updated = useVendorsStore.getState().items.find((v) => v.id === 10);
    expect(updated?.vendor_name).toBe('新名稱');
    expect(updated?.rating).toBe(5);
  });
});

describe('useVendorsStoreCompat', () => {
  beforeEach(() => {
    useVendorsStore.getState().clearAll();
  });

  it('應該提供舊版 API 別名 (vendors / selectedVendor)', () => {
    const vendor = createMockVendor({ id: 3, vendor_name: '相容性測試廠商' });
    useVendorsStore.getState().setItems([vendor]);
    useVendorsStore.getState().setSelectedItem(vendor);

    const state = useVendorsStore.getState();
    expect(state.items).toHaveLength(1);
    expect(state.selectedItem?.vendor_name).toBe('相容性測試廠商');
  });

  it('addVendor / removeVendor 應該正確操作', () => {
    useVendorsStore.getState().setPagination({ total: 0 });

    const vendor = createMockVendor({ id: 50, vendor_name: '新增廠商' });
    useVendorsStore.getState().addItem(vendor);

    expect(useVendorsStore.getState().items).toHaveLength(1);
    expect(useVendorsStore.getState().pagination.total).toBe(1);

    useVendorsStore.getState().removeItem(50);

    expect(useVendorsStore.getState().items).toHaveLength(0);
    expect(useVendorsStore.getState().pagination.total).toBe(0);
  });
});
