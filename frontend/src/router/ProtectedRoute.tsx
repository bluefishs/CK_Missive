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
import { logger } from '../services/logger';
import { resolveRequiredPermission, useNavPermissionMap } from './useNavPermissionGate';
import { usePermissions } from '../hooks/utility/usePermissions';

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
  /**
   * 跳過「照選單宣告擋」那一層。
   *
   * 只給**本來就該所有登入者都進得去**的路由用（個人儀表板、個人設定、
   * 403 頁本身）。加這個旗標時請在該路由旁寫下理由 ——
   * 沒有理由的豁免，一年後沒有人敢拿掉。
   */
  skipNavPermission?: boolean;
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
  skipNavPermission = false,
}) => {
  const location = useLocation();
  // 2026-09-07 owner：「erp 圖譜前端無須檢視，但目前架構**知道網址就可檢視**」。
  // AppRouter 用了 117 次 ProtectedRoute、傳 permissions 的 0 次 ⇒ 路由層此前
  // 只問「有沒有登入」。**藏起選單不是擋住。**
  // 擋的依據直接讀選單自己的宣告，不另立第二份（見 useNavPermissionGate）。
  const { map: navPermMap, isLoading: navPermLoading } = useNavPermissionMap();
  // ⚠️ 這裡刻意用**選單自己那一支** `usePermissions().hasPermission`，
  //    不用 `useAuthGuard` 的同名函式 —— 兩支的判準不同
  //    （前者只有 superuser 短路，後者 isAdmin 也短路）。
  //    用不同的判準會長出「選單看得到、點進去被踢出來」，那比不擋更糟。
  const { hasPermission: hasNavPermission, loading: permissionsLoading } = usePermissions();
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
    logger.warn(`[ProtectedRoute] 角色不足: 需要 ${roles.join(' 或 ')}`);
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 權限不足，重定向到儀表板
  if (permissions.length > 0 && !hasAllPermissions) {
    logger.warn(`[ProtectedRoute] 權限不足: 需要 ${permissions.join(', ')}`);
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // 照選單宣告擋（逐條路由標權限會與選單分成兩份各自演化，這裡只有一份）
  // ⚠️ 儀表板本身永遠不擋：擋下時是導向儀表板，若儀表板自己也被擋就會**無限重導**。
  //    （實測 `/dashboard` 的宣告是空的，但這件事不該靠資料剛好正確。）
  // 權限或選單宣告還沒載入完就**不擋** —— 載入中的空權限清單與「真的沒有權限」
  // 在資料上長得一樣，而把正在載入誤判成沒有權限會把合法使用者踢回儀表板。
  if (!skipNavPermission && permissions.length === 0
      && !navPermLoading && !permissionsLoading
      && location.pathname !== ROUTES.DASHBOARD) {
    const required = resolveRequiredPermission(location.pathname, navPermMap);
    if (required && !hasNavPermission(required)) {
      logger.warn(`[ProtectedRoute] 選單宣告需要 ${required}，目前身分沒有 —— 擋下 ${location.pathname}`);
      return <Navigate to={ROUTES.DASHBOARD} replace />;
    }
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
