/**
 * usePermissions Hook 單元測試
 *
 * 測試權限檢查 Hook 的核心邏輯：
 * - hasPermission / hasAnyPermission
 * - isAdmin / isSuperuser
 * - filterNavigationItems
 *
 * 執行方式:
 *   cd frontend && npm run test -- usePermissions
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '../../test/testUtils';

// ==========================================================================
// Mocks
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

let mockIsAuthDisabled = false;
vi.mock('../../config/env', () => ({
  isAuthDisabled: () => mockIsAuthDisabled,
}));

const mockGetUserInfo = vi.fn();
const mockGetCurrentUser = vi.fn();

vi.mock('../../services/authService', () => ({
  authService: {
    getUserInfo: (...args: unknown[]) => mockGetUserInfo(...args),
    getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  },
}));

vi.mock('../../constants/permissions', () => ({
  USER_ROLES: {
    superuser: {
      default_permissions: [
        'documents:read', 'documents:create', 'documents:edit', 'documents:delete',
        'projects:read', 'admin:users', 'admin:settings',
      ],
    },
  },
}));

// Import after mocks
import { usePermissions } from '../../hooks/utility/usePermissions';
import type { NavigationItem } from '../../hooks/utility/usePermissions';

// ==========================================================================
// Tests
// ==========================================================================

describe('usePermissions - auth disabled mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthDisabled = true;
  });

  it('grants all permissions when auth is disabled', async () => {
    const { result } = renderHook(() => usePermissions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.hasPermission('documents:read')).toBe(true);
    expect(result.current.hasPermission('admin:settings')).toBe(true);
    expect(result.current.hasPermission('nonexistent:permission')).toBe(true);
  });

  it('reports isAdmin and isSuperuser as true when auth is disabled', async () => {
    const { result } = renderHook(() => usePermissions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.isAdmin()).toBe(true);
    expect(result.current.isSuperuser()).toBe(true);
  });

  it('returns all navigation items when auth is disabled', async () => {
    const { result } = renderHook(() => usePermissions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const navItems: NavigationItem[] = [
      {
        key: 'dashboard',
        title: 'Dashboard',
        path: '/dashboard',
        permission_required: [],
        is_visible: true,
        is_enabled: true,
        sort_order: 1,
      },
      {
        key: 'admin',
        title: 'Admin',
        path: '/admin',
        permission_required: ['admin:settings'],
        is_visible: true,
        is_enabled: true,
        sort_order: 2,
      },
    ];

    const filtered = result.current.filterNavigationItems(navItems);
    expect(filtered).toHaveLength(2);
  });
});

describe('usePermissions - auth enabled mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthDisabled = false;
  });

  it('returns null permissions when user is not logged in', async () => {
    mockGetUserInfo.mockReturnValue(null);

    const { result } = renderHook(() => usePermissions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.userPermissions).toBeNull();
    expect(result.current.hasPermission('documents:read')).toBe(false);
    expect(result.current.isAdmin()).toBe(false);
  });

  it('grants all permissions for superuser role', async () => {
    mockGetUserInfo.mockReturnValue({
      id: 1,
      username: 'admin',
      role: 'superuser',
      is_admin: true,
      permissions: [],
    });
    mockGetCurrentUser.mockResolvedValue({
      permissions: [],
    });

    const { result } = renderHook(() => usePermissions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.userPermissions).not.toBeNull();
    expect(result.current.hasPermission('documents:read')).toBe(true);
    expect(result.current.isSuperuser()).toBe(true);
  });

  it('exposes clearPermissionsCache and reloadPermissions', async () => {
    mockGetUserInfo.mockReturnValue(null);

    const { result } = renderHook(() => usePermissions(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.clearPermissionsCache).toBe('function');
    expect(typeof result.current.reloadPermissions).toBe('function');
  });
});
