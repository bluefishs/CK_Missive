/**
 * correspondenceMatching - 公文對照矩陣配對算法
 *
 * 四層配對規則：
 * 1. parent_record_id 鏈式配對（confirmed）
 * 1.5 文號交叉引用配對（confirmed）
 * 1.7 收發對調 + 主旨相似度（high）
 * 2. TF-IDF 關鍵字 + 知識圖譜實體複合相似度（high）
 * 3. 未配對公文按業務類型分類排列（low）
 *
 * Extracted from chainUtils.ts
 * @version 1.0.0
 * @date 2026-03-26
 */

import type { WorkRecord } from '../../../types/taoyuan';
import type { DispatchDocumentLink } from '../../../types/api';
import type { DocPairs, DocPair } from './chainUtils';

// ============================================================================
// Correspondence matching thresholds (SSOT)
// ============================================================================

const SIMILARITY_THRESHOLDS = {
  HIGH_CONFIDENCE: 0.25,
  FLIP_MATCH_MIN: 0.08,
  DATE_PROXIMITY_BONUS: 0.05,
} as const;

// ============================================================================
// Types
// ============================================================================

export interface MatrixDocItem {
  docId: number;
  docNumber?: string;
  docDate?: string;
  subject?: string;
  record?: WorkRecord;
  linkedDoc?: DispatchDocumentLink;
  isUnassigned: boolean;
}

export type MatchConfidence = 'confirmed' | 'high' | 'medium' | 'low';
export type DocBusinessType = 'dispatch' | 'review' | 'reply' | 'submit' | 'payment' | 'admin' | 'other';

export interface CorrespondenceMatrixRow {
  incoming?: MatrixDocItem;
  outgoing?: MatrixDocItem;
  confidence?: MatchConfidence;
  sharedEntities?: string[];
  docTypeLabel?: string;
  /** Groups rows sharing the same incoming doc (1:N pairing) */
  groupId?: number;
}

export interface EntityPairScore {
  incoming_doc_id: number;
  outgoing_doc_id: number;
  jaccard: number;
  shared_entities: string[];
}

// ============================================================================
// Internal helpers
// ============================================================================

function toMatrixItem(pair: DocPair): MatrixDocItem {
  return {
    docId: pair.doc.id,
    docNumber: pair.doc.doc_number,
    docDate: pair.doc.doc_date,
    subject: pair.record.description || pair.doc.subject,
    record: pair.record,
    isUnassigned: false,
  };
}

function linkToMatrixItem(d: DispatchDocumentLink): MatrixDocItem {
  return {
    docId: d.document_id,
    docNumber: d.doc_number,
    docDate: d.doc_date,
    subject: d.subject,
    linkedDoc: d,
    isUnassigned: true,
  };
}

const DOC_TYPE_LABELS: Record<DocBusinessType, string> = {
  dispatch: '派工通知',
  review: '審查/會議',
  reply: '函覆/回覆',
  submit: '送件/提交',
  payment: '請款/結算',
  admin: '行政事項',
  other: '其他',
};

export function classifyDocType(subject?: string): { type: DocBusinessType; label: string } {
  if (!subject) return { type: 'other', label: DOC_TYPE_LABELS.other };
  const s = subject;

  if (/派工單[號(（]?\s*\d/i.test(s)) return { type: 'dispatch', label: DOC_TYPE_LABELS.dispatch };
  if (/審查會|會議[紀記]錄|開會通知|會勘/.test(s)) return { type: 'review', label: DOC_TYPE_LABELS.review };
  if (/函[覆復]|惠復|復函|回覆/.test(s)) return { type: 'reply', label: DOC_TYPE_LABELS.reply };
  if (/請領|請款|撥付|結算|估驗|付款/.test(s)) return { type: 'payment', label: DOC_TYPE_LABELS.payment };
  if (/檢送|提送|報送|送[達審]/.test(s)) return { type: 'submit', label: DOC_TYPE_LABELS.submit };
  if (/教育訓練|契約書|保險|印鑑|投標|工作計畫|系統建置/.test(s)) return { type: 'admin', label: DOC_TYPE_LABELS.admin };
  if (/承攬|查估|測量|拆除|地上物/.test(s)) return { type: 'dispatch', label: DOC_TYPE_LABELS.dispatch };

  return { type: 'other', label: DOC_TYPE_LABELS.other };
}

// ============================================================================
// Keyword extraction & TF-IDF similarity
// ============================================================================

function extractKeywords(subject?: string): Set<string> {
  if (!subject) return new Set();

  const tokens = new Set<string>();

  const dispatchMatches = subject.matchAll(/派工單[號]?\s*[（(]?\s*(\d{2,4})\s*[）)]?/g);
  for (const m of dispatchMatches) {
    tokens.add(`派工單${m[1]}`);
  }

  const placeMatches = subject.matchAll(
    /([\u4e00-\u9fff]{2,6}(?:路|街|段|巷|弄|公園|廣場|用地))/g,
  );
  for (const m of placeMatches) {
    tokens.add(m[1]!);
  }

  const projectMatches = subject.matchAll(
    /[「『]([\u4e00-\u9fff\d（）()、\-\s]{4,30}工程)[」』]/g,
  );
  for (const m of projectMatches) {
    tokens.add(m[1]!.replace(/\s+/g, ''));
  }

  const cleaned = subject
    .replace(/[，。、；：「」（）【】『』\s]/g, '')
    .replace(/115年度桃園市興辦公共設施用地取得所需土地市價及地上物?查估[、]?測量作業[暨曁]開?瓶?資料製作委託專業服務/g, '')
    .replace(/開口契約/g, '')
    .replace(/詳如說明/g, '')
    .replace(/請查照[惠復]*/g, '');

  const CJK = /[\u4e00-\u9fff]/;
  const cjkChars = [...cleaned].filter((c) => CJK.test(c));
  for (let i = 0; i < cjkChars.length - 1; i++) {
    tokens.add(cjkChars[i]! + cjkChars[i + 1]!);
  }
  for (let i = 0; i < cjkChars.length - 2; i++) {
    tokens.add(cjkChars[i]! + cjkChars[i + 1]! + cjkChars[i + 2]!);
  }

  const numMatches = subject.matchAll(/\d{5,}/g);
  for (const m of numMatches) {
    tokens.add(m[0]!);
  }

  const stopwords = new Set([
    '有關', '關於', '檢送', '檢附', '敬請', '本局', '貴公司',
    '本公司', '本市', '一案', '乙式', '備查', '說明', '承攬',
  ]);
  for (const t of tokens) {
    if (t.length < 2 || stopwords.has(t)) {
      tokens.delete(t);
    }
  }

  return tokens;
}

function keywordSimilarity(
  a: Set<string>,
  b: Set<string>,
  idfWeights?: Map<string, number>,
): number {
  if (a.size === 0 || b.size === 0) return 0;

  if (!idfWeights) {
    let intersection = 0;
    for (const w of a) {
      if (b.has(w)) intersection++;
    }
    const union = a.size + b.size - intersection;
    return union > 0 ? intersection / union : 0;
  }

  const allWords = new Set([...a, ...b]);
  let interWeight = 0;
  let unionWeight = 0;
  for (const w of allWords) {
    const weight = idfWeights.get(w) ?? 1;
    unionWeight += weight;
    if (a.has(w) && b.has(w)) {
      interWeight += weight;
    }
  }
  return unionWeight > 0 ? interWeight / unionWeight : 0;
}

function buildIdfWeights(allKeywordSets: Set<string>[]): Map<string, number> {
  const docFreq = new Map<string, number>();
  const N = allKeywordSets.length;
  for (const kws of allKeywordSets) {
    for (const w of kws) {
      docFreq.set(w, (docFreq.get(w) ?? 0) + 1);
    }
  }
  const idf = new Map<string, number>();
  for (const [word, df] of docFreq) {
    idf.set(word, Math.log((N + 1) / (df + 1)) + 1);
  }
  return idf;
}

// ============================================================================
// Main: buildCorrespondenceMatrix
// ============================================================================

export function buildCorrespondenceMatrix(
  assignedPairs: DocPairs,
  unassignedIncoming: DispatchDocumentLink[],
  unassignedOutgoing: DispatchDocumentLink[],
  entityScores?: EntityPairScore[],
): CorrespondenceMatrixRow[] {
  const rows: CorrespondenceMatrixRow[] = [];
  const usedInRecordIds = new Set<number>();
  const usedOutRecordIds = new Set<number>();

  // --- Phase 1: parent_record_id 鏈式配對 (supports 1:N) ---
  // Track which incomings have been paired at least once (allow reuse for 1:N)
  const pairedIncomingIds = new Set<number>();

  for (const outPair of assignedPairs.outgoingDocs) {
    if (!outPair.record.parent_record_id) continue;
    if (usedOutRecordIds.has(outPair.record.id)) continue;

    const matchIn = assignedPairs.incomingDocs.find(
      (ip) => ip.record.id === outPair.record.parent_record_id,
    );
    if (matchIn) {
      const groupId = matchIn.record.id; // Group by incoming record ID
      rows.push({
        incoming: pairedIncomingIds.has(groupId) ? undefined : toMatrixItem(matchIn),
        outgoing: toMatrixItem(outPair),
        confidence: 'confirmed',
        groupId,
      });
      pairedIncomingIds.add(groupId);
      usedOutRecordIds.add(outPair.record.id);
    }
  }

  // Mark all paired incomings as used AFTER processing all outgoings
  for (const id of pairedIncomingIds) {
    usedInRecordIds.add(id);
  }

  // --- 收集剩餘項目 ---
  const remainIn = assignedPairs.incomingDocs
    .filter((p) => !usedInRecordIds.has(p.record.id))
    .map(toMatrixItem)
    .sort((a, b) => (a.docDate || '').localeCompare(b.docDate || ''));

  const remainOut = assignedPairs.outgoingDocs
    .filter((p) => !usedOutRecordIds.has(p.record.id))
    .map(toMatrixItem)
    .sort((a, b) => (a.docDate || '').localeCompare(b.docDate || ''));

  const allUnpairedIn = [
    ...remainIn,
    ...unassignedIncoming.map(linkToMatrixItem),
  ].sort((a, b) => (a.docDate || '').localeCompare(b.docDate || ''));

  const allUnpairedOut = [
    ...remainOut,
    ...unassignedOutgoing.map(linkToMatrixItem),
  ].sort((a, b) => (a.docDate || '').localeCompare(b.docDate || ''));

  // === Phase 1.5: 文號交叉引用配對 (supports 1:N) ===
  const usedInIdx15 = new Set<number>();
  const usedOutIdx15 = new Set<number>();
  const pairedInIdx15 = new Set<number>(); // Track first-paired incomings for grouping

  for (let i = 0; i < allUnpairedIn.length; i++) {
    const inItem = allUnpairedIn[i]!;
    const inDocNum = inItem.docNumber || '';
    const inSubject = inItem.subject || '';
    if (!inDocNum && !inSubject) continue;

    for (let j = 0; j < allUnpairedOut.length; j++) {
      if (usedOutIdx15.has(j)) continue;
      const outItem = allUnpairedOut[j]!;
      const outDocNum = outItem.docNumber || '';
      const outSubject = outItem.subject || '';

      const outRefersIn = inDocNum.length > 4 && outSubject.includes(inDocNum);
      const inRefersOut = outDocNum.length > 4 && inSubject.includes(outDocNum);

      if (outRefersIn || inRefersOut) {
        const groupId = inItem.docId; // Group by incoming doc ID
        rows.push({
          incoming: pairedInIdx15.has(i) ? undefined : inItem,
          outgoing: outItem,
          confidence: 'confirmed',
          sharedEntities: [outRefersIn ? `引用文號:${inDocNum}` : `引用文號:${outDocNum}`],
          groupId,
        });
        pairedInIdx15.add(i);
        usedOutIdx15.add(j);
        // DON'T break — continue scanning for more outgoings referencing this incoming
      }
    }

    // Mark incoming as used if it was paired at least once
    if (pairedInIdx15.has(i)) {
      usedInIdx15.add(i);
    }
  }

  // === Phase 1.7: 收發對調 + 主旨相似度配對 ===
  const flipInKeywords = allUnpairedIn.map((item) => extractKeywords(item.subject));
  const flipOutKeywords = allUnpairedOut.map((item) => extractKeywords(item.subject));

  for (let i = 0; i < allUnpairedIn.length; i++) {
    if (usedInIdx15.has(i)) continue;
    const inItem = allUnpairedIn[i]!;
    const inLink = inItem.linkedDoc;
    if (!inLink) continue;
    const inSender = (inLink.sender || '').trim();
    const inReceiver = (inLink.receiver || '').trim();
    if (!inSender || !inReceiver || inSender.length < 2 || inReceiver.length < 2) continue;

    let bestIdx = -1;
    let bestScore = 0;

    for (let j = 0; j < allUnpairedOut.length; j++) {
      if (usedOutIdx15.has(j)) continue;
      const outItem = allUnpairedOut[j]!;
      const outLink = outItem.linkedDoc;
      if (!outLink) continue;
      const outSender = (outLink.sender || '').trim();
      const outReceiver = (outLink.receiver || '').trim();

      const flipMatch =
        (inSender.includes(outReceiver) || outReceiver.includes(inSender)) &&
        (inReceiver.includes(outSender) || outSender.includes(inReceiver));

      if (!flipMatch) continue;

      const kwSim = keywordSimilarity(flipInKeywords[i]!, flipOutKeywords[j]!);
      if (kwSim < SIMILARITY_THRESHOLDS.FLIP_MATCH_MIN) continue;

      const inTime = inItem.docDate ? new Date(inItem.docDate).getTime() : 0;
      const outTime = outItem.docDate ? new Date(outItem.docDate).getTime() : 0;
      const dayGap = inTime && outTime ? (outTime - inTime) / (24 * 60 * 60 * 1000) : 999;
      if (dayGap < 0 || dayGap > 60) continue;

      const dateBonus = dayGap <= 14 ? 0.1 * (1 - dayGap / 14) : 0;
      const score = kwSim + dateBonus;

      if (score > bestScore) {
        bestScore = score;
        bestIdx = j;
      }
    }

    if (bestIdx >= 0) {
      rows.push({
        incoming: inItem,
        outgoing: allUnpairedOut[bestIdx],
        confidence: 'high',
        sharedEntities: [`收發對調+主旨相似(${bestScore.toFixed(2)})`],
      });
      usedInIdx15.add(i);
      usedOutIdx15.add(bestIdx);
    }
  }

  // --- Phase 2: TF-IDF + Entity 複合相似度 ---
  const inKeywords = allUnpairedIn.map((item) => extractKeywords(item.subject));
  const outKeywords = allUnpairedOut.map((item) => extractKeywords(item.subject));

  const allKeywordSets = [...inKeywords, ...outKeywords];
  const idfWeights = allKeywordSets.length >= 6
    ? buildIdfWeights(allKeywordSets)
    : undefined;

  const entityScoreMap = new Map<string, { jaccard: number; entities: string[] }>();
  if (entityScores) {
    for (const es of entityScores) {
      entityScoreMap.set(
        `${es.incoming_doc_id}-${es.outgoing_doc_id}`,
        { jaccard: es.jaccard, entities: es.shared_entities },
      );
    }
  }

  const totalPossiblePairs = allUnpairedIn.length * allUnpairedOut.length;
  const entityCoverage = totalPossiblePairs > 0
    ? entityScoreMap.size / totalPossiblePairs
    : 0;
  const effectiveEntityWeight = entityCoverage > 0.8
    ? 0.5 + 0.1 * Math.min((entityCoverage - 0.8) / 0.2, 1)
    : 0.4;
  const effectiveKeywordWeight = 1 - effectiveEntityWeight;

  const usedOutIdx = new Set<number>(usedOutIdx15);
  const SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLDS.HIGH_CONFIDENCE;
  const DATE_PROXIMITY_BONUS = SIMILARITY_THRESHOLDS.DATE_PROXIMITY_BONUS;
  const pendingInIndices: number[] = [];

  for (let i = 0; i < allUnpairedIn.length; i++) {
    if (usedInIdx15.has(i)) continue;
    const inItem = allUnpairedIn[i]!;
    const inKw = inKeywords[i]!;
    const inDate = inItem.docDate || '';
    const inTime = inDate ? new Date(inDate).getTime() : 0;

    let bestIdx = -1;
    let bestScore = 0;
    let bestEntities: string[] | undefined;

    for (let j = 0; j < allUnpairedOut.length; j++) {
      if (usedOutIdx.has(j)) continue;
      const outDate = allUnpairedOut[j]!.docDate || '';
      if (outDate < inDate) continue;

      const kwSim = keywordSimilarity(inKw, outKeywords[j]!, idfWeights);

      const inDocId = inItem.docId;
      const outDocId = allUnpairedOut[j]!.docId;
      const entityMatch = (inDocId && outDocId)
        ? entityScoreMap.get(`${inDocId}-${outDocId}`)
        : undefined;
      const entitySim = entityMatch?.jaccard ?? 0;

      let combinedScore = entitySim > 0
        ? kwSim * effectiveKeywordWeight + entitySim * effectiveEntityWeight
        : kwSim;

      if (inTime > 0) {
        const outTime = outDate ? new Date(outDate).getTime() : 0;
        const dayGap = (outTime - inTime) / (24 * 60 * 60 * 1000);
        if (dayGap >= 0 && dayGap <= 7) {
          combinedScore += DATE_PROXIMITY_BONUS * (1 - dayGap / 7);
        }
      }

      if (combinedScore >= SIMILARITY_THRESHOLD && combinedScore > bestScore) {
        bestScore = combinedScore;
        bestIdx = j;
        bestEntities = entityMatch?.entities;
      }
    }

    if (bestIdx >= 0) {
      rows.push({
        incoming: inItem,
        outgoing: allUnpairedOut[bestIdx],
        confidence: 'high',
        sharedEntities: bestEntities,
      });
      usedOutIdx.add(bestIdx);
    } else {
      pendingInIndices.push(i);
    }
  }

  // --- Phase 3: 未配對公文按業務類型分類 ---
  for (const i of pendingInIndices) {
    if (usedInIdx15.has(i)) continue;
    const item = allUnpairedIn[i]!;
    const { label } = classifyDocType(item.subject);
    rows.push({ incoming: item, outgoing: undefined, confidence: 'low', docTypeLabel: label });
  }

  for (let j = 0; j < allUnpairedOut.length; j++) {
    if (!usedOutIdx.has(j)) {
      const item = allUnpairedOut[j]!;
      const { label } = classifyDocType(item.subject);
      rows.push({ incoming: undefined, outgoing: item, confidence: 'low', docTypeLabel: label });
    }
  }

  // --- 排序 (preserving group contiguity) ---
  const confidenceOrder: Record<string, number> = { confirmed: 0, high: 1, medium: 2, low: 3 };

  // First, collect group header positions so grouped rows stay together
  const groupHeaderIdx = new Map<number, number>();
  rows.forEach((row, idx) => {
    if (row.groupId !== undefined && !groupHeaderIdx.has(row.groupId)) {
      groupHeaderIdx.set(row.groupId, idx);
    }
  });

  rows.sort((a, b) => {
    // If both belong to the same group, keep header first then preserve insertion order
    if (a.groupId !== undefined && a.groupId === b.groupId) {
      // Header (has incoming) comes first
      if (a.incoming && !b.incoming) return -1;
      if (!a.incoming && b.incoming) return 1;
      return 0;
    }

    // For sorting across groups, use the group header's confidence/date
    const ca = confidenceOrder[a.confidence || 'low'] ?? 3;
    const cb = confidenceOrder[b.confidence || 'low'] ?? 3;
    if (ca !== cb) return ca - cb;
    if (a.docTypeLabel !== b.docTypeLabel) {
      return (a.docTypeLabel || 'zzz').localeCompare(b.docTypeLabel || 'zzz');
    }
    const dateA = a.incoming?.docDate || a.outgoing?.docDate || '';
    const dateB = b.incoming?.docDate || b.outgoing?.docDate || '';
    return dateA.localeCompare(dateB);
  });

  return rows;
}
