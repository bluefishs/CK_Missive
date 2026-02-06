/**
 * Agencies Store Unit Tests
 *
 * Tests the agencies store created via createEntityStore factory,
 * including agency-specific initial filters and the compat wrapper
 * with AgencyWithStats / Agency type casting.
 *
 * @version 1.0.0
 * @date 2026-02-06
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useAgenciesStore, useAgenciesStoreCompat } from '../agencies';
import { createMockAgencyWithStats } from '../../test/testUtils';

describe('useAgenciesStore', () => {
  beforeEach(() => {
    useAgenciesStore.getState().clearAll();
  });

  it('應該使用正確的初始篩選條件建立 Store', () => {
    const { filters } = useAgenciesStore.getState();

    expect(filters).toEqual({
      search: '',
      agency_type: undefined,
    });
  });

  it('應該正確管理機關列表（含統計資料）', () => {
    const agency1 = createMockAgencyWithStats({
      id: 1,
      agency_name: '桃園市政府',
      document_count: 15,
      sent_count: 5,
      received_count: 10,
      primary_type: 'receiver',
    });
    const agency2 = createMockAgencyWithStats({
      id: 2,
      agency_name: '新北市政府',
      document_count: 8,
      primary_type: 'sender',
    });

    useAgenciesStore.getState().setItems([agency1, agency2]);

    const items = useAgenciesStore.getState().items;
    expect(items).toHaveLength(2);
    expect(items[0]!.document_count).toBe(15);
    expect(items[0]!.primary_type).toBe('receiver');
    expect(items[1]!.agency_name).toBe('新北市政府');
  });

  it('應該支援 agency_type 篩選', () => {
    useAgenciesStore.getState().setFilters({ agency_type: '地方機關' });

    expect(useAgenciesStore.getState().filters.agency_type).toBe('地方機關');
    expect(useAgenciesStore.getState().pagination.page).toBe(1);
  });

  it('應該正確更新機關統計資料', () => {
    const agency = createMockAgencyWithStats({
      id: 5,
      agency_name: '測試機關',
      document_count: 0,
    });
    useAgenciesStore.getState().setItems([agency]);

    useAgenciesStore.getState().updateItem(5, { document_count: 10, primary_type: 'both' });

    const updated = useAgenciesStore.getState().items.find((a) => a.id === 5);
    expect(updated?.document_count).toBe(10);
    expect(updated?.primary_type).toBe('both');
  });
});

describe('useAgenciesStoreCompat', () => {
  beforeEach(() => {
    useAgenciesStore.getState().clearAll();
  });

  it('應該提供舊版 API 別名 (agencies / selectedAgency)', () => {
    const agency = createMockAgencyWithStats({
      id: 10,
      agency_name: '相容性測試機關',
    });
    useAgenciesStore.getState().setItems([agency]);
    useAgenciesStore.getState().setSelectedItem(agency);

    const state = useAgenciesStore.getState();
    expect(state.items).toHaveLength(1);
    expect(state.selectedItem?.agency_name).toBe('相容性測試機關');
  });

  it('selectedAgency 應該保留 AgencyWithStats 的統計欄位', () => {
    const agency = createMockAgencyWithStats({
      id: 20,
      agency_name: '統計測試',
      document_count: 42,
      sent_count: 20,
      received_count: 22,
      last_activity: '2026-01-15T10:00:00Z',
      primary_type: 'both',
    });
    useAgenciesStore.getState().setSelectedItem(agency);

    const selected = useAgenciesStore.getState().selectedItem;
    expect(selected?.document_count).toBe(42);
    expect(selected?.sent_count).toBe(20);
    expect(selected?.received_count).toBe(22);
    expect(selected?.last_activity).toBe('2026-01-15T10:00:00Z');
    expect(selected?.primary_type).toBe('both');
  });

  it('addAgency / removeAgency 應該正確操作', () => {
    const agency = createMockAgencyWithStats({ id: 30, agency_name: '新增機關' });
    useAgenciesStore.getState().setPagination({ total: 0 });

    useAgenciesStore.getState().addItem(agency);
    expect(useAgenciesStore.getState().items).toHaveLength(1);
    expect(useAgenciesStore.getState().pagination.total).toBe(1);

    useAgenciesStore.getState().removeItem(30);
    expect(useAgenciesStore.getState().items).toHaveLength(0);
    expect(useAgenciesStore.getState().pagination.total).toBe(0);
  });
});
