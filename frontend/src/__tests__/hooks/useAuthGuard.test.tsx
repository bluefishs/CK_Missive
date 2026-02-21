/**
 * useAuthGuard Hook 單元測試
 * useAuthGuard Hook Unit Tests
 *
 * 測試認證守衛與權限檢查功能
 *
 * 執行方式:
 *   cd frontend && npm run test -- useAuthGuard
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ============================================================================
// Mock 設定 (vi.mock 工廠內不可引用外部變數)
// ============================================================================

const mockNavigate = vi.fn();

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/documents', search: '', hash: '', state: null, key: 'default' }),
}));

// Mock authService - 使用 vi.fn() 在工廠內部定義
vi.mock('../../services/authService', () => {
  const service = {
    getUserInfo: vi.fn(),
    isAuthenticated: vi.fn(),
    isAdmin: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    validateTokenOnStartup: vi.fn().mockResolvedValue(true),
  };
  return {
    default: service,
    authService: service,
  };
});

// Mock env config - 使用模組級 getter 讓 beforeEach 可以控制
vi.mock('../../config/env', () => ({
  isAuthDisabled: vi.fn().mockReturnValue(false),
  isInternalNetwork: vi.fn().mockReturnValue(false),
}));

// Mock ROUTES
vi.mock('../../router/types', () => ({
  ROUTES: {
    HOME: '/',
    LOGIN: '/login',
    DOCUMENTS: '/documents',
    DASHBOARD: '/dashboard',
  },
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// 引入被測試的 hooks 與 mock 模組 (放在 vi.mock 之後)
import {
  useAuthGuard,
  usePermission,
  resetStartupValidation,
} from '../../hooks/utility/useAuthGuard';
import type { Permission } from '../../hooks/utility/useAuthGuard';
import authService from '../../services/authService';
import { isAuthDisabled, isInternalNetwork } from '../../config/env';

// ============================================================================
// useAuthGuard Hook 測試
// ============================================================================

describe('useAuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStartupValidation();

    // 預設：認證已停用=false, 非內網
    vi.mocked(isAuthDisabled).mockReturnValue(false);
    vi.mocked(isInternalNetwork).mockReturnValue(false);

    // 預設：已認證的一般使用者
    vi.mocked(authService.getUserInfo).mockReturnValue({
      id: 1,
      username: 'testuser',
      role: 'user',
      is_admin: false,
      permissions: ['documents:read', 'documents:write'],
      auth_provider: 'local',
    } as ReturnType<typeof authService.getUserInfo>);
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    vi.mocked(authService.isAdmin).mockReturnValue(false);
  });

  afterEach(() => {
    resetStartupValidation();
  });

  // --------------------------------------------------------------------------
  // 認證狀態偵測
  // --------------------------------------------------------------------------

  it('應該正確偵測已認證使用者', () => {
    const { result } = renderHook(() => useAuthGuard());

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.username).toBe('testuser');
    expect(result.current.userId).toBe(1);
    expect(result.current.role).toBe('user');
  });

  it('應該偵測未認證狀態', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue(null);
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    const { result } = renderHook(() => useAuthGuard());

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.username).toBeNull();
    expect(result.current.userId).toBeNull();
  });

  // --------------------------------------------------------------------------
  // AUTH_DISABLED 模式
  // --------------------------------------------------------------------------

  it('AUTH_DISABLED 模式下應該繞過所有認證', () => {
    vi.mocked(isAuthDisabled).mockReturnValue(true);
    vi.mocked(authService.getUserInfo).mockReturnValue(null);
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    const { result } = renderHook(() =>
      useAuthGuard({ requireAuth: true, roles: ['admin'] })
    );

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isAllowed).toBe(true);
    expect(result.current.authDisabled).toBe(true);
  });

  // --------------------------------------------------------------------------
  // 內網環境繞過
  // --------------------------------------------------------------------------

  it('內網環境且具有 internal auth_provider 時應該繞過認證', () => {
    vi.mocked(isInternalNetwork).mockReturnValue(true);
    vi.mocked(authService.getUserInfo).mockReturnValue({
      id: 1,
      username: 'internal-user',
      role: 'user',
      is_admin: false,
      auth_provider: 'internal',
    } as ReturnType<typeof authService.getUserInfo>);

    const { result } = renderHook(() =>
      useAuthGuard({ requireAuth: true })
    );

    expect(result.current.isAllowed).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
  });

  // --------------------------------------------------------------------------
  // requireAuth 與導向
  // --------------------------------------------------------------------------

  it('requireAuth=true 且未認證時應該不允許存取', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue(null);
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    const { result } = renderHook(() =>
      useAuthGuard({ requireAuth: true })
    );

    expect(result.current.isAllowed).toBe(false);
  });

  it('requireAuth=true 且未認證時應該導向登入頁', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue(null);
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    renderHook(() => useAuthGuard({ requireAuth: true }));

    expect(mockNavigate).toHaveBeenCalledWith(
      expect.stringContaining('/login'),
      expect.objectContaining({ replace: true })
    );
  });

  // --------------------------------------------------------------------------
  // 角色檢查
  // --------------------------------------------------------------------------

  it('具有 admin 角色時應該允許存取管理頁面', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue({
      id: 1,
      username: 'admin',
      role: 'admin',
      is_admin: true,
      permissions: [],
    } as unknown as ReturnType<typeof authService.getUserInfo>);
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    vi.mocked(authService.isAdmin).mockReturnValue(true);

    const { result } = renderHook(() =>
      useAuthGuard({ requireAuth: true, roles: ['admin'] })
    );

    expect(result.current.isAllowed).toBe(true);
    expect(result.current.isAdmin).toBe(true);
    expect(result.current.hasRole).toBe(true);
  });

  it('非 admin 角色時 roles=[admin] 應該不允許', () => {
    const { result } = renderHook(() =>
      useAuthGuard({ requireAuth: true, roles: ['admin'] })
    );

    expect(result.current.isAllowed).toBe(false);
    expect(result.current.hasRole).toBe(false);
  });

  it('superuser 角色應該擁有所有角色權限', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue({
      id: 1,
      username: 'superadmin',
      role: 'superuser',
      is_admin: true,
      permissions: [],
    } as unknown as ReturnType<typeof authService.getUserInfo>);
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    vi.mocked(authService.isAdmin).mockReturnValue(true);

    const { result } = renderHook(() =>
      useAuthGuard({ requireAuth: true, roles: ['admin', 'manager'] })
    );

    expect(result.current.isAllowed).toBe(true);
    expect(result.current.hasRole).toBe(true);
  });

  // --------------------------------------------------------------------------
  // 權限檢查
  // --------------------------------------------------------------------------

  it('應該正確檢查使用者具有的權限', () => {
    const { result } = renderHook(() =>
      useAuthGuard({
        requireAuth: true,
        permissions: ['documents:read' as Permission],
      })
    );

    expect(result.current.isAllowed).toBe(true);
    expect(result.current.hasAllPermissions).toBe(true);
  });

  it('應該拒絕使用者不具有的權限', () => {
    const { result } = renderHook(() =>
      useAuthGuard({
        requireAuth: true,
        permissions: ['admin:access' as Permission],
      })
    );

    expect(result.current.isAllowed).toBe(false);
    expect(result.current.hasAllPermissions).toBe(false);
  });

  it('admin 應該擁有所有權限', () => {
    vi.mocked(authService.getUserInfo).mockReturnValue({
      id: 1,
      username: 'admin',
      role: 'admin',
      is_admin: true,
      permissions: [],
    } as unknown as ReturnType<typeof authService.getUserInfo>);
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    vi.mocked(authService.isAdmin).mockReturnValue(true);

    const { result } = renderHook(() =>
      useAuthGuard({
        requireAuth: true,
        permissions: ['admin:access' as Permission, 'admin:users' as Permission],
      })
    );

    expect(result.current.hasAllPermissions).toBe(true);
  });

  // --------------------------------------------------------------------------
  // hasPermission 函數
  // --------------------------------------------------------------------------

  it('hasPermission 應該正確檢查單一權限', () => {
    const { result } = renderHook(() => useAuthGuard());

    expect(result.current.hasPermission('documents:read')).toBe(true);
    expect(result.current.hasPermission('admin:access')).toBe(false);
  });

  it('AUTH_DISABLED 模式下 hasPermission 應該始終返回 true', () => {
    vi.mocked(isAuthDisabled).mockReturnValue(true);

    const { result } = renderHook(() => useAuthGuard());

    expect(result.current.hasPermission('admin:access')).toBe(true);
  });

  // --------------------------------------------------------------------------
  // checkAuth 與 logout
  // --------------------------------------------------------------------------

  it('checkAuth 應該返回當前認證狀態', () => {
    const { result } = renderHook(() => useAuthGuard());

    expect(result.current.checkAuth()).toBe(true);
  });

  it('logout 應該呼叫 authService.logout 並導向登入頁', () => {
    const { result } = renderHook(() => useAuthGuard());

    result.current.logout();

    expect(authService.logout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
  });
});

// ============================================================================
// usePermission Hook 測試
// ============================================================================

describe('usePermission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStartupValidation();

    vi.mocked(isAuthDisabled).mockReturnValue(false);
    vi.mocked(isInternalNetwork).mockReturnValue(false);

    vi.mocked(authService.getUserInfo).mockReturnValue({
      id: 1,
      username: 'testuser',
      role: 'user',
      is_admin: false,
      permissions: ['documents:read'],
      auth_provider: 'local',
    } as ReturnType<typeof authService.getUserInfo>);
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    vi.mocked(authService.isAdmin).mockReturnValue(false);
  });

  afterEach(() => {
    resetStartupValidation();
  });

  it('使用者具有權限時應該返回 true', () => {
    const { result } = renderHook(() => usePermission('documents:read'));

    expect(result.current).toBe(true);
  });

  it('使用者不具有權限時應該返回 false', () => {
    const { result } = renderHook(() => usePermission('admin:access'));

    expect(result.current).toBe(false);
  });

  it('AUTH_DISABLED 模式下應該始終返回 true', () => {
    vi.mocked(isAuthDisabled).mockReturnValue(true);

    const { result } = renderHook(() => usePermission('admin:access'));

    expect(result.current).toBe(true);
  });
});
