/**
 * chainUtils - 鏈式時間軸工具函數
 *
 * buildChains: 將 flat records 轉為鏈式樹結構
 * getEffectiveDocId: 取得有效公文 ID（新/舊格式相容）
 * getEffectiveDoc: 取得有效公文摘要
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import type { WorkRecord, DocBrief } from '../../../types/taoyuan';

// ============================================================================
// Types
// ============================================================================

export interface ChainNode {
  record: WorkRecord;
  children: ChainNode[];
  depth: number;
}

// ============================================================================
// buildChains
// ============================================================================

/**
 * 將 flat records 轉為鏈式樹結構
 *
 * 邏輯:
 * - 有 parent_record_id → 掛到 parent 下
 * - 無 parent_record_id → root node
 * - 舊紀錄（無 parent_record_id）→ 獨立 root
 * - 按 sort_order / record_date 排序
 */
export function buildChains(records: WorkRecord[]): ChainNode[] {
  if (records.length === 0) return [];

  // 先按排序
  const sorted = [...records].sort((a, b) => {
    if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
    const dateA = a.record_date || '';
    const dateB = b.record_date || '';
    return dateA.localeCompare(dateB);
  });

  // 建立 id → node 映射
  const nodeMap = new Map<number, ChainNode>();
  for (const r of sorted) {
    nodeMap.set(r.id, { record: r, children: [], depth: 0 });
  }

  const roots: ChainNode[] = [];

  for (const r of sorted) {
    const node = nodeMap.get(r.id)!;
    if (r.parent_record_id && nodeMap.has(r.parent_record_id)) {
      const parent = nodeMap.get(r.parent_record_id)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      // root（無 parent 或 parent 不在當前列表中）
      roots.push(node);
    }
  }

  return roots;
}

/**
 * 將鏈式樹結構攤平為有序陣列（深度優先）
 */
export function flattenChains(roots: ChainNode[]): ChainNode[] {
  const result: ChainNode[] = [];

  function walk(node: ChainNode) {
    result.push(node);
    for (const child of node.children) {
      walk(child);
    }
  }

  for (const root of roots) {
    walk(root);
  }

  return result;
}

// ============================================================================
// 公文方向判定（Single Source of Truth）
// ============================================================================

/**
 * 判斷公文字號是否為公司發文（「乾坤」開頭）
 *
 * 這是所有公文方向判定的唯一來源。
 * 其他位置的 detectLinkType / getDocDirection 都應使用此函數。
 */
export function isOutgoingDocNumber(docNumber?: string | null): boolean {
  return !!docNumber && docNumber.startsWith('乾坤');
}

// ============================================================================
// 相容工具
// ============================================================================

/** 取得紀錄的有效公文 ID（新格式 document_id 優先，舊格式 fallback） */
export function getEffectiveDocId(record: WorkRecord): number | undefined {
  if (record.document_id) return record.document_id;
  return record.incoming_doc_id || record.outgoing_doc_id || undefined;
}

/** 取得紀錄的有效公文摘要（新格式 document 優先，舊格式 fallback） */
export function getEffectiveDoc(record: WorkRecord): DocBrief | undefined {
  if (record.document) return record.document;
  return record.incoming_doc || record.outgoing_doc || undefined;
}

// ============================================================================
// 公文分組（共用邏輯，useDispatchWorkData + useProjectWorkData 統一使用）
// ============================================================================

export interface DocPair {
  record: WorkRecord;
  doc: DocBrief;
}

export interface DocPairs {
  incomingDocs: DocPair[];
  outgoingDocs: DocPair[];
}

/**
 * 將 WorkRecord[] 分組為來文/發文配對
 *
 * 支援新舊格式：
 * - 舊格式：incoming_doc / outgoing_doc
 * - 新格式：document + isOutgoingDocNumber 判斷
 */
export function buildDocPairs(records: WorkRecord[]): DocPairs {
  const incomingDocs: DocPair[] = [];
  const outgoingDocs: DocPair[] = [];

  for (const r of records) {
    // 舊格式
    if (r.incoming_doc) {
      incomingDocs.push({ record: r, doc: r.incoming_doc });
    }
    if (r.outgoing_doc) {
      outgoingDocs.push({ record: r, doc: r.outgoing_doc });
    }
    // 新格式（document_id + document，且無舊格式欄位時）
    if (r.document && !r.incoming_doc_id && !r.outgoing_doc_id) {
      if (isOutgoingDocNumber(r.document.doc_number)) {
        outgoingDocs.push({ record: r, doc: r.document });
      } else {
        incomingDocs.push({ record: r, doc: r.document });
      }
    }
  }

  return { incomingDocs, outgoingDocs };
}

/** 判斷公文方向：來文或發文 */
export function getDocDirection(record: WorkRecord): 'incoming' | 'outgoing' | null {
  const doc = getEffectiveDoc(record);
  if (!doc) return null;

  // 新格式：由 doc_number 判斷
  if (record.document_id && doc.doc_number) {
    return isOutgoingDocNumber(doc.doc_number) ? 'outgoing' : 'incoming';
  }

  // 舊格式：由欄位判斷
  if (record.incoming_doc_id) return 'incoming';
  if (record.outgoing_doc_id) return 'outgoing';

  return null;
}
