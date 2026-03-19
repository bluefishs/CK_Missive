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
import type { DispatchDocumentLink } from '../../../types/api';
import { getCategoryLabel } from './workCategoryConstants';

// ============================================================================
// Correspondence matching thresholds (SSOT)
// ============================================================================

/** Unified similarity thresholds for correspondence matching phases */
const SIMILARITY_THRESHOLDS = {
  /** Phase 2: TF-IDF + entity composite score minimum */
  HIGH_CONFIDENCE: 0.25,
  /** Phase 1.7: Sender/receiver flip minimum keyword overlap */
  FLIP_MATCH_MIN: 0.08,
  /** Phase 2: Date proximity bonus (within 7 days) */
  DATE_PROXIMITY_BONUS: 0.05,
} as const;

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

// ============================================================================
// 公文對照矩陣（配對行式 SSOT）
// ============================================================================

/** 矩陣中的單筆公文項目 */
export interface MatrixDocItem {
  docId: number;
  docNumber?: string;
  docDate?: string;
  subject?: string;
  /** 來自作業紀錄（已指派） */
  record?: WorkRecord;
  /** 來自關聯公文（未指派） */
  linkedDoc?: DispatchDocumentLink;
  /** 是否為未指派公文 */
  isUnassigned: boolean;
}

/** 將 DocPair 轉為 MatrixDocItem */
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

/** 將 DispatchDocumentLink 轉為 MatrixDocItem */
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

// ============================================================================
// 主旨關鍵字相似度（用於配對加權）
// ============================================================================

/** 從公文主旨提取有意義的關鍵字（去除常見停用詞） */
function extractKeywords(subject?: string): Set<string> {
  if (!subject) return new Set();

  const tokens = new Set<string>();

  // 1. 提取派工單號（最強辨識信號，如 "派工單003", "派工單號004"）
  const dispatchMatches = subject.matchAll(/派工單[號]?\s*[（(]?\s*(\d{2,4})\s*[）)]?/g);
  for (const m of dispatchMatches) {
    tokens.add(`派工單${m[1]}`); // e.g. "派工單003"
  }

  // 2. 提取具名地點（中文地名 + 路/街/段/巷/弄/公園/工程）
  const placeMatches = subject.matchAll(
    /([\u4e00-\u9fff]{2,6}(?:路|街|段|巷|弄|公園|廣場|用地))/g,
  );
  for (const m of placeMatches) {
    tokens.add(m[1]!);
  }

  // 3. 提取工程名稱片段（「...工程」引號內的工程名）
  const projectMatches = subject.matchAll(
    /[「『]([\u4e00-\u9fff\d（）()、\-\s]{4,30}工程)[」』]/g,
  );
  for (const m of projectMatches) {
    tokens.add(m[1]!.replace(/\s+/g, ''));
  }

  // 4. 提取關鍵業務詞（2-4 字中文片段，N-gram 策略）
  const cleaned = subject
    .replace(/[，。、；：「」（）【】『』\s]/g, '')
    .replace(/115年度桃園市興辦公共設施用地取得所需土地市價及地上物?查估[、]?測量作業[暨曁]開?瓶?資料製作委託專業服務/g, '')
    .replace(/開口契約/g, '')
    .replace(/詳如說明/g, '')
    .replace(/請查照[惠復]*/g, '');

  // 業務關鍵詞提取（中文 bigram + trigram）
  const CJK = /[\u4e00-\u9fff]/;
  const cjkChars = [...cleaned].filter((c) => CJK.test(c));
  // Bigrams (2字)
  for (let i = 0; i < cjkChars.length - 1; i++) {
    const bigram = cjkChars[i]! + cjkChars[i + 1]!;
    tokens.add(bigram);
  }
  // Trigrams (3字) — 提供更好的語意單位
  for (let i = 0; i < cjkChars.length - 2; i++) {
    const trigram = cjkChars[i]! + cjkChars[i + 1]! + cjkChars[i + 2]!;
    tokens.add(trigram);
  }

  // 5. 保留數字序號（如文號中的 "1150000004"）
  const numMatches = subject.matchAll(/\d{5,}/g);
  for (const m of numMatches) {
    tokens.add(m[0]!);
  }

  // 移除過短或停用詞
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

/**
 * 計算 TF-IDF 加權的關鍵字相似度 (0~1)
 *
 * 當所有公文來自同一工程時，共用詞（如「道路養護」）不具鑑別力。
 * IDF 會自動降低高頻詞的權重，提升獨特詞的匹配信號。
 *
 * @param a 來文關鍵字集合
 * @param b 發文關鍵字集合
 * @param idfWeights 全文檔 IDF 權重表（可選，無則 fallback 為 Jaccard）
 */
function keywordSimilarity(
  a: Set<string>,
  b: Set<string>,
  idfWeights?: Map<string, number>,
): number {
  if (a.size === 0 || b.size === 0) return 0;

  // 無 IDF 權重時退化為普通 Jaccard
  if (!idfWeights) {
    let intersection = 0;
    for (const w of a) {
      if (b.has(w)) intersection++;
    }
    const union = a.size + b.size - intersection;
    return union > 0 ? intersection / union : 0;
  }

  // TF-IDF 加權 Jaccard：共有詞的 IDF 權重和 / 聯集詞的 IDF 權重和
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

/**
 * 建立 IDF 權重表：log(N / df)，df = 包含該詞的文檔數
 *
 * 高頻詞（出現在多數文檔）→ 低 IDF → 低權重
 * 稀有詞（只出現在少數文檔）→ 高 IDF → 高權重
 */
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
    // +1 避免 log(1)=0 的退化
    idf.set(word, Math.log((N + 1) / (df + 1)) + 1);
  }
  return idf;
}

/** 配對信心度等級 */
export type MatchConfidence = 'confirmed' | 'high' | 'medium' | 'low';

/** 公文業務類型 (用於分組顯示未配對公文) */
export type DocBusinessType = 'dispatch' | 'review' | 'reply' | 'submit' | 'payment' | 'admin' | 'other';

const DOC_TYPE_LABELS: Record<DocBusinessType, string> = {
  dispatch: '派工通知',
  review: '審查/會議',
  reply: '函覆/回覆',
  submit: '送件/提交',
  payment: '請款/結算',
  admin: '行政事項',
  other: '其他',
};

/** 從公文主旨分類業務類型 */
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

/** 帶信心度的矩陣行 */
export interface CorrespondenceMatrixRow {
  incoming?: MatrixDocItem;
  outgoing?: MatrixDocItem;
  /** 配對信心度 */
  confidence?: MatchConfidence;
  /** 共享知識圖譜實體名稱（僅 entity 配對時） */
  sharedEntities?: string[];
  /** 公文業務類型標籤（未配對時顯示分類） */
  docTypeLabel?: string;
}

/** 知識圖譜實體配對分數（來自 API） */
export interface EntityPairScore {
  incoming_doc_id: number;
  outgoing_doc_id: number;
  jaccard: number;
  shared_entities: string[];
}

/**
 * 將來文/發文建構為公文對照矩陣（配對行式）
 *
 * 四層配對規則（優先順序）：
 * 1. parent_record_id 鏈式配對（已確認） → confidence: 'confirmed'
 * 2. 主旨關鍵字相似度 + 知識圖譜實體相似度 ≥ 0.3 → confidence: 'high'
 * 3. 日期鄰近配對（30 天內） → confidence: 'medium'
 * 4. 剩餘未配對的單獨成行 → confidence: 'low'
 *
 * @param entityScores 可選的知識圖譜實體配對分數，用於 Phase 2 加權
 *
 * 全部結果依日期排序（舊→新）。
 */
export function buildCorrespondenceMatrix(
  assignedPairs: DocPairs,
  unassignedIncoming: DispatchDocumentLink[],
  unassignedOutgoing: DispatchDocumentLink[],
  entityScores?: EntityPairScore[],
): CorrespondenceMatrixRow[] {
  const rows: CorrespondenceMatrixRow[] = [];
  const usedInRecordIds = new Set<number>();
  const usedOutRecordIds = new Set<number>();

  // --- Phase 1: parent_record_id 鏈式配對（最高信心度） ---
  for (const outPair of assignedPairs.outgoingDocs) {
    if (!outPair.record.parent_record_id) continue;
    const matchIn = assignedPairs.incomingDocs.find(
      (ip) =>
        ip.record.id === outPair.record.parent_record_id &&
        !usedInRecordIds.has(ip.record.id),
    );
    if (matchIn) {
      rows.push({
        incoming: toMatrixItem(matchIn),
        outgoing: toMatrixItem(outPair),
        confidence: 'confirmed',
      });
      usedInRecordIds.add(matchIn.record.id);
      usedOutRecordIds.add(outPair.record.id);
    }
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

  // === Phase 1.5: 文號交叉引用配對（高精度） ===
  // 如果發文主旨包含來文文號，或來文主旨包含發文文號 → 幾乎確定是對應
  const usedInIdx15 = new Set<number>();
  const usedOutIdx15 = new Set<number>();

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

      // 發文主旨提到來文文號，或來文主旨提到發文文號
      const outRefersIn = inDocNum.length > 4 && outSubject.includes(inDocNum);
      const inRefersOut = outDocNum.length > 4 && inSubject.includes(outDocNum);

      if (outRefersIn || inRefersOut) {
        rows.push({
          incoming: inItem,
          outgoing: outItem,
          confidence: 'confirmed',
          sharedEntities: [outRefersIn ? `引用文號:${inDocNum}` : `引用文號:${outDocNum}`],
        });
        usedInIdx15.add(i);
        usedOutIdx15.add(j);
        break;
      }
    }
  }

  // === Phase 1.7: 收發對調 + 主旨相似度配對（高精度） ===
  // 來文 A→B 且 發文 B→A 且主旨關鍵字有交集 → 高度對應
  // 注意：同一工程的公文大多是同組收發者，需主旨相似度過濾避免過度匹配
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

      // 收發對調: 來文 A→B，發文 B→A
      const flipMatch =
        (inSender.includes(outReceiver) || outReceiver.includes(inSender)) &&
        (inReceiver.includes(outSender) || outSender.includes(inReceiver));

      if (!flipMatch) continue;

      // 必須加入主旨相似度過濾，避免同組收發者的不相關公文被誤配
      const kwSim = keywordSimilarity(flipInKeywords[i]!, flipOutKeywords[j]!);
      if (kwSim < SIMILARITY_THRESHOLDS.FLIP_MATCH_MIN) continue; // 主旨完全無交集 → 跳過

      // 日期鄰近加分
      const inTime = inItem.docDate ? new Date(inItem.docDate).getTime() : 0;
      const outTime = outItem.docDate ? new Date(outItem.docDate).getTime() : 0;
      const dayGap = inTime && outTime ? (outTime - inTime) / (24 * 60 * 60 * 1000) : 999;
      if (dayGap < 0 || dayGap > 60) continue; // 發文必須在來文之後 60 天內

      // 複合分數: 主旨相似度 + 日期接近度
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

  // 預計算所有關鍵字集合
  const inKeywords = allUnpairedIn.map((item) => extractKeywords(item.subject));
  const outKeywords = allUnpairedOut.map((item) => extractKeywords(item.subject));

  // 建立 TF-IDF 權重表（同工程公文的共用詞自動降權）
  const allKeywordSets = [...inKeywords, ...outKeywords];
  const idfWeights = allKeywordSets.length >= 6
    ? buildIdfWeights(allKeywordSets)
    : undefined; // 文檔數太少時退化為普通 Jaccard

  // 建立實體分數快速查詢表 (inDocId → outDocId → score)
  const entityScoreMap = new Map<string, { jaccard: number; entities: string[] }>();
  if (entityScores) {
    for (const es of entityScores) {
      entityScoreMap.set(
        `${es.incoming_doc_id}-${es.outgoing_doc_id}`,
        { jaccard: es.jaccard, entities: es.shared_entities },
      );
    }
  }

  // 實體分數正規化：覆蓋率越高 → 實體越可靠 → 權重越高
  const totalPossiblePairs = allUnpairedIn.length * allUnpairedOut.length;
  const entityCoverage = totalPossiblePairs > 0
    ? entityScoreMap.size / totalPossiblePairs
    : 0;
  // 覆蓋率 >80% → 實體可信度高 → 權重提升至 0.5-0.6
  const effectiveEntityWeight = entityCoverage > 0.8
    ? 0.5 + 0.1 * Math.min((entityCoverage - 0.8) / 0.2, 1)
    : 0.4;
  const effectiveKeywordWeight = 1 - effectiveEntityWeight;

  // 將 Phase 1.5/1.7 已配對的索引加入排除集
  const usedOutIdx = new Set<number>(usedOutIdx15);

  // --- Phase 2: TF-IDF 關鍵字 + 正規化實體 複合相似度配對（高信心度） ---
  const SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLDS.HIGH_CONFIDENCE;
  const DATE_PROXIMITY_BONUS = SIMILARITY_THRESHOLDS.DATE_PROXIMITY_BONUS;
  const pendingInIndices: number[] = []; // 未被 Phase 2 配對的來文 index

  for (let i = 0; i < allUnpairedIn.length; i++) {
    if (usedInIdx15.has(i)) continue; // 已在 Phase 1.5/1.7 配對
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
      // 發文日期必須 ≥ 來文日期
      if (outDate < inDate) continue;

      const kwSim = keywordSimilarity(inKw, outKeywords[j]!, idfWeights);

      // 查詢實體配對分數
      const inDocId = inItem.docId;
      const outDocId = allUnpairedOut[j]!.docId;
      const entityMatch = (inDocId && outDocId)
        ? entityScoreMap.get(`${inDocId}-${outDocId}`)
        : undefined;
      const entitySim = entityMatch?.jaccard ?? 0;

      // 複合分數：動態加權（實體覆蓋率高時自動降權）
      let combinedScore = entitySim > 0
        ? kwSim * effectiveKeywordWeight + entitySim * effectiveEntityWeight
        : kwSim;

      // 日期鄰近加分：7 天內的配對獲得微幅加分（同分時優先選最近的）
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

  // --- Phase 3: 未配對公文 → 按業務類型分類排列 ---
  // 不強制日期配對，改為分類顯示（派工/審查/送件/行政等）
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

  // --- 排序: 配對行優先(confirmed>high) → 未配對按類型分組 → 各組內按日期 ---
  const confidenceOrder: Record<string, number> = { confirmed: 0, high: 1, medium: 2, low: 3 };
  rows.sort((a, b) => {
    const ca = confidenceOrder[a.confidence || 'low'] ?? 3;
    const cb = confidenceOrder[b.confidence || 'low'] ?? 3;
    if (ca !== cb) return ca - cb;
    // 同信心度: 按類型標籤分組, 組內按日期
    if (a.docTypeLabel !== b.docTypeLabel) {
      return (a.docTypeLabel || 'zzz').localeCompare(b.docTypeLabel || 'zzz');
    }
    const dateA = a.incoming?.docDate || a.outgoing?.docDate || '';
    const dateB = b.incoming?.docDate || b.outgoing?.docDate || '';
    return dateA.localeCompare(dateB);
  });

  return rows;
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
