/**
 * 受保護路由元件
 *
 * 提供統一的路由保護功能
 *
 * @version 1.2.0
 * @date 2026-01-13
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthGuard, Permission } from '../hooks';
import { ROUTES } from './types';

/** 受保護路由選項 */
export interface ProtectedRouteProps {
  /** 子元件 */
  children: React.ReactNode;
  /** 是否需要認證 (預設 true) */
  requireAuth?: boolean;
  /** 需要的角色 */
  roles?: string[];
  /** 需要的權限 */
  permissions?: Permission[];
  /** 重定向路徑 */
  redirectTo?: string;
  /** 是否啟用認證檢查 (用於條件式保護) */
  enabled?: boolean;
}

/**
 * 受保護路由元件
 *
 * 認證檢查邏輯由 useAuthGuard 統一處理：
 * - VITE_AUTH_DISABLED=true 時完全繞過
 * - 內網環境 + auth_provider=internal 時繞過
 * - 其他情況正常檢查
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
  roles = [],
  permissions = [],
  redirectTo = ROUTES.ENTRY,
  enabled = true,
}) => {
  const location = useLocation();
  const {
    isAuthenticated,
    hasRole,
    hasAllPermissions,
    authDisabled,
  } = useAuthGuard({
    requireAuth: enabled && requireAuth,
    roles,
    permissions: permissions as Permission[],
    redirectTo,
  });

  // 未啟用保護，直接渲染
  if (!enabled) {
    return <>{children}</>;
  }

  // 認證被繞過（開發模式或內網已登入），直接渲染
  if (authDisabled) {
    return <>{children}</>;
  }

  // 未認證，重定向到登入頁
  if (requireAuth && !isAuthenticated) {
    const returnUrl = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`${redirectTo}?returnUrl=${returnUrl}`} replace />;
  }

  // 角色不足，重定向到儀表板
  if (roles.length > 0 && !hasRole) {
    console.warn(`[ProtectedRoute] 角色不足: 需要 ${roles.join(' 或 ')}`);
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 權限不足，重定向到儀表板
  if (permissions.length > 0 && !hasAllPermissions) {
    console.warn(`[ProtectedRoute] 權限不足: 需要 ${permissions.join(', ')}`);
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 通過所有檢查
  return <>{children}</>;
};

/**
 * 管理員路由元件 (便捷封裝)
 */
export const AdminRoute: React.FC<Omit<ProtectedRouteProps, 'roles'>> = ({
  children,
  ...props
}) => {
  return (
    <ProtectedRoute {...props} roles={['admin']}>
      {children}
    </ProtectedRoute>
  );
};

/**
 * 公開路由元件 (便捷封裝)
 */
export const PublicRoute: React.FC<Omit<ProtectedRouteProps, 'requireAuth' | 'enabled'>> = ({
  children,
  ...props
}) => {
  return (
    <ProtectedRoute {...props} requireAuth={false} enabled={false}>
      {children}
    </ProtectedRoute>
  );
};

export default ProtectedRoute;
