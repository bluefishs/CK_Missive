/**
 * 認證高階元件 (HOC)
 *
 * 提供統一的認證與權限控制封裝
 *
 * @version 1.0.0
 * @date 2026-01-06
 */

import React, { ComponentType } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthGuard, Permission, AuthGuardOptions } from '../../hooks';
import { ROUTES } from '../../router/types';
import { PageLoading } from '../common';

/** HOC 選項 */
export interface WithAuthOptions extends AuthGuardOptions {
  /** 載入中顯示的訊息 */
  loadingMessage?: string;
  /** 自訂未授權元件 */
  UnauthorizedComponent?: ComponentType;
}

/**
 * 認證守衛 HOC
 *
 * @example
 * ```tsx
 * // 基本用法 - 需要登入
 * export default withAuth(MyPage);
 *
 * // 需要管理員角色
 * export default withAuth(AdminPage, { roles: ['admin'] });
 *
 * // 需要特定權限
 * export default withAuth(DocumentEditPage, {
 *   permissions: ['documents:write']
 * });
 * ```
 */
export function withAuth<P extends object>(
  WrappedComponent: ComponentType<P>,
  options: WithAuthOptions = {}
): ComponentType<P> {
  const {
    requireAuth = true,
    roles = [],
    permissions = [],
    redirectTo = ROUTES.LOGIN,
    loadingMessage = '檢查權限中...',
    UnauthorizedComponent,
  } = options;

  const WithAuthComponent: React.FC<P> = (props) => {
    const location = useLocation();
    const {
      isAuthenticated,
      isAllowed,
      authDisabled,
    } = useAuthGuard({
      requireAuth,
      roles,
      permissions,
      redirectTo,
    });

    // 開發模式下直接渲染
    if (authDisabled) {
      return <WrappedComponent {...props} />;
    }

    // 未認證，重定向到登入頁
    if (requireAuth && !isAuthenticated) {
      const returnUrl = encodeURIComponent(location.pathname + location.search);
      return <Navigate to={`${redirectTo}?returnUrl=${returnUrl}`} replace />;
    }

    // 權限不足
    if (!isAllowed) {
      if (UnauthorizedComponent) {
        return <UnauthorizedComponent />;
      }
      return <Navigate to={ROUTES.DASHBOARD} replace />;
    }

    return <WrappedComponent {...props} />;
  };

  // 設定顯示名稱
  WithAuthComponent.displayName = `withAuth(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return WithAuthComponent;
}

/**
 * 需要管理員權限的 HOC
 *
 * @example
 * ```tsx
 * export default withAdminAuth(AdminPage);
 * ```
 */
export function withAdminAuth<P extends object>(
  WrappedComponent: ComponentType<P>,
  additionalOptions: Omit<WithAuthOptions, 'roles'> = {}
): ComponentType<P> {
  return withAuth(WrappedComponent, {
    ...additionalOptions,
    roles: ['admin'],
  });
}

/**
 * 需要特定權限的 HOC
 *
 * @example
 * ```tsx
 * export default withPermission(['documents:write', 'documents:delete'])(DocumentEditPage);
 * ```
 */
export function withPermission(requiredPermissions: Permission[]) {
  return function <P extends object>(
    WrappedComponent: ComponentType<P>,
    additionalOptions: Omit<WithAuthOptions, 'permissions'> = {}
  ): ComponentType<P> {
    return withAuth(WrappedComponent, {
      ...additionalOptions,
      permissions: requiredPermissions,
    });
  };
}

export default withAuth;
