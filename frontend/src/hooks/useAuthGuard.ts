/**
 * 認證守衛 Hook
 *
 * 提供統一的認證與權限檢查功能
 *
 * @version 1.0.0
 * @date 2026-01-06
 */

import { useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';
import { ROUTES } from '../router/types';

/** 權限類型 */
export type Permission =
  | 'documents:read'
  | 'documents:write'
  | 'documents:delete'
  | 'projects:read'
  | 'projects:write'
  | 'projects:delete'
  | 'admin:access'
  | 'admin:users'
  | 'admin:settings';

/** 認證狀態 */
export interface AuthState {
  isAuthenticated: boolean;
  isAdmin: boolean;
  userId: number | null;
  username: string | null;
  role: string | null;
  permissions: Permission[];
}

/** 認證守衛選項 */
export interface AuthGuardOptions {
  /** 是否需要認證 */
  requireAuth?: boolean;
  /** 需要的角色 */
  roles?: string[];
  /** 需要的權限 */
  permissions?: Permission[];
  /** 未認證時跳轉路徑 */
  redirectTo?: string;
  /** 是否顯示提示訊息 */
  showAlert?: boolean;
}

/**
 * 認證守衛 Hook
 *
 * @example
 * ```tsx
 * // 基本使用
 * const { isAuthenticated, checkAuth } = useAuthGuard();
 *
 * // 需要認證
 * const { isAllowed } = useAuthGuard({ requireAuth: true });
 *
 * // 需要管理員權限
 * const { isAllowed } = useAuthGuard({ roles: ['admin'] });
 *
 * // 需要特定權限
 * const { isAllowed, hasPermission } = useAuthGuard({
 *   permissions: ['documents:write']
 * });
 * ```
 */
export function useAuthGuard(options: AuthGuardOptions = {}) {
  const navigate = useNavigate();
  const location = useLocation();

  const {
    requireAuth = false,
    roles = [],
    permissions = [],
    redirectTo = ROUTES.LOGIN,
    showAlert = false,
  } = options;

  // 檢查是否禁用認證 (開發模式)
  const authDisabled = import.meta.env['VITE_AUTH_DISABLED'] === 'true';

  // 取得認證狀態
  const authState = useMemo<AuthState>(() => {
    if (authDisabled) {
      return {
        isAuthenticated: true,
        isAdmin: true,
        userId: 0,
        username: 'dev-user',
        role: 'admin',
        permissions: [] as Permission[],
      };
    }

    const userInfo = authService.getUserInfo();
    const isAuthenticated = authService.isAuthenticated();
    const isAdmin = authService.isAdmin();

    return {
      isAuthenticated,
      isAdmin,
      userId: userInfo?.id ?? null,
      username: userInfo?.username ?? null,
      role: userInfo?.role ?? null,
      permissions: (userInfo?.permissions as Permission[]) ?? [],
    };
  }, [authDisabled]);

  // 檢查角色
  const hasRole = useMemo(() => {
    if (authDisabled || roles.length === 0) return true;

    return roles.some((role) => {
      if (role === 'admin') return authState.isAdmin;
      return authState.role === role;
    });
  }, [authDisabled, roles, authState]);

  // 檢查權限
  const hasAllPermissions = useMemo(() => {
    if (authDisabled || permissions.length === 0) return true;

    // 管理員擁有所有權限
    if (authState.isAdmin) return true;

    return permissions.every((perm) => authState.permissions.includes(perm));
  }, [authDisabled, permissions, authState]);

  // 是否允許訪問
  const isAllowed = useMemo(() => {
    if (authDisabled) return true;

    if (requireAuth && !authState.isAuthenticated) return false;
    if (!hasRole) return false;
    if (!hasAllPermissions) return false;

    return true;
  }, [authDisabled, requireAuth, authState, hasRole, hasAllPermissions]);

  // 執行守衛邏輯
  useEffect(() => {
    if (authDisabled) return;

    if (!isAllowed) {
      if (showAlert) {
        console.warn('權限不足，正在跳轉...');
      }

      // 保存當前路徑以便登入後返回
      const returnUrl = encodeURIComponent(location.pathname + location.search);
      navigate(`${redirectTo}?returnUrl=${returnUrl}`, { replace: true });
    }
  }, [isAllowed, authDisabled, navigate, redirectTo, location, showAlert]);

  // 檢查單一權限
  const hasPermission = (permission: Permission): boolean => {
    if (authDisabled) return true;
    if (authState.isAdmin) return true;
    return authState.permissions.includes(permission);
  };

  // 手動檢查認證
  const checkAuth = (): boolean => {
    if (authDisabled) return true;
    return authService.isAuthenticated();
  };

  // 登出
  const logout = () => {
    authService.logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  return {
    ...authState,
    isAllowed,
    hasRole,
    hasAllPermissions,
    hasPermission,
    checkAuth,
    logout,
    authDisabled,
  };
}

/**
 * 權限檢查 Hook (簡化版)
 *
 * @example
 * ```tsx
 * const canEdit = usePermission('documents:write');
 * const canDelete = usePermission('documents:delete');
 * ```
 */
export function usePermission(permission: Permission): boolean {
  const { hasPermission, authDisabled, isAdmin } = useAuthGuard();

  if (authDisabled || isAdmin) return true;
  return hasPermission(permission);
}

/**
 * 多權限檢查 Hook
 *
 * @example
 * ```tsx
 * const permissions = usePermissions(['documents:write', 'documents:delete']);
 * // permissions = { 'documents:write': true, 'documents:delete': false }
 * ```
 */
export function usePermissions(
  permissionList: Permission[]
): Record<Permission, boolean> {
  const { hasPermission, authDisabled, isAdmin } = useAuthGuard();

  return permissionList.reduce(
    (acc, perm) => {
      acc[perm] = authDisabled || isAdmin || hasPermission(perm);
      return acc;
    },
    {} as Record<Permission, boolean>
  );
}

export default useAuthGuard;
