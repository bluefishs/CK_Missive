/**
 * Store 統一導出
 *
 * @version 3.1.0
 * @date 2026-01-21
 *
 * 提供統一的狀態管理入口，基於 Zustand 實現
 * 包含通用 Store Factory 和各實體 Store
 */

// ============================================================================
// 通用 Store Factory
// ============================================================================

export { createEntityStore } from './createEntityStore';
export type {
  BaseEntity,
  BaseFilter,
  PaginationState,
  EntityState,
  EntityStoreConfig,
} from './createEntityStore';

// ============================================================================
// 公文管理 Store
// ============================================================================

export { useDocumentsStore, useDocumentsStoreCompat } from './documents';
export type { DocumentsState } from './documents';

// ============================================================================
// 專案管理 Store
// ============================================================================

export { useProjectsStore, useProjectsStoreCompat } from './projects';
export type { ProjectsState, ProjectFilter } from './projects';

// ============================================================================
// 機關管理 Store
// ============================================================================

export { useAgenciesStore, useAgenciesStoreCompat } from './agencies';
export type { AgenciesState, AgencyFilter } from './agencies';

// ============================================================================
// 廠商管理 Store
// ============================================================================

export { useVendorsStore, useVendorsStoreCompat } from './vendors';
export type { VendorsState, VendorFilter } from './vendors';
