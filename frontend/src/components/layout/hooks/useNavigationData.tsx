/**
 * useNavigationData Hook
 * 負責載入和管理導覽資料
 * 從 Layout.tsx 拆分出來以提高可維護性
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import authService, { UserInfo } from '../../../services/authService';
import { usePermissions } from '../../../hooks';
import { isAuthDisabled, isInternalIP } from '../../../config/env';
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
  const loadUserInfo = useCallback(() => {
    const userInfo = authService.getUserInfo();
    const authDisabled = isAuthDisabled();

    if (userInfo) {
      setCurrentUser(userInfo);
      logger.debug('Uses localStorage user info:', userInfo.full_name || userInfo.username);
      return;
    }

    if (authDisabled) {
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
    enabled: !permissionsLoading,
    staleTime: 5 * 60 * 1000, // 5 分鐘內不重新請求
    gcTime: 10 * 60 * 1000,   // 10 分鐘後回收
  });

  // 從 query 結果計算 menuItems (取代 setState)
  const menuItems = useMemo(() => {
    if (navigationError) {
      const staticItems = getStaticMenuItems();
      const authDisabled = isAuthDisabled();
      return authDisabled
        ? staticItems
        : filterMenuItemsByPermissionLegacy(staticItems);
    }

    if (!navigationItems) {
      return [];
    }

    const authDisabled = isAuthDisabled();
    let filteredItems: NavigationItem[];

    if (authDisabled) {
      logger.debug('Development mode: Showing all navigation items');
      filteredItems = navigationItems;
    } else {
      filteredItems = userPermissions
        ? filterNavigationByRole(navigationItems)
        : [];

      if (filteredItems.length === 0 && navigationItems.length > 0) {
        filteredItems = navigationItems.filter(item => {
          const permRequired = item.permission_required;
          return !permRequired || !Array.isArray(permRequired) || permRequired.length === 0;
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
