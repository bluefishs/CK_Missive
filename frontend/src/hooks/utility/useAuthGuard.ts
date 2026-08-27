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
import { useSessionStore } from '../../store/sessionStore';

/**
 * 重置啟動驗證旗標（登出時呼叫）。
 *
 * 2026-06-15 SSO 治本後，啟動驗證已集中到 sessionStore.bootstrap（單一權威解析），
 * 不再由各 useAuthGuard 實例各自跑 → 本函式保留為相容 API（authService.clearAuth /
 * 既有測試引用），現為 no-op。
 */
export function resetStartupValidation() {
  /* no-op：啟動驗證已移至 sessionStore.bootstrap */
}

/**
 * 權限類型。
 *
 * ⚠️ 2026-08-27 校正 —— 這是**第四份**權限來源，而它兩個方向都錯：
 *
 *   列了不存在的： documents:write / projects:write / admin:access
 *   漏了存在的：   projects:create / agencies:* / vendors:* / calendar:* /
 *                  reports:* / system_docs:* / admin:database / admin:site_management …
 *
 * **它正是讓 `projects:write` 看起來合法的原因** —— tsc 接受它，
 * 於是 `ContractCasePage` 的「新增案件」按鈕用一個沒有任何角色擁有的權限守著，
 * 而 admin 打 API 明明建得了案件（後端要的是 `projects:create`）。
 *
 * 本清單現在取自實際的三個來源聯集：
 *   `role_permissions` 已分派 ∪ `site_navigation_items.permission_required`
 *   ∪ 後端 `_BUSINESS_PERMISSIONS`
 *
 * ⚠️ 它仍然是手維護的（`PERMISSION_CATEGORIES` 沒有 `as const`，
 *   導不出字面聯集）。真正的守門是
 *   `scripts/checks/role_permissions_consistency_check.py` 第 5 項 ——
 *   它掃 `hasPermission('X')` 與端點的 `require_permission("X")`，
 *   比對「有沒有角色拿得到」，新出現的一律判紅。
 *   **這個型別擋的是筆誤，不是擋漂移；漂移由那支檢核擋。**
 */
export type Permission =
  | 'admin:database'
  | 'admin:settings'
  | 'admin:site_management'
  | 'admin:users'
  | 'agencies:create'
  | 'agencies:delete'
  | 'agencies:edit'
  | 'agencies:read'
  | 'calendar:edit'
  | 'calendar:read'
  | 'documents:create'
  | 'documents:delete'
  | 'documents:edit'
  | 'documents:read'
  | 'operational:approve'
  | 'operational:read'
  | 'operational:write'
  | 'projects:create'
  | 'projects:delete'
  | 'projects:edit'
  | 'projects:read'
  | 'reports:assets:view'
  | 'reports:erp:view'
  | 'reports:export'
  | 'reports:finance:view'
  | 'reports:stats:view'
  | 'reports:tender:view'
  | 'reports:view'
  | 'system_docs:create'
  | 'system_docs:delete'
  | 'system_docs:edit'
  | 'system_docs:read'
  | 'vendors:create'
  | 'vendors:delete'
  | 'vendors:edit'
  | 'vendors:read'
  // ── 以下三個**不存在於任何角色與 SSOT**，留在型別裡只是為了讓既有程式碼編得過 ──
  //
  // 2026-08-27：它們是「無人可得」的權限（見 permission_unreachable_baseline.json）。
  // 留著它們不是認可，是因為移除會讓四個頁面編不過，而那四個頁面的正解
  // 需要 owner 決定命名（owner 指示費用核銷相關「最後在處理」）。
  //
  //   'projects:write'  → ERPExpenseDetailPage / ERPExpenseListPage / ERPLedgerPage
  //                       （後端 erp/expenses.py 的 approve/reject/delete 也要它）
  //                       ⚠️ 語意上這不是「專案寫入」，正解多半是新開 expenses:approve
  //   'admin:access'    → ERPEInvoiceSyncPage（電子發票同步，會呼叫財政部 API 有配額）
  //                       ⚠️ 正解多半是 admin:settings，但那是**放寬**，屬產品決策
  //   'documents:write' → 目前無人使用，留著僅為相容
  //
  // **這三行本身就是待辦**。解掉之後要從這裡移除 ——
  // 留著一個永遠不會成立的型別成員，等於把問題藏進型別系統。
  | 'projects:write'
  | 'admin:access'
  | 'documents:write';

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
 *
 * 注意：Google/LINE/email 等外部 provider 不適用繞過，一律走完整 JWT 認證流程。
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

  // 2026-06-15 SSO 治本：is-authenticated 真相一律取自 sessionStore（單一權威解析），
  // 不再由本 hook 各實例自行呼叫 authService.isAuthenticated()（多來源 → race 根因）。
  const sessionStatus = useSessionStore((s) => s.status);

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

    // 正常模式：is-authenticated 取自 sessionStore（已解析的權威狀態）；
    // user 細節（role/permissions）仍由 authService.getUserInfo() 提供（與 store 同源 localStorage）。
    const userInfo = authService.getUserInfo();
    const isAuthenticated = sessionStatus === 'authenticated';
    const isAdmin = isAuthenticated && authService.isAdmin();

    return {
      isAuthenticated,
      isAdmin,
      userId: userInfo?.id ?? null,
      username: userInfo?.username ?? null,
      role: userInfo?.role ?? null,
      permissions: (userInfo?.permissions as Permission[]) ?? [],
    };
  }, [authBypassed, sessionStatus]);

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

  // 啟動驗證已集中至 sessionStore.bootstrap（SessionGate 在根部 resolve 完才渲染路由）。
  // 此處不再各實例重複呼叫 validateTokenOnStartup → 消滅「瞬態未認證 → 跳轉」race。

  // 執行守衛邏輯
  useEffect(() => {
    if (authBypassed) return;

    if (!isAllowed) {
      if (showAlert) {
        logger.warn('權限不足，正在跳轉...');
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
