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
import { getCategoryLabel } from './workCategoryConstants';

// Re-export correspondence matching from dedicated module
export {
  buildCorrespondenceMatrix,
  classifyDocType,
} from './correspondenceMatching';
export type {
  MatrixDocItem,
  CorrespondenceMatrixRow,
  EntityPairScore,
  MatchConfidence,
  DocBusinessType,
} from './correspondenceMatching';

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
    let handled = false;

    // 舊格式：有展開的 incoming_doc/outgoing_doc 物件
    if (r.incoming_doc) {
      incomingDocs.push({ record: r, doc: r.incoming_doc });
      handled = true;
    }
    if (r.outgoing_doc) {
      outgoingDocs.push({ record: r, doc: r.outgoing_doc });
      handled = true;
    }

    // 新格式（document 欄位），且舊格式物件不存在時
    if (!handled && r.document) {
      if (isOutgoingDocNumber(r.document.doc_number)) {
        outgoingDocs.push({ record: r, doc: r.document });
      } else {
        incomingDocs.push({ record: r, doc: r.document });
      }
      handled = true;
    }

    // 回退：有 document_id 但展開物件缺失（JOIN 不完整）
    // 建構最小 DocBrief 讓紀錄不被遺漏
    if (!handled && (r.document_id || r.incoming_doc_id || r.outgoing_doc_id)) {
      const fallbackDoc: DocBrief = {
        id: r.document_id || r.incoming_doc_id || r.outgoing_doc_id || 0,
        doc_number: r.description?.match(/[\u4e00-\u9fff]+字第\d+號/)?.[0] || `(doc#${r.document_id || r.incoming_doc_id || r.outgoing_doc_id})`,
        subject: r.description || '',
        doc_date: r.record_date || '',
      };
      if (r.outgoing_doc_id) {
        outgoingDocs.push({ record: r, doc: fallbackDoc });
      } else {
        incomingDocs.push({ record: r, doc: fallbackDoc });
      }
    }
  }

  return { incomingDocs, outgoingDocs };
}


// ============================================================================
// 共用篩選/統計函數（Rec-1, Rec-3: useDispatchWorkData + useProjectWorkData 統一使用）
// ============================================================================

/**
 * 過濾空白紀錄（無公文 + 無描述），但保留被引用為 parent 的紀錄
 *
 * 從 useDispatchWorkData / useProjectWorkData 提取的共用邏輯
 */
export function filterBlankRecords(allRecords: WorkRecord[]): WorkRecord[] {
  const parentIds = new Set(
    allRecords
      .map((r) => r.parent_record_id)
      .filter((id): id is number => !!id),
  );
  return allRecords.filter(
    (r) =>
      r.document_id ||
      r.incoming_doc_id ||
      r.outgoing_doc_id ||
      r.description ||
      parentIds.has(r.id),
  );
}

/**
 * 計算來文/發文不重複數
 *
 * 統一新舊格式相容邏輯，避免兩個 hook 各自實作
 */
export function computeDocStats(records: WorkRecord[]): {
  incomingDocs: number;
  outgoingDocs: number;
} {
  const incomingIds = new Set<number>();
  const outgoingIds = new Set<number>();
  for (const r of records) {
    if (r.incoming_doc_id) incomingIds.add(r.incoming_doc_id);
    if (r.outgoing_doc_id) outgoingIds.add(r.outgoing_doc_id);
    if (r.document_id) {
      if (isOutgoingDocNumber(r.document?.doc_number)) {
        outgoingIds.add(r.document_id);
      } else {
        incomingIds.add(r.document_id);
      }
    }
  }
  return { incomingDocs: incomingIds.size, outgoingDocs: outgoingIds.size };
}

/**
 * 計算當前作業階段
 *
 * 從最後一筆非完成紀錄取得類別標籤，全部完成則回傳 '全部完成'
 */
export function computeCurrentStage(records: WorkRecord[]): string {
  const total = records.length;
  const completed = records.filter((r) => r.status === 'completed').length;

  if (total > 0 && completed === total) return '全部完成';

  for (let i = records.length - 1; i >= 0; i--) {
    const rec = records[i];
    if (rec && rec.status !== 'completed') {
      return getCategoryLabel(rec);
    }
  }

  return '尚未開始';
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
