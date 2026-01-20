/**
 * Hooks 模組統一匯出
 *
 * @version 2.0.0
 * @date 2026-01-19
 */

// 業務邏輯 Hooks
export * from './useDocuments';
export * from './useProjects';
export * from './useVendors';
export * from './useAgencies';

// 整合 Store 的 Hooks (React Query + Zustand)
export * from './useProjectsWithStore';
export * from './useAgenciesWithStore';
export * from './useVendorsWithStore';
export * from './useDocumentsWithStore';

// 效能與統計 Hooks
export * from './usePerformance';
export * from './useDocumentStats';

// 導航 Hooks
export * from './useAppNavigation';

// 認證與權限 Hooks
export * from './useAuthGuard';
export * from './useAdminUsers';

// 儀表板 Hooks
export * from './useDashboard';

// 行事曆 Hooks
export * from './useCalendar';

// 響應式設計 Hooks
export * from './useResponsive';
