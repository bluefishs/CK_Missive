/**
 * KnowledgeGraph 內部型別與常數
 *
 * @version 1.1.0
 * @created 2026-02-27
 * @updated 2026-03-14 — 加入 ForceGraphNodeObject / ForceGraphLinkObject 泛型別名
 */

// ============================================================================
// Force-Graph 內部型別
// ============================================================================

export interface ForceNode {
  id: string;
  label: string;
  fullLabel?: string | null;
  type: string;
  color: string;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
  mention_count?: number;
  source_project?: string;
  x?: number;
  y?: number;
  z?: number;
}

export interface ForceLink {
  source: string | ForceNode;
  target: string | ForceNode;
  label: string;
  type: string;
  weight?: number;
}

export interface GraphData {
  nodes: ForceNode[];
  links: ForceLink[];
}

// ============================================================================
// react-force-graph 泛型別名
// ============================================================================

/**
 * react-force-graph NodeObject — 攜帶 ForceNode 自訂欄位。
 *
 * 使用 NodeObject<ForceNode> 會導致 `string & ForceNode` 因為 ForceNode.id
 * 是 `string`（非 optional），而 NodeObject 的 id 是 `string | number | undefined`。
 * 為避免此問題，直接以結構型別定義。
 */
export type ForceGraphNodeObject = ForceNode & D3IndexSignature & {
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
};

/**
 * react-force-graph LinkObject — 攜帶 ForceLink 自訂欄位。
 *
 * source/target 在力模擬後會被 d3 替換為 NodeObject 參考。
 */
export type ForceGraphLinkObject = ForceLink & D3IndexSignature;

/**
 * D3 力模擬中的節點（用於 forceCollide / forceX / forceY 等回調）。
 * d3-force 的 SimulationNodeDatum 會注入 index / x / y / vx / vy 等欄位，
 * 但 ForceNode 自訂欄位（type、mention_count 等）也需要存取。
 * 加入 index signature 以相容 d3Force 的 ForceFn<NodeObject<{}>> 型別。
 */
/** d3-force 相容的 index signature（NodeObject 使用 `[others: string]: any`） */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type D3IndexSignature = { [others: string]: any };

export type D3SimNode = ForceNode & D3IndexSignature & {
  index?: number;
  vx?: number;
  vy?: number;
  vz?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
};

// ============================================================================
// 常數
// ============================================================================

/** 邊類型色彩映射 — 結構化=冷色, NER=暖色, 派工=輔助色 */
export const EDGE_COLORS: Record<string, string> = {
  sends: '#1890ff',           // 發文 — 藍
  receives: '#52c41a',        // 受文 — 綠
  belongs_to: '#722ed1',      // 所屬專案 — 紫
  reply: '#fa8c16',           // 收發配對 — 橙
  mentions: '#eb2f96',        // NER 提及 — 洋紅
  dispatch_link: '#13c2c2',   // 派工關聯 — 青
  agency_doc: '#2f54eb',      // 機關公文 — 深藍
  company_doc: '#f5222d',     // 乾坤公文 — 紅
  dispatch_project: '#a0d911', // 關聯工程 — 萊姆
  agency_entity: '#fa541c',   // 機關實體 — 火橙
  project_entity: '#389e0d',  // 工程實體 — 深綠
  dispatch_entity: '#13c2c2', // 派工實體 — 青
  co_mention: '#bfbfbf',      // 共現 — 淺灰
  manages: '#d48806',         // 管理 — 暗金
  located_in: '#faad14',      // 位於 — 金
  related_to: '#8c8c8c',      // 相關 — 灰
  // Skills Capability Map 關聯 (v2.0 — 3 層階層式)
  contains: '#999999',          // 包含 — 灰 (層→能力)
  implements: '#1890ff',        // 實現 — 藍 (能力→技能)
  depends_on: '#ff4d4f',        // 依賴 — 紅 (能力→能力)
  enhances: '#52c41a',          // 強化 — 綠 (能力→能力)
  feeds: '#faad14',             // 資料流 — 橘 (技能→技能)
  integrates: '#722ed1',        // 整合 — 紫 (技能→技能)
  evolves_to: '#ff85c0',        // 演進 — 粉 (現在→未來)
  // Legacy skill map edges (backward compat)
  uses: '#1890ff',              // 使用 — 藍
  requires: '#52c41a',          // 需要 — 綠
  triggers: '#13c2c2',          // 觸發 — 青
  depends: '#722ed1',           // 依賴 — 紫
  collaborates: '#eb2f96',      // 協作 — 洋紅
  invokes: '#fa8c16',           // 呼叫 — 橙
  // Code Graph 代碼關聯
  defines_class: '#7b68ee',   // 定義類別 — 紫
  defines_function: '#6495ed', // 定義函數 — 藍
  has_method: '#1e90ff',      // 方法 — 道奇藍
  imports: '#00bfff',         // 匯入 — 淺藍
  uses_table: '#20b2aa',     // 使用表 — 青
  inherits: '#ff6347',       // 繼承 — 番茄紅
  references_table: '#3cb371', // FK 引用 — 中綠
  calls: '#ff8c00',           // 呼叫 — 暗橙
  defines_component: '#9370db', // 定義元件 — 中紫
  defines_hook: '#da70d6',     // 定義 Hook — 蘭花紫
};

export const DEFAULT_EDGE_COLOR = 'rgba(150,150,150,0.6)';

// ============================================================================
// 工具函數
// ============================================================================

export function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '...' : str;
}

export function getNodeId(node: string | ForceNode): string {
  return typeof node === 'string' ? node : node.id;
}
