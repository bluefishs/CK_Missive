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
  // --- 業務實體（來自系統資料庫的結構化記錄） ---
  document:  { color: '#1890ff', radius: 6, label: '公文',       detailable: false, description: '系統中的收發文公文記錄（DB）' },
  project:   { color: '#52c41a', radius: 9, label: '承攬案件',   detailable: false, description: '承攬的合約工程專案（DB）' },
  agency:    { color: '#fa8c16', radius: 5, label: '機關',       detailable: false, description: '公文往來的政府機關（含 AI 提取）' },
  dispatch:  { color: '#722ed1', radius: 7, label: '派工單',     detailable: false, description: '桃園市政府的派工通知單（DB）' },
  typroject: { color: '#2f54eb', radius: 7, label: '查估工程',   detailable: false, description: '桃園派工系統的工程案件（含 AI 提取）' },
  // --- Code Graph 代碼實體 ---
  py_module:   { color: '#7b68ee', radius: 5, label: 'Python 模組', detailable: true, description: '程式碼模組（.py 檔案）' },
  py_class:    { color: '#6495ed', radius: 5, label: 'Python 類別', detailable: true, description: '程式碼中的類別定義' },
  py_function: { color: '#1e90ff', radius: 4, label: 'Python 函數', detailable: true, description: '程式碼中的函數/方法定義' },
  db_table:    { color: '#00bfff', radius: 5, label: '資料表',      detailable: true, description: 'PostgreSQL 資料庫表格' },
  // --- TypeScript/React 代碼實體 ---
  ts_module:     { color: '#9370db', radius: 5, label: 'TS 模組',     detailable: true, description: 'TypeScript/React 模組（.ts/.tsx 檔案）' },
  ts_component:  { color: '#da70d6', radius: 5, label: 'React 元件',  detailable: true, description: 'React 元件定義' },
  ts_hook:       { color: '#ba55d3', radius: 4, label: 'React Hook',  detailable: true, description: 'React 自訂 Hook（useXxx）' },
  // --- 模組總覽實體 ---
  menu_module: { color: '#f5222d', radius: 10, label: '功能模組',  detailable: false, description: '網站選單對應的功能模組' },
  api_group:   { color: '#52c41a', radius: 5,  label: 'API 群組',  detailable: false, description: 'API 端點群組' },
  // --- Skills Capability Map 節點 (v2.0 — 3 層階層式) ---
  layer:      { color: '#434343', radius: 14, label: '能力分層', detailable: false, description: '能力圖譜的架構分層 (感知/認知/知識/行動/學習)' },
  capability: { color: '#1890ff', radius: 10, label: '核心能力', detailable: false, description: '核心能力節點，大小反映成熟度 (★1-5)' },
  future:     { color: '#ff85c0', radius: 7,  label: '演進方向', detailable: false, description: '未來發展方向與目標能力' },
  // Legacy skill map types (backward compat)
  domain:    { color: '#f5222d', radius: 12, label: '領域',     detailable: false, description: 'Skills 能力圖譜中的領域分類' },
  skill:     { color: '#52c41a', radius: 7,  label: '技能',     detailable: false, description: '具體實現的技能模組' },
  agent:     { color: '#52c41a', radius: 6,  label: 'Agent',    detailable: false, description: 'Claude Code 專業代理' },
  tool:      { color: '#faad14', radius: 5,  label: '工具',     detailable: false, description: 'Agent 可呼叫的工具函數' },
  service:   { color: '#722ed1', radius: 6,  label: '服務',     detailable: false, description: '後端 AI 服務模組' },
  command:   { color: '#13c2c2', radius: 5,  label: '指令',     detailable: false, description: 'Claude Code Slash Command' },
  // --- NER 提取實體（AI 從公文文字自動識別） ---
  person:      { color: '#f5222d', radius: 5, label: '人物',       detailable: true,  description: 'AI 從公文內容提取的人名' },
  location:    { color: '#faad14', radius: 4, label: '行政區',     detailable: true,  description: '聚合後的行政區域（區/鄉/鎮）' },
  date:        { color: '#13c2c2', radius: 4, label: '日期',       detailable: true,  description: 'AI 從公文內容提取的重要日期（預設隱藏）' },
  topic:       { color: '#eb2f96', radius: 5, label: '主題',       detailable: true,  description: 'AI 從公文內容提取的主題/關鍵字（預設隱藏）' },
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

/** 預設隱藏的節點類型（使用者可在設定面板開啟） */
export const DEFAULT_HIDDEN_TYPES = new Set(['date', 'topic']);

/** 公文/派工等文件類型（實體關係模式下隱藏） */
export const DOCUMENT_NODE_TYPES = new Set(['document', 'dispatch']);

/** Code Graph 代碼實體類型（用於 EntityDetailSidebar 等判斷） */
export const CODE_ENTITY_TYPES = new Set([
  'py_module', 'py_class', 'py_function', 'db_table',
  'ts_module', 'ts_component', 'ts_hook',
]);

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
  radius?: number;
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

  const defaultVisible = !DEFAULT_HIDDEN_TYPES.has(type);

  if (!ov) {
    return { ...base, visible: defaultVisible };
  }

  return {
    color: ov.color ?? base.color,
    radius: ov.radius ?? base.radius,
    label: ov.label ?? base.label,
    detailable: base.detailable,
    description: ov.description ?? base.description,
    visible: ov.visible ?? defaultVisible,
  };
}

/** 取得所有類型的合併配置（只讀一次 localStorage） */
export function getAllMergedConfigs(
  baseConfig: Record<string, GraphNodeTypeConfig> = GRAPH_NODE_CONFIG,
): Record<string, MergedNodeConfig> {
  const overrides = getUserOverrides();
  const result: Record<string, MergedNodeConfig> = {};
  for (const [type, base] of Object.entries(baseConfig)) {
    const ov = overrides[type];
    const defaultVisible = !DEFAULT_HIDDEN_TYPES.has(type);
    result[type] = ov
      ? {
          color: ov.color ?? base.color,
          radius: ov.radius ?? base.radius,
          label: ov.label ?? base.label,
          detailable: base.detailable,
          description: ov.description ?? base.description,
          visible: ov.visible ?? defaultVisible,
        }
      : { ...base, visible: defaultVisible };
  }
  return result;
}

// ============================================================================
// 工廠函數（模組化移植用）
// ============================================================================

/**
 * 建立一組節點配置工具函數。
 * 移植到其他專案時，只需傳入該專案的節點類型定義即可。
 *
 * @example
 * const myConfig = createNodeConfigSet({
 *   table: { color: '#1890ff', radius: 6, label: '資料表', detailable: true, description: '...' },
 * });
 * <KnowledgeGraph nodeConfig={myConfig.config} ... />
 */
export function createNodeConfigSet(types: Record<string, GraphNodeTypeConfig>) {
  const config = types;

  const get = (type: string): GraphNodeTypeConfig =>
    config[type] ?? DEFAULT_NODE_CONFIG;

  const knownTypes = Object.keys(config);

  const detailableTypes = new Set(
    Object.entries(config)
      .filter(([, cfg]) => cfg.detailable)
      .map(([t]) => t),
  );

  const getMerged = () => getAllMergedConfigs(config);

  return { config, getNodeConfig: get, knownTypes, detailableTypes, getAllMergedConfigs: getMerged };
}
