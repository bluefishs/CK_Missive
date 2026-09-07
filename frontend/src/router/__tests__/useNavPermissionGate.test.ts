/**
 * 路由照選單宣告擋（owner 2026-09-07：「知道網址就可檢視」）。
 *
 * 這一組鎖的是**前綴比對**：列表擋住了而詳情頁照樣打得開，那種擋法等於沒擋。
 */
import { describe, it, expect } from 'vitest';
import { buildNavPermissionMap, resolveRequiredPermission } from '../useNavPermissionGate';

const rows = [
  { path: '/erp/ledger', permission_required: ['reports:erp:view'], is_enabled: true },
  { path: '/erp/quotations', permission_required: ['reports:finance:view'], is_enabled: true },
  { path: '/ai/erp-graph', permission_required: ['reports:erp:view'], is_enabled: true },
  { path: '/dashboard', permission_required: [], is_enabled: true },
  { path: '/disabled-page', permission_required: ['admin:users'], is_enabled: false },
  { path: '', permission_required: ['x'], is_enabled: true },
];

describe('buildNavPermissionMap', () => {
  it('只收有宣告權限、且啟用中的路徑', () => {
    const map = buildNavPermissionMap(rows);
    expect(map['/erp/ledger']).toBe('reports:erp:view');
    expect(map['/dashboard']).toBeUndefined();
    expect(map['/disabled-page']).toBeUndefined();
  });

  it('宣告是字串化的陣列時也要解得出來（jsonb 兩種取回形狀）', () => {
    const map = buildNavPermissionMap([
      { path: '/a', permission_required: '["reports:erp:view"]', is_enabled: true },
      { path: '/b', permission_required: 'admin:users', is_enabled: true },
      { path: '/c', permission_required: '[]', is_enabled: true },
    ]);
    expect(map['/a']).toBe('reports:erp:view');
    expect(map['/b']).toBe('admin:users');
    expect(map['/c']).toBeUndefined();
  });
});

describe('resolveRequiredPermission', () => {
  const map = buildNavPermissionMap(rows);

  it('完全相符', () => {
    expect(resolveRequiredPermission('/erp/ledger', map)).toBe('reports:erp:view');
  });

  it('詳情頁沿用列表的宣告——否則列表擋住、詳情頁照樣打得開', () => {
    expect(resolveRequiredPermission('/erp/quotations/541', map)).toBe('reports:finance:view');
  });

  it('取最長前綴，不是第一個命中的', () => {
    const m = buildNavPermissionMap([
      { path: '/erp', permission_required: ['reports:erp:view'], is_enabled: true },
      { path: '/erp/quotations', permission_required: ['reports:finance:view'], is_enabled: true },
    ]);
    expect(resolveRequiredPermission('/erp/quotations/1', m)).toBe('reports:finance:view');
  });

  it('沒有宣告就放行——這一層只執行既有宣告，不自己發明限制', () => {
    expect(resolveRequiredPermission('/profile', map)).toBeNull();
  });

  it('不得把 /erp-something 誤當成 /erp 的子路徑', () => {
    const m = buildNavPermissionMap([{ path: '/erp', permission_required: ['reports:erp:view'], is_enabled: true }]);
    expect(resolveRequiredPermission('/erp-report', m)).toBeNull();
  });
});
