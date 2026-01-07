/**
 * 高階元件 (HOC) 模組
 *
 * 提供可重用的元件封裝功能：
 * - withAuth: 認證守衛
 * - withAdminAuth: 管理員認證
 * - withPermission: 權限檢查
 * - withLoading: 載入狀態管理
 *
 * @version 1.0.0
 * @date 2026-01-06
 */

export {
  withAuth,
  withAdminAuth,
  withPermission,
  type WithAuthOptions,
} from './withAuth';

export {
  withLoading,
  useLoadingState,
  type WithLoadingOptions,
  type WithLoadingInjectedProps,
  type LoadingState,
} from './withLoading';
