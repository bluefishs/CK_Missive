/**
 * Store 統一導出
 *
 * @version 3.0.0
 * @date 2026-01-19
 *
 * 提供統一的狀態管理入口，基於 Zustand 實現
 */

// 公文管理 Store
export { useDocumentsStore } from './documents';
export type { DocumentsState } from './documents';

// 專案管理 Store
export { useProjectsStore } from './projects';
export type { ProjectsState, ProjectFilter } from './projects';

// 機關管理 Store
export { useAgenciesStore } from './agencies';
export type { AgenciesState, AgencyFilter } from './agencies';

// 廠商管理 Store
export { useVendorsStore } from './vendors';
export type { VendorsState, VendorFilter } from './vendors';
