/**
 * rolePermissionsApi 單元測試
 *
 * 涵蓋 ADR-0034 動態 role permissions 6 個 POST endpoint：
 * - list / get / update / getAvailable / syncUsers / getNavTree
 *
 * 執行方式：
 *   cd frontend && npx vitest run src/api/__tests__/rolePermissionsApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock('../endpoints/users', () => ({
  ADMIN_USER_MANAGEMENT_ENDPOINTS: {
    ROLE_PERMISSIONS_LIST: '/admin/role-permissions/list',
    ROLE_PERMISSIONS_GET: '/admin/role-permissions/get',
    ROLE_PERMISSIONS_UPDATE_DYNAMIC: '/admin/role-permissions/update',
    ROLE_PERMISSIONS_AVAILABLE: '/admin/role-permissions/available',
    ROLE_PERMISSIONS_SYNC_USERS: '/admin/role-permissions/sync-users',
    ROLE_PERMISSIONS_NAV_TREE: '/admin/role-permissions/nav-tree',
  },
}));

import { rolePermissionsApi } from '../rolePermissionsApi';
import { apiClient } from '../client';

const mockRole = {
  role: 'admin',
  permissions: ['documents:read', 'admin:users'],
  can_login: true,
  name_zh: '管理員',
  description_zh: '系統管理員',
  permission_count: 2,
  is_wildcard: false,
  updated_at: '2026-05-07T10:00:00Z',
  updated_by: 19,
};

describe('rolePermissionsApi.list', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /admin/role-permissions/list with empty body', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, items: [mockRole], total: 1 });

    const result = await rolePermissionsApi.list();

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/list', {});
    expect(result.total).toBe(1);
    expect(result.items[0]?.role).toBe('admin');
  });
});

describe('rolePermissionsApi.get', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /admin/role-permissions/get with role body', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, role: mockRole });

    const result = await rolePermissionsApi.get('admin');

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/get', { role: 'admin' });
    expect(result.role.permission_count).toBe(2);
  });
});

describe('rolePermissionsApi.update', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /admin/role-permissions/update with permissions array', async () => {
    const newPerms = ['documents:read', 'documents:edit'];
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      role: { ...mockRole, permissions: newPerms, permission_count: 2 },
      message: 'updated',
    });

    const result = await rolePermissionsApi.update('admin', newPerms, 'test note');

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/update', {
      role: 'admin',
      permissions: newPerms,
      note: 'test note',
    });
    expect(result.role.permissions).toEqual(newPerms);
  });

  it('預設 note 可省略', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ success: true, role: mockRole, message: 'ok' });

    await rolePermissionsApi.update('staff', []);

    const args = vi.mocked(apiClient.post).mock.calls[0]![1] as Record<string, unknown>;
    expect(args.role).toBe('staff');
    expect(args.permissions).toEqual([]);
    expect(args.note).toBeUndefined();
  });
});

describe('rolePermissionsApi.getAvailable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /admin/role-permissions/available 回傳 unassigned 紅點', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      all: ['admin:users', 'documents:read'],
      assigned: ['admin:users'],
      unassigned: ['documents:read'],
      from_navigation_items: ['admin:users'],
      from_business_endpoints: ['documents:read'],
      total_count: 2,
      unassigned_count: 1,
    });

    const result = await rolePermissionsApi.getAvailable();

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/available', {});
    expect(result.unassigned_count).toBe(1);
    expect(result.unassigned).toContain('documents:read');
  });
});

describe('rolePermissionsApi.syncUsers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POST /admin/role-permissions/sync-users 預設 onlyOutdated=true', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true, message: 'ok', role: 'admin',
      scanned: 5, updated: 2, skipped: 3,
      updated_users: [], skipped_users: [],
    });

    await rolePermissionsApi.syncUsers('admin');

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/sync-users', {
      role: 'admin',
      only_outdated: true,
    });
  });

  it('明確傳 onlyOutdated=false 強制更新所有 user', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true, message: 'ok', role: 'staff',
      scanned: 3, updated: 3, skipped: 0,
      updated_users: [], skipped_users: [],
    });

    await rolePermissionsApi.syncUsers('staff', false);

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/sync-users', {
      role: 'staff',
      only_outdated: false,
    });
  });
});

describe('rolePermissionsApi.getNavTree', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('不帶 role 時 body 為空', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true, tree: [], role: null, role_permissions: [],
      perm_to_nav: {}, is_wildcard: false,
    });

    await rolePermissionsApi.getNavTree();

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/nav-tree', {});
  });

  it('帶 role 時 body 含 role', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      success: true,
      tree: [],
      role: 'admin',
      role_permissions: ['documents:read'],
      perm_to_nav: { 'documents:read': [{ id: 1, key: 'docs', title: '公文' }] },
      is_wildcard: false,
    });

    const result = await rolePermissionsApi.getNavTree('admin');

    expect(apiClient.post).toHaveBeenCalledWith('/admin/role-permissions/nav-tree', { role: 'admin' });
    expect(result.role).toBe('admin');
    expect(result.role_permissions).toEqual(['documents:read']);
  });
});
