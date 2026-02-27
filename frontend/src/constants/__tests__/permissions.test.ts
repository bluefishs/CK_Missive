/**
 * 權限管理常數測試
 * Permissions Constants Tests
 */
import { describe, it, expect } from 'vitest';
import {
  PERMISSION_CATEGORIES,
  getPermissionInfo,
  getPermissionDisplayName,
  getCategoryDisplayName,
  groupPermissionsByCategory,
  USER_ROLES,
  USER_STATUSES,
  getRoleDisplayName,
  getStatusDisplayName,
  canRoleLogin,
  canStatusLogin,
  getRoleDefaultPermissions,
  ALL_PERMISSIONS,
  ROLE_PERMISSIONS,
} from '../permissions';

describe('permissions 常數', () => {
  describe('PERMISSION_CATEGORIES', () => {
    const expectedCategories = [
      'documents', 'projects', 'agencies', 'vendors',
      'calendar', 'reports', 'system_docs', 'admin',
    ];

    it('應包含所有 8 個權限類別', () => {
      expect(Object.keys(PERMISSION_CATEGORIES)).toHaveLength(8);
      for (const key of expectedCategories) {
        expect(PERMISSION_CATEGORIES).toHaveProperty(key);
      }
    });

    it('每個類別應有必要欄位', () => {
      for (const [key, category] of Object.entries(PERMISSION_CATEGORIES)) {
        expect(category.key).toBe(key);
        expect(category.name_zh).toBeTruthy();
        expect(category.name_en).toBeTruthy();
        expect(category.permissions.length).toBeGreaterThan(0);
      }
    });

    it('每個權限應有完整的中英文定義', () => {
      for (const category of Object.values(PERMISSION_CATEGORIES)) {
        for (const perm of category.permissions) {
          expect(perm.key).toMatch(/^[a-z_]+:[a-z_]+$/);
          expect(perm.name_zh).toBeTruthy();
          expect(perm.name_en).toBeTruthy();
          expect(perm.category).toBe(category.key);
        }
      }
    });

    it('權限 key 應全域唯一', () => {
      const allKeys = Object.values(PERMISSION_CATEGORIES)
        .flatMap(c => c.permissions.map(p => p.key));
      expect(new Set(allKeys).size).toBe(allKeys.length);
    });
  });

  describe('getPermissionInfo', () => {
    it('應返回存在的權限資訊', () => {
      const info = getPermissionInfo('documents:read');
      expect(info).toBeDefined();
      expect(info!.name_zh).toBe('檢視公文');
      expect(info!.category).toBe('documents');
    });

    it('不存在的權限應返回 undefined', () => {
      expect(getPermissionInfo('nonexistent:permission')).toBeUndefined();
    });
  });

  describe('getPermissionDisplayName', () => {
    it('中文模式應返回中文名稱', () => {
      expect(getPermissionDisplayName('documents:create', 'zh')).toBe('建立公文');
    });

    it('英文模式應返回英文名稱', () => {
      expect(getPermissionDisplayName('documents:create', 'en')).toBe('Create Documents');
    });

    it('預設應為中文', () => {
      expect(getPermissionDisplayName('documents:create')).toBe('建立公文');
    });

    it('不存在的權限應返回原始 key', () => {
      expect(getPermissionDisplayName('unknown:perm')).toBe('unknown:perm');
    });
  });

  describe('getCategoryDisplayName', () => {
    it('應返回類別的中文名稱', () => {
      expect(getCategoryDisplayName('documents')).toBe('公文管理');
    });

    it('英文模式應返回英文名稱', () => {
      expect(getCategoryDisplayName('admin', 'en')).toBe('System Administration');
    });

    it('不存在的類別應返回原始 key', () => {
      expect(getCategoryDisplayName('nonexistent')).toBe('nonexistent');
    });
  });

  describe('groupPermissionsByCategory', () => {
    it('應按類別分組權限', () => {
      const result = groupPermissionsByCategory([
        'documents:read', 'documents:create', 'projects:read',
      ]);
      expect(Object.keys(result)).toHaveLength(2);
      expect(result['documents']).toHaveLength(2);
      expect(result['projects']).toHaveLength(1);
    });

    it('空陣列應返回空物件', () => {
      expect(groupPermissionsByCategory([])).toEqual({});
    });

    it('不存在的權限應被忽略', () => {
      const result = groupPermissionsByCategory(['unknown:perm', 'documents:read']);
      expect(Object.keys(result)).toHaveLength(1);
      expect(result['documents']).toHaveLength(1);
    });
  });

  describe('USER_ROLES', () => {
    it('應包含 4 個角色', () => {
      expect(Object.keys(USER_ROLES)).toEqual(['unverified', 'user', 'admin', 'superuser']);
    });

    it('unverified 不能登入且無權限', () => {
      expect(USER_ROLES.unverified.can_login).toBe(false);
      expect(USER_ROLES.unverified.default_permissions).toHaveLength(0);
    });

    it('user 可登入且有基本讀取權限', () => {
      expect(USER_ROLES.user.can_login).toBe(true);
      expect(USER_ROLES.user.default_permissions.length).toBeGreaterThan(0);
      expect(USER_ROLES.user.default_permissions.every(p => p.includes(':read'))).toBe(true);
    });

    it('admin 權限應多於 user', () => {
      expect(USER_ROLES.admin.default_permissions.length)
        .toBeGreaterThan(USER_ROLES.user.default_permissions.length);
    });

    it('superuser 應擁有所有權限', () => {
      expect(USER_ROLES.superuser.default_permissions.length).toBe(ALL_PERMISSIONS.length);
    });
  });

  describe('USER_STATUSES', () => {
    it('應包含 4 個狀態', () => {
      expect(Object.keys(USER_STATUSES)).toEqual(['active', 'inactive', 'pending', 'suspended']);
    });

    it('僅 active 可登入', () => {
      expect(USER_STATUSES.active.can_login).toBe(true);
      expect(USER_STATUSES.inactive.can_login).toBe(false);
      expect(USER_STATUSES.pending.can_login).toBe(false);
      expect(USER_STATUSES.suspended.can_login).toBe(false);
    });
  });

  describe('getRoleDisplayName', () => {
    it.each([
      ['admin', 'zh', '管理員'],
      ['admin', 'en', 'Administrator'],
      ['user', 'zh', '一般使用者'],
      ['superuser', 'en', 'Super Administrator'],
    ] as const)('角色 %s 語言 %s 應返回 %s', (role, lang, expected) => {
      expect(getRoleDisplayName(role, lang)).toBe(expected);
    });

    it('不存在的角色應返回原始 key', () => {
      expect(getRoleDisplayName('nonexistent')).toBe('nonexistent');
    });
  });

  describe('getStatusDisplayName', () => {
    it.each([
      ['active', 'zh', '啟用'],
      ['inactive', 'en', 'Inactive'],
      ['pending', 'zh', '待驗證'],
    ] as const)('狀態 %s 語言 %s 應返回 %s', (status, lang, expected) => {
      expect(getStatusDisplayName(status, lang)).toBe(expected);
    });
  });

  describe('canRoleLogin / canStatusLogin', () => {
    it('admin 可登入', () => {
      expect(canRoleLogin('admin')).toBe(true);
    });

    it('unverified 不可登入', () => {
      expect(canRoleLogin('unverified')).toBe(false);
    });

    it('不存在的角色不可登入', () => {
      expect(canRoleLogin('nonexistent')).toBe(false);
    });

    it('active 狀態可登入', () => {
      expect(canStatusLogin('active')).toBe(true);
    });

    it('suspended 狀態不可登入', () => {
      expect(canStatusLogin('suspended')).toBe(false);
    });

    it('不存在的狀態不可登入', () => {
      expect(canStatusLogin('nonexistent')).toBe(false);
    });
  });

  describe('getRoleDefaultPermissions', () => {
    it('admin 應有多個預設權限', () => {
      const perms = getRoleDefaultPermissions('admin');
      expect(perms.length).toBeGreaterThan(5);
      expect(perms).toContain('documents:read');
      expect(perms).toContain('admin:users');
    });

    it('不存在的角色應返回空陣列', () => {
      expect(getRoleDefaultPermissions('nonexistent')).toEqual([]);
    });
  });

  describe('ALL_PERMISSIONS / ROLE_PERMISSIONS', () => {
    it('ALL_PERMISSIONS 應大於 0', () => {
      expect(ALL_PERMISSIONS.length).toBeGreaterThan(0);
    });

    it('ALL_PERMISSIONS 應全域唯一', () => {
      expect(new Set(ALL_PERMISSIONS).size).toBe(ALL_PERMISSIONS.length);
    });

    it('ROLE_PERMISSIONS superuser 應等於 ALL_PERMISSIONS', () => {
      expect(ROLE_PERMISSIONS['superuser']).toEqual(ALL_PERMISSIONS);
    });

    it('ROLE_PERMISSIONS 每個角色的權限應為 ALL_PERMISSIONS 的子集', () => {
      const allSet = new Set(ALL_PERMISSIONS);
      for (const [, perms] of Object.entries(ROLE_PERMISSIONS)) {
        for (const p of perms) {
          expect(allSet.has(p)).toBe(true);
        }
      }
    });
  });
});
