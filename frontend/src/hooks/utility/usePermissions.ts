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
import { shouldUseDevMockUser } from '../../config/env';
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
  const authDisabled = shouldUseDevMockUser();

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

  // P-29 (2026-05-06)：admin 不再等同 superuser
  //   - superuser / dev (id=0) → 所有 permission（最高層級）
  //   - admin → 用 API/cache 回傳的 user.permissions（受 /admin/permissions/admin 限制）
  //   - 其他 → 用 user.permissions
  if (userInfo.id === 0 || userInfo.role === 'superuser') {
    finalPermissions = USER_ROLES.superuser.default_permissions;
  } else {
    // admin 不再 fallback 到 superuser 全集；走自己 user.permissions
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
    const authDisabled = shouldUseDevMockUser();
    if (authDisabled) {
      return true;
    }

    if (!userPermissions) return false;

    // P-29：僅 superuser 短路；admin 走正常 permission filter
    if (userPermissions.role === 'superuser') {
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
    const authDisabled = shouldUseDevMockUser();
    if (authDisabled) {
      return true;
    }

    if (!userPermissions) return false;

    // P-29：僅 superuser 短路；admin 走正常 permission filter
    if (userPermissions.role === 'superuser') {
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
    const authDisabled = shouldUseDevMockUser();
    if (authDisabled) {
      return items.map(item => ({
        ...item,
        children: item.children ? filterNavigationItems(item.children) : undefined
      }));
    }

    if (!userPermissions) return [];

    return items
      .filter(item => {
        if (!item.is_enabled || !item.is_visible) return false;
        if (!item.permission_required || item.permission_required.length === 0) {
          return true;
        }
        return hasPermission(item.permission_required);
      })
      .map(item => ({
        ...item,
        children: item.children ? filterNavigationItems(item.children) : undefined,
      }))
      // P-38（路 A 細分授權）：父選單若 originally 有 children 但全被過濾掉（用戶
      // 對所有子權限都沒有），父選單自動隱藏避免「點不開的空目錄」。
      // 「報表分析」父 nav 用 reports:view 總開關；若 admin 給總開關但沒給任何子，
      // 結果會看到空的「報表分析」目錄 — 加此邏輯避免。
      .filter(item => {
        const originalHadChildren = !!(items.find(x => x.key === item.key)?.children?.length);
        if (originalHadChildren && (!item.children || item.children.length === 0)) {
          return false;
        }
        return true;
      });
  }, [userPermissions, hasPermission]);

  // 根據角色過濾導覽項目
  const filterNavigationByRole = useCallback((items: NavigationItem[]): NavigationItem[] => {
    // 開發模式 (AUTH_DISABLED=true) 時，顯示所有導覽項目
    const authDisabled = shouldUseDevMockUser();
    if (authDisabled) {
      return filterNavigationItems(items);
    }

    if (!userPermissions) return [];

    // P-26 (2026-05-06) admin/staff/user 全改為動態 'all'：
    //   過去 admin 用前端硬編碼 42-key 白名單，但 DB site_navigation_items 用不同
    //   命名（documents-menu vs documents / erp-menu vs ERP），交集只 24 keys。
    //   結果：李昭德 admin role 側邊欄只看 3 項（與 DB enabled 72 項嚴重脫鉤）。
    //
    //   修法：移除前端硬編碼白名單。所有 role 都看「DB enabled+visible 的 nav」，
    //   再由 filterNavigationItems 用 permission_required vs user.permissions 過濾。
    //   這樣 /admin/site-management 加新 nav item 後，admin/staff 立即動態看到
    //   （只要其 permission_required 對齊用戶的 permissions）。
    //
    //   superuser 仍 'all' 略過 permission filter；其他 role 經兩層過濾。
    const roleNavigationMap: Record<string, string[] | 'all'> = {
      'superuser': 'all', // 略過 permission filter
      'admin': 'all',     // 由 permission filter 對齊（不再硬編碼白名單）
      'user': 'all',      // 由 permission filter 對齊
      'staff': 'all',     // 由 permission filter 對齊
      'unverified': [
        'dashboard'
      ]
    };

    // 防呆：未定義角色 → 視同 user
    const allowedItems = roleNavigationMap[userPermissions.role] ?? 'all';

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

  // 檢查是否為管理員（admin 或 superuser）— 用於存取 /admin/* 等管理區
  // 注意：是否擁有特定 admin permission（如 admin:site_management）由 hasPermission 決定
  const isAdmin = useCallback((): boolean => {
    // 開發模式 (AUTH_DISABLED=true) 時，視為管理員
    const authDisabled = shouldUseDevMockUser();
    if (authDisabled) {
      return true;
    }
    return userPermissions?.is_admin || userPermissions?.role === 'admin' || userPermissions?.role === 'superuser' || false;
  }, [userPermissions]);

  // 檢查是否為超級管理員
  const isSuperuser = useCallback((): boolean => {
    // 開發模式 (AUTH_DISABLED=true) 時，視為超級管理員
    const authDisabled = shouldUseDevMockUser();
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