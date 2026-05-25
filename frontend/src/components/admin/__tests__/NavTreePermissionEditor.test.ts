/**
 * NavTreePermissionEditor 純函式單元測試
 *
 * 涵蓋 v1.2 父子級聯邏輯：
 * - collectAllNavPerms — 從 tree 收集所有 nav perm
 * - computeCascadedDraft — 根據勾選的 nav perm 計算新 draft（保留 nav 外 perm）
 *
 * 執行：
 *   cd frontend && npx vitest run src/components/admin/__tests__/NavTreePermissionEditor.test.ts
 */
import { describe, it, expect } from 'vitest';
import {
  collectAllNavPerms,
  computeCascadedDraft,
} from '../NavTreePermissionEditor';
import type { NavTreeNode } from '../../../api/rolePermissionsApi';

const mkNode = (
  id: number,
  perms: string[],
  children: NavTreeNode[] = [],
): NavTreeNode => ({
  id,
  parent_id: null,
  key: `nav-${id}`,
  title: `Nav ${id}`,
  path: null,
  level: 0,
  sort_order: id,
  is_enabled: true,
  is_visible: true,
  permission_required: perms,
  children,
});

describe('collectAllNavPerms', () => {
  it('扁平 tree — 收集 root 節點 perm', () => {
    const tree: NavTreeNode[] = [
      mkNode(1, ['documents:read']),
      mkNode(2, ['admin:users']),
    ];
    const result = collectAllNavPerms(tree);
    expect(result.size).toBe(2);
    expect(result.has('documents:read')).toBe(true);
    expect(result.has('admin:users')).toBe(true);
  });

  it('巢狀 tree — 遞迴收集子孫 perm', () => {
    const tree: NavTreeNode[] = [
      mkNode(1, ['root:perm'], [
        mkNode(2, ['child1:perm'], [
          mkNode(4, ['grandchild:perm']),
        ]),
        mkNode(3, ['child2:perm']),
      ]),
    ];
    const result = collectAllNavPerms(tree);
    expect(result.size).toBe(4);
    expect(result.has('grandchild:perm')).toBe(true);
  });

  it('多 nav 共享同 perm — set 去重', () => {
    const tree: NavTreeNode[] = [
      mkNode(1, ['shared:perm']),
      mkNode(2, ['shared:perm', 'unique:perm']),
    ];
    const result = collectAllNavPerms(tree);
    expect(result.size).toBe(2);
  });

  it('空 tree → 空 set', () => {
    expect(collectAllNavPerms([]).size).toBe(0);
  });

  it('節點無 perm → 不入集合', () => {
    const tree: NavTreeNode[] = [mkNode(1, [])];
    expect(collectAllNavPerms(tree).size).toBe(0);
  });
});

describe('computeCascadedDraft', () => {
  it('純 cascade — checkedNavPerms 完整覆蓋', () => {
    const allNavPerms = new Set(['a', 'b', 'c']);
    const oldDraft: string[] = [];
    const checkedNavPerms = new Set(['a', 'b']);
    expect(computeCascadedDraft(allNavPerms, oldDraft, checkedNavPerms)).toEqual(['a', 'b']);
  });

  it('保留 nav 外 perm — 後端 endpoint perm 不被誤刪', () => {
    const allNavPerms = new Set(['nav:a', 'nav:b']);
    const oldDraft = ['nav:a', 'business:x', 'business:y'];
    const checkedNavPerms = new Set(['nav:b']);
    const result = computeCascadedDraft(allNavPerms, oldDraft, checkedNavPerms);
    // nav:a 取消勾選（不在 checkedNavPerms）→ 移除
    // nav:b 新勾選 → 加入
    // business:x/y 不屬 nav perm → 保留
    expect(result).toEqual(['business:x', 'business:y', 'nav:b']);
  });

  it('全勾 cascade — 父勾後子應一起 in', () => {
    const allNavPerms = new Set(['parent', 'child1', 'child2']);
    const oldDraft: string[] = [];
    // antd Tree 父勾選自動 cascade 子，info.checkedNodes 應包含父+子三節點
    const checkedNavPerms = new Set(['parent', 'child1', 'child2']);
    expect(computeCascadedDraft(allNavPerms, oldDraft, checkedNavPerms)).toEqual([
      'child1', 'child2', 'parent',
    ]);
  });

  it('全取消 cascade — 父反勾後子應一起移除', () => {
    const allNavPerms = new Set(['parent', 'child1', 'child2']);
    const oldDraft = ['parent', 'child1', 'child2', 'business:x'];
    const checkedNavPerms = new Set<string>(); // 全部反勾
    const result = computeCascadedDraft(allNavPerms, oldDraft, checkedNavPerms);
    expect(result).toEqual(['business:x']);
  });

  it('排序去重 — 重複 perm 與亂序', () => {
    const allNavPerms = new Set(['a', 'b']);
    const oldDraft = ['z', 'a', 'z']; // a 屬 nav，z 不屬
    const checkedNavPerms = new Set(['a', 'b']);
    const result = computeCascadedDraft(allNavPerms, oldDraft, checkedNavPerms);
    expect(result).toEqual(['a', 'b', 'z']); // 排序、去重
  });

  it('空 navTree — 完全保留 oldDraft', () => {
    const allNavPerms = new Set<string>();
    const oldDraft = ['p1', 'p2'];
    const checkedNavPerms = new Set<string>();
    expect(computeCascadedDraft(allNavPerms, oldDraft, checkedNavPerms)).toEqual(['p1', 'p2']);
  });
});

/**
 * P-59 (v1.3, 5/07)：per-node toggle 邏輯（NavTreePermissionEditor 內部 handleCheck 改寫後）
 *
 * 取消 cascade 行為，每節點獨立切換：
 * - 勾選某節點 → 把該節點的 perms 加入 draft
 * - 取消某節點 → 把該節點的 perms 從 draft 移除
 * - 共享同 perm 的其他 nav 視覺上同步更新（perm 才是 SSOT）
 *
 * 此處純粹模擬 handleCheck 的核心邏輯（無 React 渲染）。
 */
function applyPerNodeToggle(
  oldDraft: string[],
  nodePerms: string[],
  checked: boolean,
): string[] {
  const set = new Set(oldDraft);
  if (checked) {
    nodePerms.forEach((p) => set.add(p));
  } else {
    nodePerms.forEach((p) => set.delete(p));
  }
  return Array.from(set).sort();
}

describe('per-node toggle (P-59 checkStrictly)', () => {
  it('勾單一節點 → 只加入該節點的 perms', () => {
    const result = applyPerNodeToggle(['existing:perm'], ['nav:a', 'nav:b'], true);
    expect(result).toEqual(['existing:perm', 'nav:a', 'nav:b']);
  });

  it('取消單一節點 → 只移除該節點的 perms（不影響其他 nav 外 perm）', () => {
    const result = applyPerNodeToggle(
      ['nav:a', 'nav:b', 'nav:c', 'business:x'],
      ['nav:a'],
      false,
    );
    expect(result).toEqual(['business:x', 'nav:b', 'nav:c']);
  });

  it('取消父節點 → 不再 cascade 移除子節點 perms（v1.2 → v1.3 行為差異）', () => {
    // 假設父 perm = 'parent', 子 perms = ['child1', 'child2']
    // checkStrictly 模式下，「取消父」只移除 'parent'
    const oldDraft = ['parent', 'child1', 'child2'];
    const result = applyPerNodeToggle(oldDraft, ['parent'], false);
    expect(result).toEqual(['child1', 'child2']);
  });

  it('共享 perm 取消 — 同 perm 其他 nav 連動為視覺問題（業務本質，非 cascade bug）', () => {
    // nav 1, 2 都需要 'shared:perm'
    // 取消 nav 1 → perm 移除 → nav 2 也視覺上 unchecked（這是 perm SSOT 必然結果）
    const oldDraft = ['shared:perm'];
    const result = applyPerNodeToggle(oldDraft, ['shared:perm'], false);
    expect(result).toEqual([]);
  });

  it('重複勾選 idempotent — 不會重複加入', () => {
    const result = applyPerNodeToggle(['a:b'], ['a:b'], true);
    expect(result).toEqual(['a:b']);
  });

  it('取消未在 draft 的 perm idempotent — 安全 no-op', () => {
    const result = applyPerNodeToggle(['x:y'], ['nonexistent:perm'], false);
    expect(result).toEqual(['x:y']);
  });
});
