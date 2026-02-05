/**
 * Hooks 模組統一匯出
 *
 * 分層架構 (詳見 README.md):
 * - business/ : 業務邏輯 Hooks (三層: Query → State → Business)
 * - system/   : 系統功能 Hooks (calendar, dashboard, admin)
 * - utility/  : 工具類 Hooks (auth, navigation, responsive)
 *
 * 命名規則:
 * - 層 1 Queries: use{Entity}Query, use{Entity}s
 * - 層 2 State: use{Entity}WithStore
 * - 層 3 Business: use{Entity}{Action}
 *
 * @version 2.2.0
 * @date 2026-02-06
 * @see README.md 完整分層規範
 */

// ============================================================================
// 業務邏輯 Hooks
// ============================================================================
export * from './business';

// ============================================================================
// 系統功能 Hooks
// ============================================================================
export * from './system';

// ============================================================================
// 工具類 Hooks
// ============================================================================
export * from './utility';
