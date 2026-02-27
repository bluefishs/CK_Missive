/**
 * usePermissions Hook 單元測試
 *
 * 安全關鍵 Hook：權限檢查、角色判斷、導覽過濾
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Hoisted mocks — 必須在 import 之前設定
// ---------------------------------------------------------------------------

const { mockIsAuthDisabled, mockGetUserInfo, mockGetCurrentUser, mockCacheGet, mockCacheSet, mockCacheDelete } =
  vi.hoisted(() => ({
    mockIsAuthDisabled: vi.fn((): boolean => false),
    mockGetUserInfo: vi.fn((): unknown => null),
    mockGetCurrentUser: vi.fn(async (): Promise<unknown> => null),
    mockCacheGet: vi.fn((): unknown => null),
    mockCacheSet: vi.fn(),
    mockCacheDelete: vi.fn(),
  }));

vi.mock('../../../config/env', () => ({
  isAuthDisabled: mockIsAuthDisabled,
}));

vi.mock('../../../services/authService', () => ({
  authService: {
    getUserInfo: mockGetUserInfo,
    getCurrentUser: mockGetCurrentUser,
  },
}));

vi.mock('../../../services/cacheService', () => ({
  cacheService: {
    get: mockCacheGet,
    set: mockCacheSet,
    delete: mockCacheDelete,
  },
  CACHE_KEYS: { USER_PERMISSIONS: 'user_permissions' },
  CACHE_TTL: { MEDIUM: 300000 },
}));

vi.mock('../../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('../../../constants/permissions', () => ({
  USER_ROLES: {
    superuser: {
      key: 'superuser',
      default_permissions: [
        'documents:read', 'documents:create', 'documents:edit', 'documents:delete',
        'projects:read', 'projects:create', 'projects:edit', 'projects:delete',
        'admin:users', 'admin:settings',
      ],
    },
    admin: {
      key: 'admin',
      default_permissions: [
        'documents:read', 'documents:create', 'documents:edit',
        'projects:read', 'projects:create',
        'admin:users',
      ],
    },
    user: {
      key: 'user',
      default_permissions: ['documents:read', 'projects:read'],
    },
    unverified: {
      key: 'unverified',
      default_permissions: [],
    },
  },
}));

import { usePermissions, type NavigationItem } from '../usePermissions';

// ---------------------------------------------------------------------------
// 測試輔助
// ---------------------------------------------------------------------------

/** 建立模擬 UserInfo */
function makeUserInfo(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    username: 'testuser',
    full_name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    is_admin: false,
    is_active: true,
    permissions: [],
    auth_provider: 'local',
    created_at: '2026-01-01T00:00:00Z',
    login_count: 1,
    email_verified: true,
    ...overrides,
  };
}

/** 建立模擬導覽項目 */
function makeNavItem(overrides: Partial<NavigationItem> = {}): NavigationItem {
  return {
    key: 'test-item',
    title: '測試項目',
    path: '/test',
    permission_required: [],
    is_visible: true,
    is_enabled: true,
    sort_order: 0,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// 測試開始
// ---------------------------------------------------------------------------

describe('usePermissions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthDisabled.mockReturnValue(false);
    mockGetUserInfo.mockReturnValue(null);
    mockGetCurrentUser.mockResolvedValue(null);
    mockCacheGet.mockReturnValue(null);
  });

  // =========================================================================
  // 1. 初始化與載入
  // =========================================================================

  describe('初始化與載入', () => {
    it('無使用者資訊時，userPermissions 應為 null', async () => {
      mockGetUserInfo.mockReturnValue(null);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.userPermissions).toBeNull();
      expect(result.current.error).toBeNull();
    });

    it('有使用者資訊時，應載入權限', async () => {
      const userInfo = makeUserInfo({ role: 'user', permissions: ['documents:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read', 'projects:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.userPermissions).not.toBeNull();
      expect(result.current.userPermissions?.role).toBe('user');
    });

    it('快取命中時，應使用快取的權限', async () => {
      const cached = { permissions: ['documents:read'], role: 'user', is_admin: false };
      mockGetUserInfo.mockReturnValue(makeUserInfo());
      mockCacheGet.mockReturnValue(cached);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.userPermissions).toEqual(cached);
      // 未呼叫 API
      expect(mockGetCurrentUser).not.toHaveBeenCalled();
    });

    it('API 失敗時，應回退至本地使用者權限', async () => {
      const userInfo = makeUserInfo({ permissions: ['documents:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // 應有權限資料（從本地回退）
      expect(result.current.userPermissions).not.toBeNull();
      expect(result.current.error).toBeNull();
    });

    it('API 回傳字串格式權限時，應正確解析', async () => {
      const userInfo = makeUserInfo();
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: '["documents:read","projects:read"]',
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.userPermissions).not.toBeNull();
    });

    it('載入出錯時，應設定 error 狀態', async () => {
      // 讓 getUserInfo 拋出例外
      mockGetUserInfo.mockImplementation(() => {
        throw new Error('Storage access denied');
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.error).toBe('Storage access denied');
    });
  });

  // =========================================================================
  // 2. AUTH_DISABLED 模式（開發模式）
  // =========================================================================

  describe('AUTH_DISABLED 模式', () => {
    beforeEach(() => {
      mockIsAuthDisabled.mockReturnValue(true);
    });

    it('應使用預設開發者帳號（superuser）', async () => {
      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.userPermissions).not.toBeNull();
      expect(result.current.userPermissions?.role).toBe('superuser');
      expect(result.current.userPermissions?.is_admin).toBe(true);
    });

    it('hasPermission 應始終回傳 true', async () => {
      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission('documents:delete')).toBe(true);
      expect(result.current.hasPermission('admin:settings')).toBe(true);
      expect(result.current.hasPermission('nonexistent:perm')).toBe(true);
    });

    it('hasAnyPermission 應始終回傳 true', async () => {
      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasAnyPermission(['nonexistent:perm'])).toBe(true);
    });

    it('isAdmin 應回傳 true', async () => {
      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isAdmin()).toBe(true);
    });

    it('isSuperuser 應回傳 true', async () => {
      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isSuperuser()).toBe(true);
    });

    it('filterNavigationItems 應回傳所有項目（不過濾）', async () => {
      const items: NavigationItem[] = [
        makeNavItem({ key: 'a', permission_required: ['admin:settings'], is_visible: true, is_enabled: true }),
        makeNavItem({ key: 'b', permission_required: ['nonexistent'], is_visible: true, is_enabled: true }),
      ];

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(2);
    });

    it('不應呼叫 API 取得權限', async () => {
      renderHook(() => usePermissions());

      await waitFor(() => {
        expect(mockGetCurrentUser).not.toHaveBeenCalled();
      });
    });
  });

  // =========================================================================
  // 3. hasPermission — 單一/多重權限檢查
  // =========================================================================

  describe('hasPermission', () => {
    it('userPermissions 為 null 時，應回傳 false', async () => {
      mockGetUserInfo.mockReturnValue(null);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission('documents:read')).toBe(false);
    });

    it('一般使用者有對應權限時，應回傳 true', async () => {
      const userInfo = makeUserInfo({ role: 'user', permissions: ['documents:read', 'projects:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read', 'projects:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission('documents:read')).toBe(true);
    });

    it('一般使用者無對應權限時，應回傳 false', async () => {
      const userInfo = makeUserInfo({ role: 'user', permissions: ['documents:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission('admin:settings')).toBe(false);
    });

    it('傳入陣列時，應檢查所有權限（AND 邏輯）', async () => {
      const userInfo = makeUserInfo({ role: 'user', permissions: ['documents:read', 'projects:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read', 'projects:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission(['documents:read', 'projects:read'])).toBe(true);
      expect(result.current.hasPermission(['documents:read', 'admin:settings'])).toBe(false);
    });

    it('superuser 角色應擁有所有權限', async () => {
      const userInfo = makeUserInfo({ id: 5, role: 'superuser', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission('admin:settings')).toBe(true);
      expect(result.current.hasPermission('nonexistent:perm')).toBe(true);
    });

    it('is_admin 為 true 時，應擁有所有權限', async () => {
      const userInfo = makeUserInfo({ id: 5, role: 'admin', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasPermission('anything')).toBe(true);
    });

    it('空字串權限應回傳 true（空陣列 every 為 true）', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // 空陣列 every() 回傳 true
      expect(result.current.hasPermission([])).toBe(true);
    });
  });

  // =========================================================================
  // 4. hasAnyPermission — OR 邏輯權限檢查
  // =========================================================================

  describe('hasAnyPermission', () => {
    it('userPermissions 為 null 時，應回傳 false', async () => {
      mockGetUserInfo.mockReturnValue(null);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasAnyPermission(['documents:read'])).toBe(false);
    });

    it('擁有任一權限時，應回傳 true', async () => {
      const userInfo = makeUserInfo({ role: 'user', permissions: ['documents:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasAnyPermission(['documents:read', 'admin:settings'])).toBe(true);
    });

    it('不擁有任何一個權限時，應回傳 false', async () => {
      const userInfo = makeUserInfo({ role: 'user', permissions: ['documents:read'] });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasAnyPermission(['admin:settings', 'admin:users'])).toBe(false);
    });

    it('superuser 角色應回傳 true', async () => {
      const userInfo = makeUserInfo({ id: 5, role: 'superuser', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasAnyPermission(['nonexistent:perm'])).toBe(true);
    });

    it('空陣列應回傳 false（some() 對空陣列回傳 false）', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: ['documents:read'],
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.hasAnyPermission([])).toBe(false);
    });
  });

  // =========================================================================
  // 5. 角色判斷 — isAdmin / isSuperuser
  // =========================================================================

  describe('isAdmin', () => {
    it('一般使用者應回傳 false', async () => {
      const userInfo = makeUserInfo({ role: 'user', is_admin: false });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isAdmin()).toBe(false);
    });

    it('admin 角色應回傳 true', async () => {
      const userInfo = makeUserInfo({ id: 2, role: 'admin', is_admin: false });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isAdmin()).toBe(true);
    });

    it('is_admin 旗標為 true 時應回傳 true', async () => {
      const userInfo = makeUserInfo({ id: 3, role: 'user', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isAdmin()).toBe(true);
    });

    it('superuser 角色應回傳 true', async () => {
      const userInfo = makeUserInfo({ id: 4, role: 'superuser', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isAdmin()).toBe(true);
    });
  });

  describe('isSuperuser', () => {
    it('一般使用者應回傳 false', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isSuperuser()).toBe(false);
    });

    it('admin 角色應回傳 false（admin != superuser）', async () => {
      const userInfo = makeUserInfo({ id: 2, role: 'admin', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isSuperuser()).toBe(false);
    });

    it('superuser 角色應回傳 true', async () => {
      const userInfo = makeUserInfo({ id: 5, role: 'superuser', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.isSuperuser()).toBe(true);
    });
  });

  // =========================================================================
  // 6. filterNavigationItems — 導覽過濾
  // =========================================================================

  describe('filterNavigationItems', () => {
    it('userPermissions 為 null 時，應回傳空陣列', async () => {
      mockGetUserInfo.mockReturnValue(null);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [makeNavItem({ key: 'a' })];
      expect(result.current.filterNavigationItems(items)).toEqual([]);
    });

    it('應過濾掉 is_enabled=false 的項目', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        makeNavItem({ key: 'a', is_enabled: false }),
        makeNavItem({ key: 'b', is_enabled: true }),
      ];

      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(1);
      expect(filtered[0]!.key).toBe('b');
    });

    it('應過濾掉 is_visible=false 的項目', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        makeNavItem({ key: 'a', is_visible: false }),
        makeNavItem({ key: 'b', is_visible: true }),
      ];

      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(1);
      expect(filtered[0]!.key).toBe('b');
    });

    it('無權限要求的項目，所有人都可見', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [makeNavItem({ key: 'public', permission_required: [] })];
      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(1);
    });

    it('有權限要求但使用者缺乏權限時，應過濾掉', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: ['documents:read'] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        makeNavItem({ key: 'admin', permission_required: ['admin:settings'] }),
      ];

      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(0);
    });

    it('子項目也應遞迴過濾', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: ['documents:read'] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items: NavigationItem[] = [
        makeNavItem({
          key: 'parent',
          permission_required: [],
          children: [
            makeNavItem({ key: 'child-visible', permission_required: [] }),
            makeNavItem({ key: 'child-hidden', permission_required: ['admin:settings'] }),
          ],
        }),
      ];

      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(1);
      expect(filtered[0]!.children).toHaveLength(1);
      expect(filtered[0]!.children![0]!.key).toBe('child-visible');
    });
  });

  // =========================================================================
  // 7. filterNavigationByRole — 角色導覽過濾
  // =========================================================================

  describe('filterNavigationByRole', () => {
    it('userPermissions 為 null 時，應回傳空陣列', async () => {
      mockGetUserInfo.mockReturnValue(null);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.filterNavigationByRole([makeNavItem()])).toEqual([]);
    });

    it('superuser 角色應看到所有項目', async () => {
      const userInfo = makeUserInfo({ id: 5, role: 'superuser', is_admin: true });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue(userInfo);

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        makeNavItem({ key: 'dashboard' }),
        makeNavItem({ key: 'admin-dashboard' }),
        makeNavItem({ key: 'custom-item' }),
      ];

      const filtered = result.current.filterNavigationByRole(items);
      expect(filtered).toHaveLength(3);
    });

    it('unverified 角色只能看到 dashboard', async () => {
      const userInfo = makeUserInfo({ id: 10, role: 'unverified', is_admin: false });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        makeNavItem({ key: 'dashboard' }),
        makeNavItem({ key: 'document-list' }),
        makeNavItem({ key: 'admin-dashboard' }),
      ];

      const filtered = result.current.filterNavigationByRole(items);
      expect(filtered).toHaveLength(1);
      expect(filtered[0]!.key).toBe('dashboard');
    });

    it('未知角色應回傳空陣列', async () => {
      const userInfo = makeUserInfo({ id: 11, role: 'unknown_role', is_admin: false });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [makeNavItem({ key: 'dashboard' })];
      const filtered = result.current.filterNavigationByRole(items);
      expect(filtered).toEqual([]);
    });

    it('user 角色應看到允許的導覽項目', async () => {
      const userInfo = makeUserInfo({ id: 6, role: 'user', is_admin: false });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: ['documents:read'] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        makeNavItem({ key: 'dashboard' }),
        makeNavItem({ key: 'document-list' }),
        makeNavItem({ key: 'user-management', permission_required: ['admin:users'] }),
      ];

      const filtered = result.current.filterNavigationByRole(items);
      // dashboard 和 document-list 在 user 角色允許清單中
      expect(filtered).toHaveLength(2);
      expect(filtered.map((i) => i.key)).toContain('dashboard');
      expect(filtered.map((i) => i.key)).toContain('document-list');
    });
  });

  // =========================================================================
  // 8. reloadPermissions / clearPermissionsCache
  // =========================================================================

  describe('reloadPermissions', () => {
    it('應清除快取並重新載入', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: ['documents:read'] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      await act(async () => {
        await result.current.reloadPermissions();
      });

      // cacheDelete 應被呼叫（清除快取）
      expect(mockCacheDelete).toHaveBeenCalled();
      // getCurrentUser 應被呼叫至少 2 次（初始 + 重新載入）
      expect(mockGetCurrentUser.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('clearPermissionsCache', () => {
    it('應刪除對應使用者的快取鍵', async () => {
      const userInfo = makeUserInfo({ id: 42 });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      act(() => {
        result.current.clearPermissionsCache();
      });

      expect(mockCacheDelete).toHaveBeenCalledWith('user_permissions_42', 'memory');
    });
  });

  // =========================================================================
  // 9. 開發者帳號（id=0）
  // =========================================================================

  describe('開發者帳號 (id=0)', () => {
    it('id=0 應獲得 superuser 權限', async () => {
      const userInfo = makeUserInfo({ id: 0, role: 'user', is_admin: false });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // id=0 分支給予 superuser 預設權限
      expect(result.current.userPermissions?.permissions).toEqual(
        expect.arrayContaining(['documents:read', 'admin:settings'])
      );
    });
  });

  // =========================================================================
  // 10. 邊界情況
  // =========================================================================

  describe('邊界情況', () => {
    it('permission_required 為 null/undefined 的項目應可見', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({ ...userInfo, permissions: [] });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      const items = [
        // 模擬後端回傳 null
        { ...makeNavItem({ key: 'no-perms' }), permission_required: null as unknown as string[] },
      ];

      const filtered = result.current.filterNavigationItems(items);
      expect(filtered).toHaveLength(1);
    });

    it('API 回傳 null 權限時不應崩潰', async () => {
      const userInfo = makeUserInfo({ role: 'user' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockResolvedValue({
        ...userInfo,
        permissions: null,
      });

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.userPermissions).not.toBeNull();
    });

    it('本地權限為無法解析的字串時不應崩潰', async () => {
      const userInfo = makeUserInfo({ permissions: 'invalid-json' });
      mockGetUserInfo.mockReturnValue(userInfo);
      mockGetCurrentUser.mockRejectedValue(new Error('API down'));

      const { result } = renderHook(() => usePermissions());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // 不應崩潰，error 為 null
      expect(result.current.error).toBeNull();
    });
  });
});
