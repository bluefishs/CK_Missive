/**
 * useNavigationData Hook
 * 負責載入和管理導覽資料
 * 從 Layout.tsx 拆分出來以提高可維護性
 */

import { useState, useEffect, useCallback } from 'react';
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

export const useNavigationData = (): UseNavigationDataReturn => {
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [navigationLoading, setNavigationLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);

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
      logger.debug('✅ 使用 localStorage 中的使用者資訊:', userInfo.full_name || userInfo.username);
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
      logger.debug('⚠️ 使用預設開發者資訊 (AUTH_DISABLED=true)');
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

  // 載入導覽資料
  const loadNavigationData = useCallback(async () => {
    try {
      setNavigationLoading(true);
      const authDisabled = isAuthDisabled();

      logger.debug('🔧 Environment variables:', {
        VITE_AUTH_DISABLED: import.meta.env.VITE_AUTH_DISABLED,
        isInternalIP: isInternalIP(),
        authDisabled
      });

      // 清除快取
      navigationService.clearNavigationCache();
      localStorage.removeItem('cache_navigation_items');
      sessionStorage.removeItem('cache_navigation_items');

      const result = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
      const navigationItems = result.items || [];
      logger.debug('📥 Raw navigation items received:', navigationItems.length, 'items');

      let filteredItems: NavigationItem[];

      if (authDisabled) {
        logger.debug('🛠️ Development mode: Showing all navigation items');
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
      logger.debug('🌲 Dynamic menu items loaded:', convertedItems.length, 'items');
      setMenuItems(convertedItems);

    } catch (error) {
      logger.error('Failed to load navigation:', error);
      const staticItems = getStaticMenuItems();
      const authDisabled = isAuthDisabled();
      const filteredStaticItems = authDisabled
        ? staticItems
        : filterMenuItemsByPermissionLegacy(staticItems);
      setMenuItems(filteredStaticItems);
    } finally {
      setNavigationLoading(false);
    }
  }, [userPermissions, filterNavigationByRole, filterMenuItemsByPermissionLegacy]);

  // 初始載入用戶資訊
  useEffect(() => {
    loadUserInfo();
  }, [loadUserInfo]);

  // 權限載入後載入導覽（含初始載入 — userPermissions 由 null 變為有值時觸發）
  useEffect(() => {
    if (!permissionsLoading) {
      loadNavigationData();
    }
  }, [userPermissions, permissionsLoading, loadNavigationData]);

  // 監聽導覽更新事件
  useEffect(() => {
    const handleNavigationUpdate = () => {
      logger.debug('🔄 Navigation update event received');
      loadNavigationData();
    };
    window.addEventListener('navigation-updated', handleNavigationUpdate);
    return () => {
      window.removeEventListener('navigation-updated', handleNavigationUpdate);
    };
  }, [loadNavigationData]);

  // 監聽登入事件
  useEffect(() => {
    const handleUserLogin = async () => {
      logger.debug('🔐 User login event received');
      loadUserInfo();
      await reloadPermissions();
      loadNavigationData();
    };
    window.addEventListener('user-logged-in', handleUserLogin);
    return () => {
      window.removeEventListener('user-logged-in', handleUserLogin);
    };
  }, [loadUserInfo, reloadPermissions, loadNavigationData]);

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
