/**
 * 知識圖譜節點配置
 *
 * 集中定義所有節點類型的視覺樣式與行為屬性。
 * KnowledgeGraph.tsx 及其他圖譜相關元件統一由此匯入。
 *
 * v2.0: 新增 description + 使用者覆蓋機制 (localStorage)
 *
 * @version 2.0.0
 * @created 2026-02-24
 * @updated 2026-02-24
 */

// ============================================================================
// 單一節點配置型別
// ============================================================================

export interface GraphNodeTypeConfig {
  /** 節點顏色 (hex) */
  color: string;
  /** 基礎半徑 (px)，實際大小會加上 mention_count 加成 */
  radius: number;
  /** 中文顯示標籤 */
  label: string;
  /** 是否可透過 Phase 2 API 查詢正規化實體詳情 */
  detailable: boolean;
  /** 給使用者看的用途說明 */
  description: string;
}

// ============================================================================
// 節點類型配置表（內建預設）
// ============================================================================

export const GRAPH_NODE_CONFIG: Record<string, GraphNodeTypeConfig> = {
  // --- 業務實體 ---
  document:  { color: '#1890ff', radius: 6, label: '公文',     detailable: false, description: '系統中的收發文公文記錄' },
  project:   { color: '#52c41a', radius: 9, label: '專案',     detailable: false, description: '承攬的合約工程專案' },
  agency:    { color: '#fa8c16', radius: 5, label: '機關',     detailable: false, description: '公文往來的政府機關' },
  dispatch:  { color: '#722ed1', radius: 7, label: '派工',     detailable: false, description: '桃園市政府的派工通知單' },
  typroject: { color: '#2f54eb', radius: 7, label: '桃園工程', detailable: false, description: '桃園市政府的工程案件' },
  // --- NER 提取實體 ---
  org:         { color: '#d48806', radius: 5, label: '組織',     detailable: true,  description: 'AI 從公文內容提取的組織/單位名稱' },
  person:      { color: '#f5222d', radius: 5, label: '人物',     detailable: true,  description: 'AI 從公文內容提取的人名' },
  ner_project: { color: '#a0d911', radius: 5, label: '工程名稱', detailable: true,  description: 'AI 從公文內容提取的專案/工程名稱' },
  location:    { color: '#faad14', radius: 4, label: '地點',     detailable: true,  description: 'AI 從公文內容提取的地點/地址' },
  date:        { color: '#13c2c2', radius: 4, label: '日期',     detailable: true,  description: 'AI 從公文內容提取的重要日期' },
  topic:       { color: '#eb2f96', radius: 5, label: '主題',     detailable: true,  description: 'AI 從公文內容提取的主題/關鍵字' },
};

// ============================================================================
// 衍生常數（從配置表自動產生）
// ============================================================================

/** 未知類型的 fallback 配置 */
export const DEFAULT_NODE_CONFIG: GraphNodeTypeConfig = {
  color: '#999999',
  radius: 5,
  label: '未知',
  detailable: false,
  description: '未知類型的節點',
};

/** 取得內建節點配置，未知類型回傳 fallback */
export function getNodeConfig(type: string): GraphNodeTypeConfig {
  return GRAPH_NODE_CONFIG[type] ?? DEFAULT_NODE_CONFIG;
}

/** 所有已知節點類型 */
export const KNOWN_NODE_TYPES = Object.keys(GRAPH_NODE_CONFIG);

/** 可查詢正規化實體詳情的類型集合 */
export const CANONICAL_ENTITY_TYPES = new Set(
  Object.entries(GRAPH_NODE_CONFIG)
    .filter(([, cfg]) => cfg.detailable)
    .map(([type]) => type)
);

// ============================================================================
// 使用者覆蓋機制 (localStorage)
// ============================================================================

const STORAGE_KEY = 'kg_node_config_overrides';

/** 使用者可覆蓋的欄位 */
export interface NodeConfigOverride {
  color?: string;
  label?: string;
  description?: string;
  visible?: boolean;
}

export type NodeConfigOverrides = Record<string, NodeConfigOverride>;

/** 讀取使用者覆蓋設定 */
export function getUserOverrides(): NodeConfigOverrides {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as NodeConfigOverrides;
  } catch {
    return {};
  }
}

/** 寫入使用者覆蓋設定 */
export function saveUserOverrides(overrides: NodeConfigOverrides): void {
  try {
    // 清除空覆蓋
    const cleaned: NodeConfigOverrides = {};
    for (const [key, val] of Object.entries(overrides)) {
      if (val && Object.keys(val).length > 0) {
        cleaned[key] = val;
      }
    }
    if (Object.keys(cleaned).length === 0) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cleaned));
    }
  } catch {
    // localStorage 不可用時靜默失敗
  }
}

/** 重置所有使用者覆蓋 */
export function resetUserOverrides(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 靜默
  }
}

export interface MergedNodeConfig extends GraphNodeTypeConfig {
  visible: boolean;
}

/** 取得合併後的節點配置（內建預設 + 使用者覆蓋） */
export function getMergedNodeConfig(type: string): MergedNodeConfig {
  const base = GRAPH_NODE_CONFIG[type] ?? DEFAULT_NODE_CONFIG;
  const overrides = getUserOverrides();
  const ov = overrides[type];

  if (!ov) {
    return { ...base, visible: true };
  }

  return {
    color: ov.color ?? base.color,
    radius: base.radius,
    label: ov.label ?? base.label,
    detailable: base.detailable,
    description: ov.description ?? base.description,
    visible: ov.visible ?? true,
  };
}

/** 取得所有類型的合併配置（只讀一次 localStorage） */
export function getAllMergedConfigs(): Record<string, MergedNodeConfig> {
  const overrides = getUserOverrides();
  const result: Record<string, MergedNodeConfig> = {};
  for (const [type, base] of Object.entries(GRAPH_NODE_CONFIG)) {
    const ov = overrides[type];
    result[type] = ov
      ? {
          color: ov.color ?? base.color,
          radius: base.radius,
          label: ov.label ?? base.label,
          detailable: base.detailable,
          description: ov.description ?? base.description,
          visible: ov.visible ?? true,
        }
      : { ...base, visible: true };
  }
  return result;
}
