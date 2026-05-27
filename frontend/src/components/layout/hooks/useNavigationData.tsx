/**
 * useNavigationData Hook
 * 負責載入和管理導覽資料
 * 從 Layout.tsx 拆分出來以提高可維護性
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import authService, { UserInfo } from '../../../services/authService';
import { usePermissions } from '../../../hooks';
import { isAuthDisabled, isInternalIP, shouldUseDevMockUser } from '../../../config/env';
import { navigationService } from '../../../services/navigationService';
import { secureApiService } from '../../../services/secureApiService';
import { logger } from '../../../utils/logger';
import { convertToMenuItems, getStaticMenuItems, MenuItem } from './useMenuItems';
import type { NavigationItem } from './types';
export type { NavigationItem } from './types';

interface UseNavigationDataReturn {
  menuItems: MenuItem[];
  navigationLoading: boolean;
  permissionsLoading: boolean;
  currentUser: UserInfo | null;
  isAdmin: () => boolean;
  hasPermission: (permission: string) => boolean;
}

const NAVIGATION_QUERY_KEY = ['navigation', 'items'] as const;

export const useNavigationData = (): UseNavigationDataReturn => {
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const queryClient = useQueryClient();

  const {
    userPermissions,
    loading: permissionsLoading,
    filterNavigationByRole,
    hasPermission,
    isAdmin,
    reloadPermissions
  } = usePermissions();

  // 載入用戶資訊
  const loadUserInfo = useCallback(async () => {
    const userInfo = authService.getUserInfo();
    // P-58：先看真實 user_info；只有沒登入時 dev mock 才介入
    const useDevMock = shouldUseDevMockUser();

    if (userInfo) {
      setCurrentUser(userInfo);
      logger.debug('Uses localStorage user info:', userInfo.full_name || userInfo.username);
      return;
    }

    if (useDevMock) {
      setCurrentUser({
        id: 0,
        username: 'developer',
        full_name: '開發者',
        email: 'dev@ck-missive.local',
        role: 'superuser',
        is_admin: true,
        is_active: true,
        permissions: '[]',
        created_at: new Date().toISOString(),
        login_count: 0,
        email_verified: true
      });
      logger.debug('Using default developer info (AUTH_DISABLED=true)');
      return;
    }

    // L49 (2026-05-27): self-heal — localStorage.user_info 缺失但 JWT 有效時，
    // 從 /auth/me 重新拉用戶資料補進 localStorage，避免顯示「訪客」假象。
    // 觸發場景：PM2 廢除後切 docker container，舊瀏覽器仍持 JWT cookie/bearer
    // 但 localStorage 在某個流程被清空（logout 流 / 跨 subdomain 切換 / 清快取）。
    const hasJwt = !!localStorage.getItem('access_token') || !!localStorage.getItem('refresh_token');
    if (hasJwt) {
      try {
        logger.debug('user_info missing but JWT present → rehydrate via /auth/me');
        const fetched = await authService.getCurrentUser();
        if (fetched) {
          localStorage.setItem('user_info', JSON.stringify(fetched));
          setCurrentUser(fetched);
          return;
        }
      } catch (err) {
        // /auth/me 失敗（JWT 過期或網路問題）→ 真的視為未登入
        logger.warn('/auth/me rehydrate failed, fall through to guest', err);
      }
    }

    setCurrentUser(null);
  }, []);

  // 舊版權限過濾 (保留相容性)
  const filterMenuItemsByPermissionLegacy = useCallback((items: MenuItem[]): MenuItem[] => {
    return items.filter(item => {
      if (item.permission_required && !hasPermission(item.permission_required)) {
        return false;
      }
      if (item.key === 'admin' || item.key === 'admin-menu') {
        return isAdmin();
      }
      if (item.children) {
        item.children = filterMenuItemsByPermissionLegacy(item.children);
        return item.children.length > 0;
      }
      return true;
    });
  }, [hasPermission, isAdmin]);

  // 使用 React Query 載入導覽資料
  const {
    data: navigationItems,
    isLoading: navigationQueryLoading,
    isError: navigationError,
  } = useQuery({
    queryKey: [...NAVIGATION_QUERY_KEY, userPermissions?.role],
    queryFn: async () => {
      logger.debug('Environment variables:', {
        VITE_AUTH_DISABLED: import.meta.env.VITE_AUTH_DISABLED,
        isInternalIP: isInternalIP(),
        authDisabled: isAuthDisabled()
      });

      // 清除舊版快取
      navigationService.clearNavigationCache();
      localStorage.removeItem('cache_navigation_items');
      sessionStorage.removeItem('cache_navigation_items');

      const result = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
      const items = result.items || [];
      logger.debug('Raw navigation items received:', items.length, 'items');
      return items;
    },
    // F21 (5/04 修復)：只在已登入時 fetch，避免 /entry 登入頁觸發 401 死循環。
    // user_info 由 setAuthData() 寫入 localStorage（真登入後才有）。
    // AUTH_DISABLED=true 內網時也允許 fetch（後端會回 mock）。
    enabled: !permissionsLoading && (
      isAuthDisabled() || !!localStorage.getItem('user_info')
    ),
    staleTime: 5 * 60 * 1000, // 5 分鐘內不重新請求
    gcTime: 10 * 60 * 1000,   // 10 分鐘後回收
  });

  // 從 query 結果計算 menuItems (取代 setState)
  const menuItems = useMemo(() => {
    if (navigationError) {
      const staticItems = getStaticMenuItems();
      // P-58：dev mock 才顯示全部；真用戶（即使在 dev 內網）走 perm filter
      const useDevMock = shouldUseDevMockUser();
      return useDevMock
        ? staticItems
        : filterMenuItemsByPermissionLegacy(staticItems);
    }

    if (!navigationItems) {
      return [];
    }

    const useDevMock = shouldUseDevMockUser();
    let filteredItems: NavigationItem[];

    if (useDevMock) {
      logger.debug('Development mock mode: Showing all navigation items (no real user_info)');
      filteredItems = navigationItems;
    } else {
      filteredItems = userPermissions
        ? filterNavigationByRole(navigationItems)
        : [];

      if (filteredItems.length === 0 && navigationItems.length > 0) {
        // P-57：fallback 只看「真正空的權限陣列」；非陣列（如後端回 JSON 字串）視為「需要權限」不放行，
        // 避免後端 schema bug 導致全部 nav 對無權限用戶可見。
        filteredItems = navigationItems.filter(item => {
          const permRequired = item.permission_required;
          return !permRequired || (Array.isArray(permRequired) && permRequired.length === 0);
        });
      }
    }

    const convertedItems = convertToMenuItems(filteredItems);
    logger.debug('Dynamic menu items loaded:', convertedItems.length, 'items');
    return convertedItems;
  }, [navigationItems, navigationError, userPermissions, filterNavigationByRole, filterMenuItemsByPermissionLegacy]);

  const navigationLoading = navigationQueryLoading || permissionsLoading;

  // 初始載入用戶資訊
  useEffect(() => {
    loadUserInfo();
  }, [loadUserInfo]);

  // F25 (5/06 強化)：跨分頁 + 同分頁 fallback —
  // 若有任何路徑寫了 user_info（saveAuthData 後但 user-logged-in event 漏 dispatch），
  // 一旦 storage event 觸發或下次 visibility change，立即重讀 localStorage。
  // 防護「Header 訪客」反覆出現的 race condition（5/04 認證鏈漏修一環的延伸防線）。
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'user_info' && e.newValue) {
        logger.debug('storage event: user_info updated → reloadUserInfo');
        loadUserInfo();
      }
    };
    const handleVisibilityChange = () => {
      // 從背景切回前景時校正 — 若 localStorage 有 user_info 但 currentUser 仍 null
      if (document.visibilityState === 'visible' && !currentUser) {
        const stored = localStorage.getItem('user_info');
        if (stored) {
          logger.debug('visibility change: user_info exists but state null → reloadUserInfo');
          loadUserInfo();
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [loadUserInfo, currentUser]);

  // 監聽導覽更新事件 — 透過 invalidateQueries 觸發 React Query 重新請求
  useEffect(() => {
    const handleNavigationUpdate = () => {
      logger.debug('Navigation update event received');
      queryClient.invalidateQueries({ queryKey: NAVIGATION_QUERY_KEY });
    };
    window.addEventListener('navigation-updated', handleNavigationUpdate);
    return () => {
      window.removeEventListener('navigation-updated', handleNavigationUpdate);
    };
  }, [queryClient]);

  // 監聽登入事件
  useEffect(() => {
    const handleUserLogin = async () => {
      logger.debug('User login event received');
      loadUserInfo();
      await reloadPermissions();
      queryClient.invalidateQueries({ queryKey: NAVIGATION_QUERY_KEY });
    };
    window.addEventListener('user-logged-in', handleUserLogin);
    return () => {
      window.removeEventListener('user-logged-in', handleUserLogin);
    };
  }, [loadUserInfo, reloadPermissions, queryClient]);

  return {
    menuItems,
    navigationLoading,
    permissionsLoading,
    currentUser,
    isAdmin,
    hasPermission
  };
};

export default useNavigationData;
