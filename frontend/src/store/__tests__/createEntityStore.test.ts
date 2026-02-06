/**
 * createEntityStore Factory Unit Tests
 *
 * Tests the generic store factory that powers all entity stores.
 * Covers initial state, CRUD actions, filter/pagination management,
 * and the clearAll reset behaviour.
 *
 * @version 1.0.0
 * @date 2026-02-06
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { createEntityStore, type BaseEntity, type BaseFilter } from '../createEntityStore';

// ============================================================================
// Test Entity & Filter Types
// ============================================================================

interface TestEntity extends BaseEntity {
  id: number;
  name: string;
  value: number;
}

interface TestFilter extends BaseFilter {
  search?: string;
  category?: string;
}

// ============================================================================
// Store Setup
// ============================================================================

const initialFilters: TestFilter = {
  search: '',
  category: undefined,
};

const useTestStore = createEntityStore<TestEntity, TestFilter>({
  name: 'test-entity-store',
  initialFilters,
});

// Helper to create test entities
function makeEntity(id: number, name?: string, value?: number): TestEntity {
  return { id, name: name ?? `Entity ${id}`, value: value ?? id * 10 };
}

// ============================================================================
// Tests
// ============================================================================

describe('createEntityStore', () => {
  beforeEach(() => {
    useTestStore.getState().clearAll();
  });

  // --------------------------------------------------------------------------
  // Initial State
  // --------------------------------------------------------------------------

  describe('初始狀態', () => {
    it('應該正確初始化空狀態', () => {
      const state = useTestStore.getState();

      expect(state.items).toEqual([]);
      expect(state.selectedItem).toBeNull();
      expect(state.loading).toBe(false);
      expect(state.filters).toEqual(initialFilters);
      expect(state.pagination).toEqual({
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 0,
      });
    });

    it('應該支援自訂初始分頁', () => {
      const useCustomStore = createEntityStore<TestEntity, TestFilter>({
        name: 'custom-pagination-store',
        initialFilters,
        initialPagination: { limit: 50 },
      });

      const state = useCustomStore.getState();

      expect(state.pagination.limit).toBe(50);
      expect(state.pagination.page).toBe(1);
      expect(state.pagination.total).toBe(0);
    });
  });

  // --------------------------------------------------------------------------
  // setItems / setSelectedItem
  // --------------------------------------------------------------------------

  describe('setItems / setSelectedItem', () => {
    it('應該正確設定 items 列表', () => {
      const entities = [makeEntity(1), makeEntity(2), makeEntity(3)];

      useTestStore.getState().setItems(entities);

      expect(useTestStore.getState().items).toEqual(entities);
      expect(useTestStore.getState().items).toHaveLength(3);
    });

    it('應該正確設定 selectedItem', () => {
      const entity = makeEntity(5, 'Selected');

      useTestStore.getState().setSelectedItem(entity);

      expect(useTestStore.getState().selectedItem).toEqual(entity);
    });

    it('應該允許清除 selectedItem 為 null', () => {
      useTestStore.getState().setSelectedItem(makeEntity(1));
      useTestStore.getState().setSelectedItem(null);

      expect(useTestStore.getState().selectedItem).toBeNull();
    });
  });

  // --------------------------------------------------------------------------
  // addItem
  // --------------------------------------------------------------------------

  describe('addItem', () => {
    it('應該將新項目加到列表開頭', () => {
      const existing = makeEntity(1, 'Old');
      const newItem = makeEntity(2, 'New');

      useTestStore.getState().setItems([existing]);
      useTestStore.getState().addItem(newItem);

      const items = useTestStore.getState().items;
      expect(items).toHaveLength(2);
      expect(items[0]).toEqual(newItem);
      expect(items[1]).toEqual(existing);
    });

    it('應該在新增時遞增 total', () => {
      useTestStore.getState().setPagination({ total: 5 });
      useTestStore.getState().addItem(makeEntity(99));

      expect(useTestStore.getState().pagination.total).toBe(6);
    });
  });

  // --------------------------------------------------------------------------
  // updateItem
  // --------------------------------------------------------------------------

  describe('updateItem', () => {
    it('應該根據 id 更新指定項目', () => {
      useTestStore.getState().setItems([
        makeEntity(1, 'A', 10),
        makeEntity(2, 'B', 20),
      ]);

      useTestStore.getState().updateItem(1, { name: 'Updated A', value: 999 });

      const item = useTestStore.getState().items.find((i) => i.id === 1);
      expect(item?.name).toBe('Updated A');
      expect(item?.value).toBe(999);
    });

    it('不應影響其他項目', () => {
      useTestStore.getState().setItems([
        makeEntity(1, 'A', 10),
        makeEntity(2, 'B', 20),
      ]);

      useTestStore.getState().updateItem(1, { name: 'Updated A' });

      const other = useTestStore.getState().items.find((i) => i.id === 2);
      expect(other?.name).toBe('B');
      expect(other?.value).toBe(20);
    });

    it('應該同步更新 selectedItem（如果 id 匹配）', () => {
      const entity = makeEntity(3, 'Before');
      useTestStore.getState().setSelectedItem(entity);
      useTestStore.getState().setItems([entity]);

      useTestStore.getState().updateItem(3, { name: 'After' });

      expect(useTestStore.getState().selectedItem?.name).toBe('After');
    });

    it('不應影響 selectedItem（如果 id 不匹配）', () => {
      useTestStore.getState().setSelectedItem(makeEntity(1, 'Selected'));
      useTestStore.getState().setItems([makeEntity(1), makeEntity(2)]);

      useTestStore.getState().updateItem(2, { name: 'Changed' });

      expect(useTestStore.getState().selectedItem?.name).toBe('Selected');
    });
  });

  // --------------------------------------------------------------------------
  // removeItem
  // --------------------------------------------------------------------------

  describe('removeItem', () => {
    it('應該根據 id 移除項目', () => {
      useTestStore.getState().setItems([
        makeEntity(1),
        makeEntity(2),
        makeEntity(3),
      ]);

      useTestStore.getState().removeItem(2);

      const ids = useTestStore.getState().items.map((i) => i.id);
      expect(ids).toEqual([1, 3]);
    });

    it('應該在移除時遞減 total（不低於 0）', () => {
      useTestStore.getState().setPagination({ total: 3 });
      useTestStore.getState().setItems([makeEntity(1), makeEntity(2), makeEntity(3)]);

      useTestStore.getState().removeItem(1);

      expect(useTestStore.getState().pagination.total).toBe(2);
    });

    it('total 不應低於 0', () => {
      useTestStore.getState().setPagination({ total: 0 });

      useTestStore.getState().removeItem(999);

      expect(useTestStore.getState().pagination.total).toBe(0);
    });

    it('應該在移除匹配的 selectedItem 時清除為 null', () => {
      useTestStore.getState().setSelectedItem(makeEntity(5));
      useTestStore.getState().setItems([makeEntity(5)]);

      useTestStore.getState().removeItem(5);

      expect(useTestStore.getState().selectedItem).toBeNull();
    });

    it('不應清除不匹配的 selectedItem', () => {
      useTestStore.getState().setSelectedItem(makeEntity(1, 'Keep'));
      useTestStore.getState().setItems([makeEntity(1), makeEntity(2)]);

      useTestStore.getState().removeItem(2);

      expect(useTestStore.getState().selectedItem?.id).toBe(1);
    });
  });

  // --------------------------------------------------------------------------
  // setFilters / resetFilters
  // --------------------------------------------------------------------------

  describe('setFilters / resetFilters', () => {
    it('應該合併篩選條件', () => {
      useTestStore.getState().setFilters({ search: 'hello' });

      expect(useTestStore.getState().filters.search).toBe('hello');
      expect(useTestStore.getState().filters.category).toBeUndefined();
    });

    it('應該在設定篩選條件時重置頁碼為 1', () => {
      useTestStore.getState().setPagination({ page: 5 });

      useTestStore.getState().setFilters({ category: 'A' });

      expect(useTestStore.getState().pagination.page).toBe(1);
    });

    it('應該正確重置所有篩選條件', () => {
      useTestStore.getState().setFilters({ search: 'test', category: 'B' });

      useTestStore.getState().resetFilters();

      expect(useTestStore.getState().filters).toEqual(initialFilters);
      expect(useTestStore.getState().pagination.page).toBe(1);
    });
  });

  // --------------------------------------------------------------------------
  // setPagination
  // --------------------------------------------------------------------------

  describe('setPagination', () => {
    it('應該合併分頁設定', () => {
      useTestStore.getState().setPagination({ page: 3, total: 100 });

      const { pagination } = useTestStore.getState();
      expect(pagination.page).toBe(3);
      expect(pagination.total).toBe(100);
      expect(pagination.limit).toBe(10); // default preserved
    });
  });

  // --------------------------------------------------------------------------
  // clearAll
  // --------------------------------------------------------------------------

  describe('clearAll', () => {
    it('應該重置所有狀態至初始值', () => {
      // Dirty the store
      useTestStore.getState().setItems([makeEntity(1), makeEntity(2)]);
      useTestStore.getState().setSelectedItem(makeEntity(1));
      useTestStore.getState().setFilters({ search: 'dirty', category: 'X' });
      useTestStore.getState().setPagination({ page: 5, total: 200, limit: 50 });
      useTestStore.getState().setLoading(true);

      // Reset
      useTestStore.getState().clearAll();

      const state = useTestStore.getState();
      expect(state.items).toEqual([]);
      expect(state.selectedItem).toBeNull();
      expect(state.filters).toEqual(initialFilters);
      expect(state.loading).toBe(false);
      expect(state.pagination).toEqual({
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 0,
      });
    });
  });
});
