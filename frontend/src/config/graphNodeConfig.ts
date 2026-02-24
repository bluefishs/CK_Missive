/**
 * 知識圖譜節點配置
 *
 * 集中定義所有節點類型的視覺樣式與行為屬性。
 * KnowledgeGraph.tsx 及其他圖譜相關元件統一由此匯入。
 *
 * @version 1.0.0
 * @created 2026-02-24
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
}

// ============================================================================
// 節點類型配置表
// ============================================================================

export const GRAPH_NODE_CONFIG: Record<string, GraphNodeTypeConfig> = {
  // --- 業務實體 ---
  document:  { color: '#1890ff', radius: 6, label: '公文',     detailable: false },
  project:   { color: '#52c41a', radius: 9, label: '專案',     detailable: false },
  agency:    { color: '#fa8c16', radius: 5, label: '機關',     detailable: false },
  dispatch:  { color: '#722ed1', radius: 7, label: '派工',     detailable: false },
  typroject: { color: '#2f54eb', radius: 7, label: '桃園工程', detailable: false },
  // --- NER 提取實體 ---
  org:       { color: '#d48806', radius: 5, label: '組織',     detailable: true },
  person:    { color: '#f5222d', radius: 5, label: '人物',     detailable: true },
  location:  { color: '#faad14', radius: 4, label: '地點',     detailable: true },
  date:      { color: '#13c2c2', radius: 4, label: '日期',     detailable: true },
  topic:     { color: '#eb2f96', radius: 5, label: '主題',     detailable: true },
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
};

/** 取得節點配置，未知類型回傳 fallback */
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
