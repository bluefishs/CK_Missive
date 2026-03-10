/**
 * 權限檢查 Hook
 * 提供動態權限檢查和導覽過濾功能
 *
 * @version 2.0.0
 * @date 2026-03-10
 */
import { useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { authService } from '../../services/authService';
import { USER_ROLES } from '../../constants/permissions';
import { isAuthDisabled } from '../../config/env';
import { logger } from '../../utils/logger';

export interface NavigationItem {
  key: string;
  title: string;
  path: string;
  icon?: string;
  permission_required: string[];
  is_visible: boolean;
  is_enabled: boolean;
  sort_order: number;
  children?: NavigationItem[];
}

export interface UserPermissions {
  permissions: string[];
  role: string;
  is_admin: boolean;
}

/**
 * 從 API 取得並計算使用者權限資料
 */
async function fetchUserPermissions(): Promise<UserPermissions | null> {
  const authDisabled = isAuthDisabled();

  // 僅在明確停用認證時使用預設管理員
  let userInfo = authService.getUserInfo();
  if (authDisabled) {
    // 創建預設的開發者帳號資訊，使用超級管理員角色
    userInfo = {
      id: 0,  // 開發用預設 ID
      username: 'developer',
      full_name: '開發者',
      email: 'dev@ck-missive.local',
      role: 'superuser',
      is_admin: true,
      is_active: true,
      permissions: [],
      auth_provider: 'local',
      created_at: new Date().toISOString(),
      login_count: 0,
      email_verified: true
    };
    logger.debug('Using default developer user info (AUTH_DISABLED=true)');
  }

  // 如果沒有使用者資訊且認證未停用，則返回 null（應該會被重導向到登入頁）
  if (!userInfo) {
    return null;
  }

  // 在開發模式下，跳過 API 調用直接使用預設權限
  let permissions: string[] = [];
  if (!authDisabled) {
    try {
      const currentUser = await authService.getCurrentUser();
      if (currentUser && typeof currentUser.permissions === 'string') {
        permissions = JSON.parse(currentUser.permissions);
      } else if (Array.isArray(currentUser?.permissions)) {
        permissions = currentUser.permissions;
      }
    } catch (apiError) {
      logger.warn('Failed to fetch permissions from API, using cached data:', apiError);
      // 如果 API 失敗，嘗試從本地資料取得
      if (userInfo.permissions) {
        try {
          permissions = typeof userInfo.permissions === 'string'
            ? JSON.parse(userInfo.permissions)
            : userInfo.permissions;
        } catch (parseError) {
          logger.warn('Failed to parse cached permissions:', parseError);
        }
      }
    }
  } else {
    logger.debug('Auth disabled - skipping API call for permissions');
  }

  // 使用既有角色權限配置
  let finalPermissions: string[] = [];

  if (userInfo.id === 0 || userInfo.role === 'superuser' || userInfo.is_admin) {
    // 開發者帳號或超級管理員給予所有權限
    finalPermissions = USER_ROLES.superuser.default_permissions;
  } else {
    // 使用 API 或快取的權限資料
    finalPermissions = permissions || [];
  }

  return {
    permissions: finalPermissions,
    role: userInfo.role || 'user',
    is_admin: userInfo.is_admin || false
  };
}

export const usePermissions = () => {
  const queryClient = useQueryClient();

  const {
    data: userPermissions = null,
    isLoading: loading,
    error: queryError,
  } = useQuery<UserPermissions | null>({
    queryKey: ['userPermissions'],
    queryFn: fetchUserPermissions,
    staleTime: 5 * 60 * 1000, // 5 分鐘內不重新請求
    gcTime: 10 * 60 * 1000,   // 10 分鐘快取保留
    retry: 1,
  });

  const error = useMemo(
    () => (queryError ? (queryError instanceof Error ? queryError.message : 'Failed to load permissions') : null),
    [queryError]
  );

  // 檢查是否擁有特定權限
  const hasPermission = useCallback((permission: string | string[]): boolean => {
    // 開發模式 (AUTH_DISABLED=true) 時，所有功能開放
    const authDisabled = isAuthDisabled();
    if (authDisabled) {
      return true;
    }

    if (!userPermissions) return false;

    // 超級管理員和管理員擁有所有權限
    if (userPermissions.role === 'superuser' || userPermissions.is_admin) {
      return true;
    }

    const requiredPerms = Array.isArray(permission) ? permission : [permission];

    // 檢查是否擁有所有必要權限
    return requiredPerms.every(perm =>
      userPermissions.permissions.includes(perm)
    );
  }, [userPermissions]);

  // 檢查是否擁有任一權限
  const hasAnyPermission = useCallback((permissions: string[]): boolean => {
    // 開發模式 (AUTH_DISABLED=true) 時，所有功能開放
    const authDisabled = isAuthDisabled();
    if (authDisabled) {
      return true;
    }

    if (!userPermissions) return false;

    // 超級管理員和管理員擁有所有權限
    if (userPermissions.role === 'superuser' || userPermissions.is_admin) {
      return true;
    }

    // 檢查是否擁有任一權限
    return permissions.some(perm =>
      userPermissions.permissions.includes(perm)
    );
  }, [userPermissions]);

  // 過濾可見的導覽項目
  const filterNavigationItems = useCallback((items: NavigationItem[]): NavigationItem[] => {
    // 開發模式 (AUTH_DISABLED=true) 時，顯示所有導覽項目
    const authDisabled = isAuthDisabled();
    if (authDisabled) {
      return items.map(item => ({
        ...item,
        children: item.children ? filterNavigationItems(item.children) : undefined
      }));
    }

    if (!userPermissions) return [];

    return items.filter(item => {
      // 檢查項目是否啟用和可見
      if (!item.is_enabled || !item.is_visible) return false;

      // 如果沒有權限要求，所有人都可以看到
      if (!item.permission_required || item.permission_required.length === 0) {
        return true;
      }

      // 檢查權限
      return hasPermission(item.permission_required);
    }).map(item => ({
      ...item,
      children: item.children ? filterNavigationItems(item.children) : undefined
    }));
  }, [userPermissions, hasPermission]);

  // 根據角色過濾導覽項目
  const filterNavigationByRole = useCallback((items: NavigationItem[]): NavigationItem[] => {
    // 開發模式 (AUTH_DISABLED=true) 時，顯示所有導覽項目
    const authDisabled = isAuthDisabled();
    if (authDisabled) {
      return filterNavigationItems(items);
    }

    if (!userPermissions) return [];

    const roleNavigationMap: Record<string, string[] | 'all'> = {
      'superuser': 'all', // 顯示所有項目
      'admin': [
        'dashboard', 'documents-menu', 'document-list', 'document-create',
        'projects-menu', 'projects', 'contract-cases', 'agencies', 'vendors',
        'calendar-menu', 'calendar', 'reports',
        'system-docs-menu', 'api-docs', 'api-mapping', 'unified-form-demo',
        'system-admin-menu', 'admin-dashboard', 'user-management',
        'permission-management', 'site-management', 'database-management'
      ],
      'user': [
        'dashboard', 'documents-menu', 'document-list',
        'projects-menu', 'projects', 'agencies', 'vendors',
        'calendar-menu', 'calendar', 'reports'
      ],
      'unverified': [
        'dashboard'
      ]
    };

    const allowedItems = roleNavigationMap[userPermissions.role];

    if (allowedItems === 'all') {
      return filterNavigationItems(items);
    }

    if (!Array.isArray(allowedItems)) {
      return [];
    }

    // 先按角色過濾，再按權限過濾
    const roleFiltered = items.filter(item => allowedItems.includes(item.key));
    return filterNavigationItems(roleFiltered);
  }, [userPermissions, filterNavigationItems]);

  // 檢查是否為管理員
  const isAdmin = useCallback((): boolean => {
    // 開發模式 (AUTH_DISABLED=true) 時，視為管理員
    const authDisabled = isAuthDisabled();
    if (authDisabled) {
      return true;
    }
    return userPermissions?.is_admin || userPermissions?.role === 'admin' || userPermissions?.role === 'superuser' || false;
  }, [userPermissions]);

  // 檢查是否為超級管理員
  const isSuperuser = useCallback((): boolean => {
    // 開發模式 (AUTH_DISABLED=true) 時，視為超級管理員
    const authDisabled = isAuthDisabled();
    if (authDisabled) {
      return true;
    }
    return userPermissions?.role === 'superuser' || false;
  }, [userPermissions]);

  // 清除權限快取 (invalidate React Query cache)
  const clearPermissionsCache = useCallback(() => {
    queryClient.removeQueries({ queryKey: ['userPermissions'] });
  }, [queryClient]);

  // 重新載入權限並清除快取
  const reloadPermissions = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['userPermissions'] });
  }, [queryClient]);

  return {
    userPermissions,
    loading,
    error,
    hasPermission,
    hasAnyPermission,
    filterNavigationItems,
    filterNavigationByRole,
    isAdmin,
    isSuperuser,
    reloadPermissions,
    clearPermissionsCache
  };
};