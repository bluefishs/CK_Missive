/**
 * 受保護路由元件
 *
 * 提供統一的路由保護功能，整合 useAuthGuard Hook
 *
 * @version 1.0.0
 * @date 2026-01-06
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthGuard, Permission } from '../hooks/useAuthGuard';
import { ROUTES } from './types';
import { PageLoading } from '../components/common';

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
  /** 顯示載入中訊息 */
  loadingMessage?: string;
  /** 是否啟用認證檢查 (用於條件式保護) */
  enabled?: boolean;
}

/**
 * 受保護路由元件
 *
 * 使用 useAuthGuard Hook 提供認證與權限控制
 *
 * @example
 * ```tsx
 * // 基本認證保護
 * <ProtectedRoute>
 *   <MyPage />
 * </ProtectedRoute>
 *
 * // 需要管理員權限
 * <ProtectedRoute roles={['admin']}>
 *   <AdminPage />
 * </ProtectedRoute>
 *
 * // 需要特定權限
 * <ProtectedRoute permissions={['documents:write']}>
 *   <DocumentEditPage />
 * </ProtectedRoute>
 *
 * // 條件式保護 (用於公開頁面)
 * <ProtectedRoute enabled={false}>
 *   <PublicPage />
 * </ProtectedRoute>
 * ```
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
  roles = [],
  permissions = [],
  redirectTo = ROUTES.LOGIN,
  loadingMessage,
  enabled = true,
}) => {
  const location = useLocation();
  const {
    isAuthenticated,
    isAllowed,
    authDisabled,
    hasRole,
    hasAllPermissions,
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

  // 開發模式下直接渲染
  if (authDisabled) {
    return <>{children}</>;
  }

  // 未認證，重定向到登入頁
  if (requireAuth && !isAuthenticated) {
    const returnUrl = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`${redirectTo}?returnUrl=${returnUrl}`} replace />;
  }

  // 角色不足，重定向
  if (roles.length > 0 && !hasRole) {
    console.warn(`[ProtectedRoute] 角色不足: 需要 ${roles.join(' 或 ')}`);
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 權限不足，重定向
  if (permissions.length > 0 && !hasAllPermissions) {
    console.warn(`[ProtectedRoute] 權限不足: 需要 ${permissions.join(', ')}`);
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 通過所有檢查
  return <>{children}</>;
};

/**
 * 管理員路由元件 (便捷封裝)
 *
 * @example
 * ```tsx
 * <AdminRoute>
 *   <AdminDashboard />
 * </AdminRoute>
 * ```
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
 *
 * 用於不需要認證的頁面
 *
 * @example
 * ```tsx
 * <PublicRoute>
 *   <LoginPage />
 * </PublicRoute>
 * ```
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
