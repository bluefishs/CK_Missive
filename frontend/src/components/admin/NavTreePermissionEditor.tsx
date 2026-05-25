/**
 * NavTreePermissionEditor — 依選單階層編輯權限（ADR-0034 配套）
 *
 * 設計：
 * - 用 antd Tree 渲染 site_navigation_items 完整階層（含 group / page / 子 page）
 * - 每個有 permission_required 的節點 checkbox（勾選 = 把該 perm 加入 role）
 * - 多 nav 共用同 perm 時：勾任一即勾全部，UI 標示「同時影響 N 個選單」
 * - 沒 permission_required 的節點標「公開」
 * - **搜尋過濾**（v1.1）：title / path / perm 模糊搜尋，自動展開匹配節點
 * - **顯示模式 filter**（v1.1）：全部 / 已授權 / 未授權 / 公開
 * - **重新整理**（v1.1）：site-management 變動後一鍵刷新樹
 *
 * @version 1.1.0
 * @date 2026-05-07
 */
import React, { useMemo, useState, useEffect } from 'react';
import {
  Tree, Tag, Typography, Space, Empty, Spin, Tooltip,
  Input, Segmented, Button,
} from 'antd';
import {
  LockOutlined, GlobalOutlined, InfoCircleOutlined,
  SearchOutlined, ReloadOutlined,
} from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import type { NavTreeNode, NavTreeResponse } from '../../api/rolePermissionsApi';

const { Text } = Typography;

interface Props {
  data: NavTreeResponse | undefined;
  isLoading: boolean;
  draftPermissions: string[];
  /**
   * v1.2：傳完整新 draft（推薦，支援父子級聯批次）。
   * 介面從「toggle」改為「set」 — antd Tree onCheck cascade 會自動觸發子節點，
   * 我們從 checkedNodes 收集所有 nav perm 一次計算完整 draft。
   */
  onDraftChange: (newDraft: string[]) => void;
  /** 重新整理（觸發 useNavTree refetch） */
  onRefetch?: () => void;
  readOnly?: boolean;
}

type FilterMode = 'all' | 'granted' | 'ungranted' | 'public';

const FILTER_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '已授權', value: 'granted' },
  { label: '未授權', value: 'ungranted' },
  { label: '公開', value: 'public' },
];

/**
 * 過濾 + 搜尋邏輯：
 * - 若節點符合條件（matched）→ 保留
 * - 若節點任一子孫 matched → 保留並繼續展開
 * - 否則剔除
 *
 * 回傳：{ filteredNodes, matchedKeys（用於高亮） }
 */
function filterTree(
  nodes: NavTreeNode[],
  searchLower: string,
  mode: FilterMode,
  draftSet: Set<string>,
): { filtered: NavTreeNode[]; matched: Set<string>; expandedKeys: string[] } {
  const matched = new Set<string>();
  const expandedKeys: string[] = [];

  function visit(node: NavTreeNode): NavTreeNode | null {
    // 條件 1：模式過濾
    const hasPerm = node.permission_required.length > 0;
    const allGranted = hasPerm && node.permission_required.every((p) => draftSet.has(p));
    const someGranted = hasPerm && node.permission_required.some((p) => draftSet.has(p));

    let modeMatch = false;
    if (mode === 'all') modeMatch = true;
    else if (mode === 'granted') modeMatch = allGranted;
    else if (mode === 'ungranted') modeMatch = hasPerm && !someGranted;
    else if (mode === 'public') modeMatch = !hasPerm;

    // 條件 2：搜尋過濾
    let searchMatch = !searchLower;
    if (searchLower) {
      const haystack = [
        node.title || '',
        node.key || '',
        node.path || '',
        ...node.permission_required,
      ].join(' ').toLowerCase();
      searchMatch = haystack.includes(searchLower);
    }

    const selfMatch = modeMatch && searchMatch;

    // 遞迴 children
    const filteredChildren = node.children
      .map(visit)
      .filter((x): x is NavTreeNode => x !== null);

    if (selfMatch || filteredChildren.length > 0) {
      if (selfMatch) matched.add(`nav-${node.id}`);
      expandedKeys.push(`nav-${node.id}`);
      return { ...node, children: filteredChildren };
    }
    return null;
  }

  const filtered = nodes.map(visit).filter((x): x is NavTreeNode => x !== null);
  return { filtered, matched, expandedKeys };
}

/** 將 NavTreeNode 轉為 antd DataNode */
function toAntdTreeData(
  nodes: NavTreeNode[],
  permToNav: NavTreeResponse['perm_to_nav'],
  draftPermsSet: Set<string>,
  matchedKeys: Set<string>,
): DataNode[] {
  return nodes.map((n) => {
    const perms = n.permission_required;
    const hasPerm = perms.length > 0;
    const allChecked = hasPerm && perms.every((p) => draftPermsSet.has(p));
    const someChecked = hasPerm && perms.some((p) => draftPermsSet.has(p));
    const isMatched = matchedKeys.has(`nav-${n.id}`);

    const sharedNavInfo = perms
      .map((p) => {
        const sharedNavs = permToNav[p] || [];
        if (sharedNavs.length > 1) {
          const otherCount = sharedNavs.length - 1;
          return `${p} (同時影響 +${otherCount} 個選單)`;
        }
        return p;
      })
      .join(' / ');

    const titleStyle: React.CSSProperties = isMatched
      ? { background: '#fffbe6', padding: '0 4px', borderRadius: 3 }
      : {};

    const title = (
      <Space size={8} style={{ alignItems: 'center', ...titleStyle }}>
        <Text strong={!n.parent_id} style={{ fontSize: !n.parent_id ? 14 : 13 }}>
          {n.title}
        </Text>
        {!n.is_enabled && <Tag color="default" style={{ fontSize: 10 }}>已停用</Tag>}
        {!n.is_visible && <Tag color="default" style={{ fontSize: 10 }}>隱藏</Tag>}
        {!hasPerm && (
          <Tag color="green" icon={<GlobalOutlined />} style={{ fontSize: 10 }}>公開</Tag>
        )}
        {hasPerm && (
          <Tooltip title={sharedNavInfo}>
            <Tag
              color={allChecked ? 'blue' : someChecked ? 'gold' : 'orange'}
              icon={<LockOutlined />}
              style={{ fontSize: 10 }}
            >
              {perms.length === 1 ? perms[0] : `${perms.length} perms`}
            </Tag>
          </Tooltip>
        )}
        {n.path && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            <code>{n.path}</code>
          </Text>
        )}
      </Space>
    );

    return {
      key: `nav-${n.id}`,
      title,
      _navPermissions: perms,
      checkable: hasPerm,
      children: n.children.length > 0
        ? toAntdTreeData(n.children, permToNav, draftPermsSet, matchedKeys)
        : undefined,
    } as DataNode & { _navPermissions: string[] };
  });
}

/**
 * 收集整棵 tree 用到的所有 nav perm（給 cascade 計算用）
 * 匯出供單元測試。
 */
// eslint-disable-next-line react-refresh/only-export-components
export function collectAllNavPerms(nodes: NavTreeNode[]): Set<string> {
  const set = new Set<string>();
  const walk = (ns: NavTreeNode[]) => {
    for (const n of ns) {
      n.permission_required.forEach((p) => set.add(p));
      if (n.children.length > 0) walk(n.children);
    }
  };
  walk(nodes);
  return set;
}

/**
 * v1.2 父子級聯純函式：根據「當前勾選的 nav 節點集合」計算新 draft。
 *
 * 規則：
 * - 保留 oldDraft 中「不屬於 nav-tree 任何節點」的 perm（純後端 endpoint perm）。
 * - 加入「目前勾選 nav 節點」的所有 perm（antd Tree onCheck 已自動 cascade）。
 * - 排序去重。
 *
 * 匯出供單元測試與外部呼叫者使用。
 */
// eslint-disable-next-line react-refresh/only-export-components
export function computeCascadedDraft(
  allNavPerms: Set<string>,
  oldDraft: string[],
  checkedNavPerms: Set<string>,
): string[] {
  const preservedOutsideNav = oldDraft.filter((p) => !allNavPerms.has(p));
  return Array.from(new Set([...preservedOutsideNav, ...checkedNavPerms])).sort();
}

function collectCheckedKeys(
  nodes: NavTreeNode[],
  draftPermsSet: Set<string>,
): string[] {
  const keys: string[] = [];
  const walk = (ns: NavTreeNode[]) => {
    for (const n of ns) {
      const perms = n.permission_required;
      if (perms.length > 0 && perms.every((p) => draftPermsSet.has(p))) {
        keys.push(`nav-${n.id}`);
      }
      if (n.children.length > 0) walk(n.children);
    }
  };
  walk(nodes);
  return keys;
}

export const NavTreePermissionEditor: React.FC<Props> = ({
  data,
  isLoading,
  draftPermissions,
  onDraftChange,
  onRefetch,
  readOnly,
}) => {
  const [search, setSearch] = useState('');
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  // 受控 expandedKeys — 初次 data 載入時自動展開全部，使用者後續可手動 collapse
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  // 收集整棵 tree 全部 keys（給初始展開用）
  const allKeys = useMemo(() => {
    if (!data?.tree) return [] as string[];
    const keys: string[] = [];
    const walk = (ns: NavTreeNode[]) => {
      for (const n of ns) {
        keys.push(`nav-${n.id}`);
        if (n.children.length > 0) walk(n.children);
      }
    };
    walk(data.tree);
    return keys;
  }, [data]);

  // data 第一次載入時自動展開全部；後續 data 變動且 user 還在初始狀態時也跟著補
  useEffect(() => {
    if (allKeys.length > 0 && expandedKeys.length === 0) {
      setExpandedKeys(allKeys);
    }
  }, [allKeys, expandedKeys.length]);

  const draftSet = useMemo(() => new Set(draftPermissions), [draftPermissions]);

  const { filtered, matched, autoExpandKeys } = useMemo(() => {
    if (!data?.tree) return { filtered: [] as NavTreeNode[], matched: new Set<string>(), autoExpandKeys: [] as string[] };
    const result = filterTree(data.tree, search.toLowerCase(), filterMode, draftSet);
    return { filtered: result.filtered, matched: result.matched, autoExpandKeys: result.expandedKeys };
  }, [data, search, filterMode, draftSet]);

  const treeData = useMemo(() => {
    if (!data) return [];
    return toAntdTreeData(filtered, data.perm_to_nav, draftSet, matched);
  }, [filtered, data, draftSet, matched]);

  const checkedKeysList = useMemo(() => {
    if (!data?.tree) return [] as string[];
    return collectCheckedKeys(data.tree, draftSet);
  }, [data, draftSet]);

  // checkStrictly={true} 下 antd Tree 期望 { checked, halfChecked } 物件
  const checkedKeys = useMemo(
    () => ({ checked: checkedKeysList, halfChecked: [] as React.Key[] }),
    [checkedKeysList],
  );

  // 統計（在原始 tree 上計算，不受 filter 影響）
  const stats = useMemo(() => {
    if (!data?.tree) return { total: 0, granted: 0, ungranted: 0, publicCount: 0 };
    let total = 0, granted = 0, ungranted = 0, publicCount = 0;
    const walk = (ns: NavTreeNode[]) => {
      for (const n of ns) {
        total++;
        const perms = n.permission_required;
        if (perms.length === 0) publicCount++;
        else if (perms.every((p) => draftSet.has(p))) granted++;
        else ungranted++;
        if (n.children.length > 0) walk(n.children);
      }
    };
    walk(data.tree);
    return { total, granted, ungranted, publicCount };
  }, [data, draftSet]);

  // 注：v1.3 改為 checkStrictly + per-node toggle 後，allNavPerms / computeCascadedDraft
  // 不再用於 React 元件內部，但保留為 export 以便外部呼叫者與單元測試引用 cascade 純函式。
  // 不再呼叫 collectAllNavPerms 避免 ESLint 警告 unused。

  /**
   * v1.3（P-59，5/07）：改 checkStrictly — 每個節點獨立切換，不再父子聯動。
   *
   * 解決問題：
   * - 「取消勾選某選單，多個其他選單也同步被關閉」
   *   → 之前 onCheck cascade 會抹掉子節點的 perm；
   *     而且兩個 nav 共享同 perm 時，取消其一導致 perm 從 draft 移除 → 另一個也視為未勾選。
   *
   * 新行為：
   * - info.checked 表示這次點擊是「勾」(true) 或「取消」(false)
   * - info.node._navPermissions 是這個節點自身的 perms
   * - 勾 → 把這節點的 perms 加入 draft
   * - 取消 → 把這節點的 perms 從 draft 移除（不影響其他節點 — 但若其他 nav 共享同 perm，
   *   它們也會視覺上連動更新，這是「perm 才是 SSOT」的本質，無法迴避）
   *
   * 注意：cascade 失能後，要勾「父節點 + 全部子」必須一個個點 — 但取消單一不再連坐他人。
   */
  const handleCheck = (
    _keys: { checked: React.Key[]; halfChecked: React.Key[] } | { checked: React.Key[] } | React.Key[],
    info: { checked: boolean; node: DataNode & { _navPermissions?: string[] } },
  ) => {
    const nodePerms = info.node?._navPermissions || [];
    if (nodePerms.length === 0) return;

    const draftSetCopy = new Set(draftPermissions);
    if (info.checked) {
      nodePerms.forEach((p) => draftSetCopy.add(p));
    } else {
      nodePerms.forEach((p) => draftSetCopy.delete(p));
    }
    const newDraft = Array.from(draftSetCopy).sort();
    onDraftChange(newDraft);
  };

  if (isLoading) return <Spin />;
  if (!data || !data.tree.length) return <Empty description="無選單資料" />;

  return (
    <div>
      {/* 工具列 */}
      <Space
        wrap
        style={{ marginBottom: 12, width: '100%', justifyContent: 'space-between' }}
      >
        <Space wrap>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="搜尋 title / path / permission key..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 320 }}
          />
          <Segmented
            options={FILTER_OPTIONS}
            value={filterMode}
            onChange={(v) => setFilterMode(v as FilterMode)}
          />
        </Space>
        <Space>
          <Tooltip title="從 site-management 加新 nav 後刷新此樹">
            <Button
              icon={<ReloadOutlined />}
              onClick={() => onRefetch?.()}
              size="small"
            >
              重新整理
            </Button>
          </Tooltip>
        </Space>
      </Space>

      {/* 統計 */}
      <Space
        wrap
        style={{ marginBottom: 12 }}
        split={<span style={{ color: '#d9d9d9' }}>|</span>}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          總計 <strong>{stats.total}</strong> 個選單
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          已授權 <Tag color="blue">{stats.granted}</Tag>
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          未授權 <Tag color="orange">{stats.ungranted}</Tag>
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          公開 <Tag color="green">{stats.publicCount}</Tag>
        </Text>
        {(search || filterMode !== 'all') && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            <InfoCircleOutlined /> 過濾後顯示 <strong>{matched.size}</strong> 個匹配
          </Text>
        )}
      </Space>

      {/* 提示 */}
      <Space style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          <InfoCircleOutlined /> 點擊勾選即把該選單的 permission 加入 role。
          多 nav 共用同 perm 時，勾任一即同步勾全部（tooltip 標示影響範圍）。
        </Text>
      </Space>

      {filtered.length === 0 ? (
        <Empty description="無符合條件的選單" />
      ) : (
        <Tree
          treeData={treeData}
          checkable
          checkStrictly
          checkedKeys={checkedKeys}
          onCheck={handleCheck as never}
          expandedKeys={search || filterMode !== 'all' ? autoExpandKeys : expandedKeys}
          onExpand={(keys) => setExpandedKeys(keys)}
          disabled={readOnly}
          selectable={false}
          showIcon={false}
        />
      )}
    </div>
  );
};

export default NavTreePermissionEditor;
