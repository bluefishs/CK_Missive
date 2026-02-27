/**
 * KnowledgeGraph 內部型別與常數
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

// ============================================================================
// Force-Graph 內部型別
// ============================================================================

export interface ForceNode {
  id: string;
  label: string;
  type: string;
  color: string;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
  mention_count?: number;
  x?: number;
  y?: number;
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
  manages: '#d48806',         // 管理 — 暗金
  located_in: '#faad14',      // 位於 — 金
  related_to: '#8c8c8c',      // 相關 — 灰
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
