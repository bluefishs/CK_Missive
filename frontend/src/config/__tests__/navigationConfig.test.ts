/**
 * 導覽列配置常數測試
 * Navigation Config Tests
 */
import { describe, it, expect } from 'vitest';
import {
  ICON_OPTIONS,
  ICON_OPTIONS_V2,
  MODULE_NAMES,
  ACTION_NAMES,
  PERMISSION_GROUPS,
  formatPermissionLabel,
} from '../navigationConfig';
import type { PermissionGroup } from '../navigationConfig';

// ============================================================================
// ICON_OPTIONS
// ============================================================================

describe('ICON_OPTIONS', () => {
  it('應為非空陣列', () => {
    expect(Array.isArray(ICON_OPTIONS)).toBe(true);
    expect(ICON_OPTIONS.length).toBeGreaterThan(0);
  });

  it('所有項目應為非空字串', () => {
    for (const icon of ICON_OPTIONS) {
      expect(typeof icon).toBe('string');
      expect(icon.length).toBeGreaterThan(0);
    }
  });

  it('應包含常用圖示', () => {
    expect(ICON_OPTIONS).toContain('dashboard');
    expect(ICON_OPTIONS).toContain('file-text');
    expect(ICON_OPTIONS).toContain('setting');
    expect(ICON_OPTIONS).toContain('calendar');
  });

  it('不應有重複的圖示', () => {
    const uniqueSet = new Set(ICON_OPTIONS);
    expect(uniqueSet.size).toBe(ICON_OPTIONS.length);
  });
});

// ============================================================================
// ICON_OPTIONS_V2
// ============================================================================

describe('ICON_OPTIONS_V2', () => {
  it('數量應與 ICON_OPTIONS 一致', () => {
    expect(ICON_OPTIONS_V2.length).toBe(ICON_OPTIONS.length);
  });

  it('每個項目應有 value 和 label 屬性', () => {
    for (const option of ICON_OPTIONS_V2) {
      expect(option).toHaveProperty('value');
      expect(option).toHaveProperty('label');
      expect(typeof option.value).toBe('string');
      expect(typeof option.label).toBe('string');
    }
  });

  it('value 和 label 應與 ICON_OPTIONS 對應', () => {
    ICON_OPTIONS_V2.forEach((option, idx) => {
      expect(option.value).toBe(ICON_OPTIONS[idx]);
      expect(option.label).toBe(ICON_OPTIONS[idx]);
    });
  });
});

// ============================================================================
// MODULE_NAMES
// ============================================================================

describe('MODULE_NAMES', () => {
  const expectedModules: Record<string, string> = {
    documents: '公文',
    projects: '案件',
    agencies: '單位',
    vendors: '廠商',
    reports: '報表',
    calendar: '行事曆',
  };

  it('應包含所有預期模組', () => {
    for (const key of Object.keys(expectedModules)) {
      expect(MODULE_NAMES).toHaveProperty(key);
    }
  });

  it.each(Object.entries(expectedModules))(
    '模組 "%s" 應對應中文名稱 "%s"',
    (key, expectedName) => {
      expect(MODULE_NAMES[key]).toBe(expectedName);
    },
  );

  it('所有值應為非空中文字串', () => {
    for (const value of Object.values(MODULE_NAMES)) {
      expect(typeof value).toBe('string');
      expect(value.length).toBeGreaterThan(0);
    }
  });
});

// ============================================================================
// ACTION_NAMES
// ============================================================================

describe('ACTION_NAMES', () => {
  const expectedActions: Record<string, string> = {
    read: '檢視',
    create: '新增',
    edit: '編輯',
    delete: '刪除',
    export: '匯出',
    view: '檢視',
  };

  it('應包含所有預期操作', () => {
    for (const key of Object.keys(expectedActions)) {
      expect(ACTION_NAMES).toHaveProperty(key);
    }
  });

  it.each(Object.entries(expectedActions))(
    '操作 "%s" 應對應中文名稱 "%s"',
    (key, expectedName) => {
      expect(ACTION_NAMES[key]).toBe(expectedName);
    },
  );
});

// ============================================================================
// PERMISSION_GROUPS
// ============================================================================

describe('PERMISSION_GROUPS', () => {
  it('應為非空陣列', () => {
    expect(Array.isArray(PERMISSION_GROUPS)).toBe(true);
    expect(PERMISSION_GROUPS.length).toBeGreaterThan(0);
  });

  it('每個群組應有 label 和 options 屬性', () => {
    for (const group of PERMISSION_GROUPS) {
      expect(typeof group.label).toBe('string');
      expect(group.label.length).toBeGreaterThan(0);
      expect(Array.isArray(group.options)).toBe(true);
      expect(group.options.length).toBeGreaterThan(0);
    }
  });

  it('每個選項應有 value 和 label 屬性', () => {
    for (const group of PERMISSION_GROUPS) {
      for (const option of group.options) {
        expect(typeof option.value).toBe('string');
        expect(typeof option.label).toBe('string');
        expect(option.value.length).toBeGreaterThan(0);
        expect(option.label.length).toBeGreaterThan(0);
      }
    }
  });

  it('所有 value 應唯一且不重複', () => {
    const allValues = PERMISSION_GROUPS.flatMap(g => g.options.map(o => o.value));
    const uniqueValues = new Set(allValues);
    expect(uniqueValues.size).toBe(allValues.length);
  });

  it('權限 value 格式應為 module:action', () => {
    const allValues = PERMISSION_GROUPS.flatMap(g => g.options.map(o => o.value));
    for (const value of allValues) {
      expect(value).toContain(':');
    }
  });

  it('應包含「公文管理」群組', () => {
    const docGroup = PERMISSION_GROUPS.find(g => g.label === '公文管理');
    expect(docGroup).toBeDefined();
    expect(docGroup!.options.length).toBeGreaterThanOrEqual(4);
  });

  it('應包含「系統管理」群組', () => {
    const adminGroup = PERMISSION_GROUPS.find(g => g.label === '系統管理');
    expect(adminGroup).toBeDefined();
    const adminValues = adminGroup!.options.map(o => o.value);
    expect(adminValues).toContain('admin:users');
    expect(adminValues).toContain('admin:settings');
  });

  it('應包含「角色限制」群組', () => {
    const roleGroup = PERMISSION_GROUPS.find(g => g.label === '角色限制');
    expect(roleGroup).toBeDefined();
    const roleValues = roleGroup!.options.map(o => o.value);
    expect(roleValues).toContain('role:admin');
    expect(roleValues).toContain('role:superuser');
  });
});

// ============================================================================
// formatPermissionLabel
// ============================================================================

describe('formatPermissionLabel', () => {
  it('undefined 應回傳「無限制」(綠色)', () => {
    const result = formatPermissionLabel(undefined);
    expect(result.label).toBe('無限制');
    expect(result.color).toBe('green');
  });

  it('admin: 前綴應回傳系統標籤 (紅色)', () => {
    const result = formatPermissionLabel('admin:users');
    expect(result.label).toBe('系統：users');
    expect(result.color).toBe('red');
  });

  it('role: 前綴應回傳角色標籤 (紫色)', () => {
    const result = formatPermissionLabel('role:admin');
    expect(result.label).toBe('角色：admin');
    expect(result.color).toBe('purple');
  });

  it('module:action 格式應翻譯為中文 (青色)', () => {
    const result = formatPermissionLabel('documents:read');
    expect(result.label).toBe('公文：檢視');
    expect(result.color).toBe('cyan');
  });

  it('未知模組應保留原始名稱', () => {
    const result = formatPermissionLabel('unknown_module:create');
    expect(result.label).toBe('unknown_module：新增');
    expect(result.color).toBe('cyan');
  });

  it('未知操作應保留原始名稱', () => {
    const result = formatPermissionLabel('documents:unknown_action');
    expect(result.label).toBe('公文：unknown_action');
    expect(result.color).toBe('cyan');
  });

  it('無冒號的字串應原樣回傳 (藍色)', () => {
    const result = formatPermissionLabel('some-permission');
    expect(result.label).toBe('some-permission');
    expect(result.color).toBe('blue');
  });
});
