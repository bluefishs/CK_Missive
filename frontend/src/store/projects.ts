/**
 * 專案管理 Store
 *
 * 使用通用 Store Factory 建立，減少重複程式碼。
 *
 * @version 2.0.0
 * @date 2026-01-21
 */

import type { Project } from '../types/api';
import { createEntityStore, type BaseFilter, type EntityState } from './createEntityStore';

// ============================================================================
// 型別定義
// ============================================================================

/** 專案篩選條件 */
export interface ProjectFilter extends BaseFilter {
  search?: string;
  year?: number;
  category?: string;
  status?: string;
}

/** 專案 Store 狀態型別 */
export type ProjectsState = EntityState<Project, ProjectFilter>;

// ============================================================================
// Store 建立
// ============================================================================

const initialFilters: ProjectFilter = {
  search: '',
  year: undefined,
  category: undefined,
  status: undefined,
};

/**
 * 專案 Store
 *
 * @example
 * ```typescript
 * const {
 *   items: projects,
 *   selectedItem: selectedProject,
 *   filters,
 *   pagination,
 *   setItems,
 *   addItem,
 *   updateItem,
 *   removeItem,
 *   setFilters,
 *   resetFilters,
 * } = useProjectsStore();
 * ```
 */
export const useProjectsStore = createEntityStore<Project, ProjectFilter>({
  name: 'projects-store',
  initialFilters,
});

// ============================================================================
// 相容性別名（向後相容舊 API）
// ============================================================================

/**
 * 專案 Store 相容性包裝
 * 提供舊版 API 的別名，方便漸進式遷移
 */
export function useProjectsStoreCompat() {
  const store = useProjectsStore();
  return {
    // 舊版別名
    projects: store.items,
    selectedProject: store.selectedItem,
    setProjects: store.setItems,
    setSelectedProject: store.setSelectedItem,
    addProject: store.addItem,
    updateProject: store.updateItem,
    removeProject: store.removeItem,
    // 新版 API
    ...store,
  };
}
