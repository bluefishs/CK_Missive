/**
 * 認證守衛 Hook
 *
 * 提供統一的認證與權限檢查功能
 *
 * @version 1.3.0
 * @date 2026-01-15
 * @changelog
 * - v1.3.0: 新增 superuser 角色擁有所有角色權限的邏輯
 */

import { useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../../services/authService';
import { ROUTES } from '../../router/types';
import { isAuthDisabled, isInternalNetwork } from '../../config/env';
import { logger } from '../../utils/logger';

/** 權限類型 */
export type Permission =
  | 'documents:read'
  | 'documents:write'
  | 'documents:create'
  | 'documents:edit'
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
 * 檢查是否應該繞過認證檢查
 * 條件：
 * 1. VITE_AUTH_DISABLED=true（完全停用認證）
 * 2. 內網環境 + 已有 internal auth_provider 的 user_info
 */
const shouldBypassAuth = (): boolean => {
  // 環境變數完全停用認證
  if (isAuthDisabled()) {
    logger.debug('[AuthGuard] Bypass: AUTH_DISABLED=true');
    return true;
  }

  // 內網環境 + 已通過快速進入
  const isInternal = isInternalNetwork();
  const userInfo = authService.getUserInfo();

  logger.debug('[AuthGuard] Check:', {
    isInternalNetwork: isInternal,
    hasUserInfo: !!userInfo,
    authProvider: userInfo?.auth_provider
  });

  if (isInternal && userInfo && userInfo.auth_provider === 'internal') {
    logger.debug('[AuthGuard] Bypass: Internal network + internal auth');
    return true;
  }

  return false;
};

/**
 * 認證守衛 Hook
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

  // 檢查是否繞過認證
  const authBypassed = shouldBypassAuth();

  // 取得認證狀態
  const authState = useMemo<AuthState>(() => {
    if (authBypassed) {
      // 繞過模式：從 localStorage 取得 user_info 或使用預設管理員
      const userInfo = authService.getUserInfo();
      return {
        isAuthenticated: true,
        isAdmin: userInfo?.is_admin ?? true,
        userId: userInfo?.id ?? 0,
        username: userInfo?.username ?? 'dev-user',
        role: userInfo?.role ?? 'admin',
        permissions: [] as Permission[],
      };
    }

    // 正常模式：檢查實際認證狀態
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
  }, [authBypassed]);

  // 檢查角色
  const hasRole = useMemo(() => {
    if (authBypassed || roles.length === 0) return true;

    // superuser 擁有所有角色權限
    if (authState.role === 'superuser') return true;

    return roles.some((role) => {
      if (role === 'admin') return authState.isAdmin;
      return authState.role === role;
    });
  }, [authBypassed, roles, authState]);

  // 檢查權限
  const hasAllPermissions = useMemo(() => {
    if (authBypassed || permissions.length === 0) return true;

    // 管理員擁有所有權限
    if (authState.isAdmin) return true;

    return permissions.every((perm) => authState.permissions.includes(perm));
  }, [authBypassed, permissions, authState]);

  // 是否允許訪問
  const isAllowed = useMemo(() => {
    if (authBypassed) return true;

    if (requireAuth && !authState.isAuthenticated) return false;
    if (!hasRole) return false;
    if (!hasAllPermissions) return false;

    return true;
  }, [authBypassed, requireAuth, authState, hasRole, hasAllPermissions]);

  // 執行守衛邏輯
  useEffect(() => {
    if (authBypassed) return;

    if (!isAllowed) {
      if (showAlert) {
        console.warn('權限不足，正在跳轉...');
      }

      // 保存當前路徑以便登入後返回
      const returnUrl = encodeURIComponent(location.pathname + location.search);
      navigate(`${redirectTo}?returnUrl=${returnUrl}`, { replace: true });
    }
  }, [isAllowed, authBypassed, navigate, redirectTo, location, showAlert]);

  // 檢查單一權限
  const hasPermission = (permission: Permission): boolean => {
    if (authBypassed) return true;
    if (authState.isAdmin) return true;
    return authState.permissions.includes(permission);
  };

  // 手動檢查認證
  const checkAuth = (): boolean => {
    if (authBypassed) return true;
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
    authDisabled: authBypassed,  // 向後相容
  };
}

/**
 * 權限檢查 Hook (簡化版)
 */
export function usePermission(permission: Permission): boolean {
  const { hasPermission, authDisabled, isAdmin } = useAuthGuard();

  if (authDisabled || isAdmin) return true;
  return hasPermission(permission);
}

/**
 * 多權限檢查 Hook
 * @deprecated 使用 usePermissions().hasPermission() 代替
 */
export function useMultiplePermissions(
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
