/**
 * Projects Store Unit Tests
 *
 * Tests the projects store created via createEntityStore factory,
 * including project-specific initial filters and the compat wrapper.
 *
 * @version 1.0.0
 * @date 2026-02-06
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useProjectsStore } from '../projects';
import { createMockProject } from '../../test/testUtils';

describe('useProjectsStore', () => {
  beforeEach(() => {
    useProjectsStore.getState().clearAll();
  });

  it('應該使用正確的初始篩選條件建立 Store', () => {
    const { filters } = useProjectsStore.getState();

    expect(filters).toEqual({
      search: '',
      year: undefined,
      category: undefined,
      status: undefined,
    });
  });

  it('應該正確管理專案列表和篩選', () => {
    const project = createMockProject({
      id: 1,
      project_name: '桃園測量案',
      year: 2026,
      status: 'in_progress',
    });

    useProjectsStore.getState().setItems([project]);
    useProjectsStore.getState().setFilters({ year: 2026, status: 'in_progress' });

    expect(useProjectsStore.getState().items).toHaveLength(1);
    expect(useProjectsStore.getState().filters.year).toBe(2026);
    expect(useProjectsStore.getState().filters.status).toBe('in_progress');
    expect(useProjectsStore.getState().pagination.page).toBe(1);
  });

  it('應該正確新增專案並更新 total', () => {
    useProjectsStore.getState().setPagination({ total: 10 });

    const newProject = createMockProject({ id: 99, project_name: '新專案' });
    useProjectsStore.getState().addItem(newProject);

    expect(useProjectsStore.getState().items[0]!.project_name).toBe('新專案');
    expect(useProjectsStore.getState().pagination.total).toBe(11);
  });

  it('應該正確重置篩選條件', () => {
    useProjectsStore.getState().setFilters({
      search: 'test',
      year: 2025,
      category: '01委辦案件',
      status: 'completed',
    });

    useProjectsStore.getState().resetFilters();

    expect(useProjectsStore.getState().filters).toEqual({
      search: '',
      year: undefined,
      category: undefined,
      status: undefined,
    });
  });
});

describe('useProjectsStoreCompat', () => {
  beforeEach(() => {
    useProjectsStore.getState().clearAll();
  });

  it('應該提供舊版 API 別名 (projects / selectedProject)', () => {
    const project = createMockProject({ id: 5, project_name: '相容性測試專案' });
    useProjectsStore.getState().setItems([project]);
    useProjectsStore.getState().setSelectedItem(project);

    const state = useProjectsStore.getState();
    expect(state.items).toHaveLength(1);
    expect(state.items[0]!.project_name).toBe('相容性測試專案');
    expect(state.selectedItem?.id).toBe(5);
  });

  it('updateProject / removeProject 應該正確操作', () => {
    const project = createMockProject({ id: 20, project_name: '原始名稱' });
    useProjectsStore.getState().setItems([project]);
    useProjectsStore.getState().setPagination({ total: 1 });

    // Update
    useProjectsStore.getState().updateItem(20, { project_name: '修改名稱' });
    expect(useProjectsStore.getState().items[0]!.project_name).toBe('修改名稱');

    // Remove
    useProjectsStore.getState().removeItem(20);
    expect(useProjectsStore.getState().items).toHaveLength(0);
    expect(useProjectsStore.getState().pagination.total).toBe(0);
  });
});
