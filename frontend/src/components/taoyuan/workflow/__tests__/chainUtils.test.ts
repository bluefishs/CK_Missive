/**
 * chainUtils 單元測試
 *
 * 測試鏈式時間軸工具函數：
 * - buildChains / flattenChains
 * - isOutgoingDocNumber
 * - getEffectiveDocId / getEffectiveDoc
 * - buildDocPairs / getDocDirection
 * - buildCorrespondenceMatrix (3-phase pairing algorithm)
 */
import { describe, it, expect } from 'vitest';
import {
  buildChains,
  flattenChains,
  isOutgoingDocNumber,
  getEffectiveDocId,
  getEffectiveDoc,
  buildDocPairs,
  buildCorrespondenceMatrix,
  getDocDirection,
} from '../chainUtils';
import type { ChainNode, DocPairs, CorrespondenceMatrixRow } from '../chainUtils';
import type { WorkRecord, DocBrief, DispatchDocumentLink } from '../../../../types/taoyuan';

// ============================================================================
// Factory Helpers
// ============================================================================

let _recordIdSeq = 0;

function makeRecord(overrides: Partial<WorkRecord> & { id: number }): WorkRecord {
  return {
    dispatch_order_id: 1,
    sort_order: 0,
    record_date: '2026-01-01',
    status: 'in_progress',
    milestone_type: 'other',
    ...overrides,
  } as WorkRecord;
}

function makeDocBrief(overrides: Partial<DocBrief> = {}): DocBrief {
  return {
    id: 100,
    doc_number: '桃工用字第1150002362號',
    subject: '測試公文主旨',
    doc_date: '2026-01-15',
    ...overrides,
  };
}

/** 建立來文 WorkRecord（舊格式 incoming_doc_id + incoming_doc） */
function makeIncomingRecord(
  id: number,
  docDate: string,
  overrides: Partial<WorkRecord> = {},
): WorkRecord {
  const doc = makeDocBrief({
    id: id * 10,
    doc_number: `桃工用字第${id}號`,
    doc_date: docDate,
  });
  return makeRecord({
    id,
    sort_order: id,
    record_date: docDate,
    incoming_doc_id: doc.id,
    incoming_doc: doc,
    ...overrides,
  });
}

/** 建立發文 WorkRecord（舊格式 outgoing_doc_id + outgoing_doc） */
function makeOutgoingRecord(
  id: number,
  docDate: string,
  overrides: Partial<WorkRecord> = {},
): WorkRecord {
  const doc = makeDocBrief({
    id: id * 10,
    doc_number: `乾坤測字第${id}號`,
    doc_date: docDate,
  });
  return makeRecord({
    id,
    sort_order: id,
    record_date: docDate,
    outgoing_doc_id: doc.id,
    outgoing_doc: doc,
    ...overrides,
  });
}

/** 建立未指派的 DispatchDocumentLink（來文） */
function makeUnassignedIncoming(
  documentId: number,
  docDate: string,
  overrides: Partial<DispatchDocumentLink> = {},
): DispatchDocumentLink {
  return {
    link_id: documentId + 9000,
    link_type: 'agency_incoming',
    dispatch_order_id: 1,
    document_id: documentId,
    doc_number: `桃工用字第UA${documentId}號`,
    doc_date: docDate,
    subject: `未指派來文 ${documentId}`,
    ...overrides,
  };
}

/** 建立未指派的 DispatchDocumentLink（發文） */
function makeUnassignedOutgoing(
  documentId: number,
  docDate: string,
  overrides: Partial<DispatchDocumentLink> = {},
): DispatchDocumentLink {
  return {
    link_id: documentId + 9000,
    link_type: 'company_outgoing',
    dispatch_order_id: 1,
    document_id: documentId,
    doc_number: `乾坤測字第UA${documentId}號`,
    doc_date: docDate,
    subject: `未指派發文 ${documentId}`,
    ...overrides,
  };
}

/** 從 records 陣列建構 DocPairs（使用 buildDocPairs） */
function makePairsFromRecords(records: WorkRecord[]): DocPairs {
  return buildDocPairs(records);
}

// ============================================================================
// buildChains
// ============================================================================

describe('buildChains', () => {
  it('空陣列回傳空陣列', () => {
    expect(buildChains([])).toEqual([]);
  });

  it('全部無 parent → 全部是 root', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2 }),
      makeRecord({ id: 3, sort_order: 3 }),
    ];
    const chains = buildChains(records);
    expect(chains).toHaveLength(3);
    expect(chains.every((c) => c.depth === 0)).toBe(true);
    expect(chains.every((c) => c.children.length === 0)).toBe(true);
  });

  it('鏈式結構正確掛載 parent → child', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 2 }),
    ];
    const chains = buildChains(records);

    expect(chains).toHaveLength(1); // 只有 1 個 root
    const root = chains[0]!;
    expect(root.record.id).toBe(1);
    expect(root.depth).toBe(0);
    expect(root.children).toHaveLength(1);
    const child1 = root.children[0]!;
    expect(child1.record.id).toBe(2);
    expect(child1.depth).toBe(1);
    const child2 = child1.children[0]!;
    expect(child2.record.id).toBe(3);
    expect(child2.depth).toBe(2);
  });

  it('parent 不在列表中 → child 成為 root', () => {
    const records = [
      makeRecord({ id: 5, sort_order: 1, parent_record_id: 999 }),
      makeRecord({ id: 6, sort_order: 2 }),
    ];
    const chains = buildChains(records);
    expect(chains).toHaveLength(2);
  });

  it('混合新舊格式（舊紀錄無 parent 作為獨立 root）', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }), // 舊格式
      makeRecord({ id: 2, sort_order: 2 }), // 舊格式
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 2 }), // 新格式
    ];
    const chains = buildChains(records);
    expect(chains).toHaveLength(2); // id=1 獨立 root, id=2 是 chain root
    expect(chains[1]!.children).toHaveLength(1);
  });

  it('按 sort_order 排序', () => {
    const records = [
      makeRecord({ id: 3, sort_order: 3 }),
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2 }),
    ];
    const chains = buildChains(records);
    expect(chains.map((c) => c.record.id)).toEqual([1, 2, 3]);
  });

  it('sort_order 相同時按 record_date 排序', () => {
    const records = [
      makeRecord({ id: 2, sort_order: 1, record_date: '2026-02-01' }),
      makeRecord({ id: 1, sort_order: 1, record_date: '2026-01-01' }),
    ];
    const chains = buildChains(records);
    expect(chains[0]!.record.id).toBe(1);
    expect(chains[1]!.record.id).toBe(2);
  });

  it('一個 parent 有多個 children', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 1 }),
    ];
    const chains = buildChains(records);
    expect(chains).toHaveLength(1);
    expect(chains[0]!.children).toHaveLength(2);
  });

  it('record_date 為 null 排在最前', () => {
    const records = [
      makeRecord({ id: 2, sort_order: 1, record_date: '2026-03-01' }),
      makeRecord({ id: 1, sort_order: 1, record_date: undefined }),
    ];
    const chains = buildChains(records);
    // null record_date → empty string '' < '2026-03-01'
    expect(chains[0]!.record.id).toBe(1);
    expect(chains[1]!.record.id).toBe(2);
  });

  it('深層巢狀（depth 3+）', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 2 }),
      makeRecord({ id: 4, sort_order: 4, parent_record_id: 3 }),
    ];
    const chains = buildChains(records);
    expect(chains).toHaveLength(1);
    const leaf = chains[0]!.children[0]!.children[0]!.children[0]!;
    expect(leaf.record.id).toBe(4);
    expect(leaf.depth).toBe(3);
  });

  it('不修改原始陣列（immutable sort）', () => {
    const records = [
      makeRecord({ id: 3, sort_order: 3 }),
      makeRecord({ id: 1, sort_order: 1 }),
    ];
    const original = [...records];
    buildChains(records);
    expect(records[0]!.id).toBe(original[0]!.id);
    expect(records[1]!.id).toBe(original[1]!.id);
  });
});

// ============================================================================
// flattenChains
// ============================================================================

describe('flattenChains', () => {
  it('空 roots 回傳空陣列', () => {
    expect(flattenChains([])).toEqual([]);
  });

  it('深度優先攤平', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 2 }),
      makeRecord({ id: 4, sort_order: 4 }),
    ];
    const chains = buildChains(records);
    const flat = flattenChains(chains);
    expect(flat.map((n) => n.record.id)).toEqual([1, 2, 3, 4]);
  });

  it('多個 root 各自深度優先', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3 }),
      makeRecord({ id: 4, sort_order: 4, parent_record_id: 3 }),
    ];
    const chains = buildChains(records);
    const flat = flattenChains(chains);
    // DFS: root1 → child1, root2 → child2
    expect(flat.map((n) => n.record.id)).toEqual([1, 2, 3, 4]);
  });

  it('分支結構攤平保持 DFS 順序', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 1 }),
      makeRecord({ id: 4, sort_order: 4, parent_record_id: 2 }),
    ];
    const chains = buildChains(records);
    const flat = flattenChains(chains);
    // DFS: 1 → 2 → 4 → 3
    expect(flat.map((n) => n.record.id)).toEqual([1, 2, 4, 3]);
  });

  it('depth 屬性正確保留', () => {
    const records = [
      makeRecord({ id: 1, sort_order: 1 }),
      makeRecord({ id: 2, sort_order: 2, parent_record_id: 1 }),
      makeRecord({ id: 3, sort_order: 3, parent_record_id: 2 }),
    ];
    const chains = buildChains(records);
    const flat = flattenChains(chains);
    expect(flat.map((n) => n.depth)).toEqual([0, 1, 2]);
  });

  it('單一節點無 children', () => {
    const records = [makeRecord({ id: 1, sort_order: 1 })];
    const chains = buildChains(records);
    const flat = flattenChains(chains);
    expect(flat).toHaveLength(1);
    expect(flat[0]!.record.id).toBe(1);
    expect(flat[0]!.depth).toBe(0);
  });
});

// ============================================================================
// isOutgoingDocNumber
// ============================================================================

describe('isOutgoingDocNumber', () => {
  it('「乾坤」開頭為發文', () => {
    expect(isOutgoingDocNumber('乾坤測字第1150000006號')).toBe(true);
  });

  it('非「乾坤」開頭為來文', () => {
    expect(isOutgoingDocNumber('桃工用字第1150002362號')).toBe(false);
  });

  it('null / undefined / 空字串回傳 false', () => {
    expect(isOutgoingDocNumber(null)).toBe(false);
    expect(isOutgoingDocNumber(undefined)).toBe(false);
    expect(isOutgoingDocNumber('')).toBe(false);
  });

  it('只有「乾坤」兩字也算發文', () => {
    expect(isOutgoingDocNumber('乾坤')).toBe(true);
  });

  it('中間包含「乾坤」但不在開頭 → false', () => {
    expect(isOutgoingDocNumber('測試乾坤字號')).toBe(false);
  });
});

// ============================================================================
// getEffectiveDocId
// ============================================================================

describe('getEffectiveDocId', () => {
  it('新格式 document_id 優先', () => {
    const r = makeRecord({
      id: 1,
      document_id: 100,
      incoming_doc_id: 200,
    });
    expect(getEffectiveDocId(r)).toBe(100);
  });

  it('舊格式 fallback incoming_doc_id', () => {
    const r = makeRecord({ id: 1, incoming_doc_id: 200 });
    expect(getEffectiveDocId(r)).toBe(200);
  });

  it('舊格式 fallback outgoing_doc_id', () => {
    const r = makeRecord({ id: 1, outgoing_doc_id: 300 });
    expect(getEffectiveDocId(r)).toBe(300);
  });

  it('無公文回傳 undefined', () => {
    const r = makeRecord({ id: 1 });
    expect(getEffectiveDocId(r)).toBeUndefined();
  });

  it('document_id 為 0（falsy）→ fallback 到舊格式', () => {
    // document_id = 0 is falsy in JS, so it should fallback
    const r = makeRecord({ id: 1, document_id: 0, incoming_doc_id: 200 });
    expect(getEffectiveDocId(r)).toBe(200);
  });

  it('incoming_doc_id 和 outgoing_doc_id 都存在 → incoming 優先', () => {
    const r = makeRecord({ id: 1, incoming_doc_id: 200, outgoing_doc_id: 300 });
    expect(getEffectiveDocId(r)).toBe(200);
  });

  it('document_id 為 null → fallback', () => {
    const r = makeRecord({ id: 1, document_id: undefined, outgoing_doc_id: 300 });
    expect(getEffectiveDocId(r)).toBe(300);
  });
});

// ============================================================================
// getEffectiveDoc
// ============================================================================

describe('getEffectiveDoc', () => {
  it('新格式 document 優先', () => {
    const doc = makeDocBrief({ id: 100 });
    const r = makeRecord({
      id: 1,
      document: doc,
      incoming_doc: makeDocBrief({ id: 200 }),
    });
    expect(getEffectiveDoc(r)).toBe(doc);
  });

  it('舊格式 fallback incoming_doc', () => {
    const inDoc = makeDocBrief({ id: 200 });
    const r = makeRecord({ id: 1, incoming_doc: inDoc });
    expect(getEffectiveDoc(r)).toBe(inDoc);
  });

  it('舊格式 fallback outgoing_doc', () => {
    const outDoc = makeDocBrief({ id: 300 });
    const r = makeRecord({ id: 1, outgoing_doc: outDoc });
    expect(getEffectiveDoc(r)).toBe(outDoc);
  });

  it('無公文回傳 undefined', () => {
    const r = makeRecord({ id: 1 });
    expect(getEffectiveDoc(r)).toBeUndefined();
  });

  it('incoming_doc 和 outgoing_doc 都存在 → incoming 優先（|| 短路）', () => {
    const inDoc = makeDocBrief({ id: 200 });
    const outDoc = makeDocBrief({ id: 300 });
    const r = makeRecord({ id: 1, incoming_doc: inDoc, outgoing_doc: outDoc });
    expect(getEffectiveDoc(r)).toBe(inDoc);
  });
});

// ============================================================================
// buildDocPairs
// ============================================================================

describe('buildDocPairs', () => {
  it('空陣列回傳空配對', () => {
    const pairs = buildDocPairs([]);
    expect(pairs.incomingDocs).toHaveLength(0);
    expect(pairs.outgoingDocs).toHaveLength(0);
  });

  it('舊格式 incoming_doc 歸類為來文', () => {
    const doc = makeDocBrief({ doc_number: '桃工用字第123號' });
    const r = makeRecord({ id: 1, incoming_doc: doc, incoming_doc_id: 100 });
    const pairs = buildDocPairs([r]);
    expect(pairs.incomingDocs).toHaveLength(1);
    expect(pairs.outgoingDocs).toHaveLength(0);
  });

  it('舊格式 outgoing_doc 歸類為發文', () => {
    const doc = makeDocBrief({ doc_number: '乾坤測字第456號' });
    const r = makeRecord({ id: 1, outgoing_doc: doc, outgoing_doc_id: 100 });
    const pairs = buildDocPairs([r]);
    expect(pairs.incomingDocs).toHaveLength(0);
    expect(pairs.outgoingDocs).toHaveLength(1);
  });

  it('新格式「乾坤」開頭歸類為發文', () => {
    const doc = makeDocBrief({ doc_number: '乾坤測字第789號' });
    const r = makeRecord({ id: 1, document: doc, document_id: 100 });
    const pairs = buildDocPairs([r]);
    expect(pairs.outgoingDocs).toHaveLength(1);
    expect(pairs.incomingDocs).toHaveLength(0);
  });

  it('新格式非「乾坤」歸類為來文', () => {
    const doc = makeDocBrief({ doc_number: '桃工用字第000號' });
    const r = makeRecord({ id: 1, document: doc, document_id: 100 });
    const pairs = buildDocPairs([r]);
    expect(pairs.incomingDocs).toHaveLength(1);
    expect(pairs.outgoingDocs).toHaveLength(0);
  });

  it('同時有舊格式時不重複計入新格式', () => {
    const inDoc = makeDocBrief({ id: 100 });
    const newDoc = makeDocBrief({ id: 200 });
    const r = makeRecord({
      id: 1,
      incoming_doc: inDoc,
      incoming_doc_id: 100,
      document: newDoc,
      document_id: 200,
    });
    const pairs = buildDocPairs([r]);
    // incoming_doc_id 存在 → 新格式 document 不計入
    expect(pairs.incomingDocs).toHaveLength(1);
    expect(pairs.incomingDocs[0]!.doc).toBe(inDoc);
  });

  it('多筆混合紀錄正確分類', () => {
    const records = [
      makeIncomingRecord(1, '2026-01-01'),
      makeOutgoingRecord(2, '2026-01-05'),
      makeIncomingRecord(3, '2026-01-10'),
      makeOutgoingRecord(4, '2026-01-15'),
    ];
    const pairs = buildDocPairs(records);
    expect(pairs.incomingDocs).toHaveLength(2);
    expect(pairs.outgoingDocs).toHaveLength(2);
  });

  it('無公文的紀錄不計入', () => {
    const r = makeRecord({ id: 1 });
    const pairs = buildDocPairs([r]);
    expect(pairs.incomingDocs).toHaveLength(0);
    expect(pairs.outgoingDocs).toHaveLength(0);
  });

  it('同一紀錄同時有 incoming_doc 和 outgoing_doc → 兩者都計入', () => {
    const inDoc = makeDocBrief({ id: 10 });
    const outDoc = makeDocBrief({ id: 20 });
    const r = makeRecord({
      id: 1,
      incoming_doc: inDoc,
      incoming_doc_id: 10,
      outgoing_doc: outDoc,
      outgoing_doc_id: 20,
    });
    const pairs = buildDocPairs([r]);
    expect(pairs.incomingDocs).toHaveLength(1);
    expect(pairs.outgoingDocs).toHaveLength(1);
  });
});

// ============================================================================
// getDocDirection
// ============================================================================

describe('getDocDirection', () => {
  it('新格式「乾坤」→ outgoing', () => {
    const doc = makeDocBrief({ doc_number: '乾坤測字第001號' });
    const r = makeRecord({ id: 1, document: doc, document_id: 100 });
    expect(getDocDirection(r)).toBe('outgoing');
  });

  it('新格式非「乾坤」→ incoming', () => {
    const doc = makeDocBrief({ doc_number: '桃工用字第001號' });
    const r = makeRecord({ id: 1, document: doc, document_id: 100 });
    expect(getDocDirection(r)).toBe('incoming');
  });

  it('舊格式 incoming_doc_id → incoming', () => {
    const doc = makeDocBrief();
    const r = makeRecord({ id: 1, incoming_doc: doc, incoming_doc_id: 100 });
    expect(getDocDirection(r)).toBe('incoming');
  });

  it('舊格式 outgoing_doc_id → outgoing', () => {
    const doc = makeDocBrief();
    const r = makeRecord({ id: 1, outgoing_doc: doc, outgoing_doc_id: 100 });
    expect(getDocDirection(r)).toBe('outgoing');
  });

  it('無公文 → null', () => {
    const r = makeRecord({ id: 1 });
    expect(getDocDirection(r)).toBeNull();
  });

  it('新格式有 document 但 doc_number 為 undefined → fallback 舊格式', () => {
    const doc = makeDocBrief({ doc_number: undefined });
    const r = makeRecord({ id: 1, document: doc, document_id: 100, incoming_doc_id: 200 });
    // document exists so getEffectiveDoc returns it, but doc_number is falsy
    // so it won't match isOutgoingDocNumber, falls through to incoming_doc_id check
    expect(getDocDirection(r)).toBe('incoming');
  });
});

// ============================================================================
// buildCorrespondenceMatrix
// ============================================================================

describe('buildCorrespondenceMatrix', () => {
  // --------------------------------------------------------------------------
  // Basic / empty cases
  // --------------------------------------------------------------------------

  describe('basic cases', () => {
    it('all empty inputs → empty result', () => {
      const emptyPairs: DocPairs = { incomingDocs: [], outgoingDocs: [] };
      const result = buildCorrespondenceMatrix(emptyPairs, [], []);
      expect(result).toEqual([]);
    });

    it('only assigned incoming docs → all rows have incoming, no outgoing', () => {
      const records = [
        makeIncomingRecord(1, '2026-01-10'),
        makeIncomingRecord(2, '2026-01-20'),
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(2);
      result.forEach((row) => {
        expect(row.incoming).toBeDefined();
        expect(row.outgoing).toBeUndefined();
        expect(row.incoming!.isUnassigned).toBe(false);
      });
    });

    it('only assigned outgoing docs → all rows have outgoing, no incoming', () => {
      const records = [
        makeOutgoingRecord(1, '2026-02-10'),
        makeOutgoingRecord(2, '2026-02-20'),
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(2);
      result.forEach((row) => {
        expect(row.outgoing).toBeDefined();
        expect(row.incoming).toBeUndefined();
        expect(row.outgoing!.isUnassigned).toBe(false);
      });
    });

    it('only unassigned incoming docs → all rows incoming-only with isUnassigned=true', () => {
      const unassignedIn = [
        makeUnassignedIncoming(501, '2026-03-01'),
        makeUnassignedIncoming(502, '2026-03-10'),
      ];
      const emptyPairs: DocPairs = { incomingDocs: [], outgoingDocs: [] };
      const result = buildCorrespondenceMatrix(emptyPairs, unassignedIn, []);

      expect(result).toHaveLength(2);
      result.forEach((row) => {
        expect(row.incoming).toBeDefined();
        expect(row.incoming!.isUnassigned).toBe(true);
        expect(row.outgoing).toBeUndefined();
      });
    });

    it('only unassigned outgoing docs → all rows outgoing-only with isUnassigned=true', () => {
      const unassignedOut = [
        makeUnassignedOutgoing(601, '2026-04-01'),
        makeUnassignedOutgoing(602, '2026-04-10'),
      ];
      const emptyPairs: DocPairs = { incomingDocs: [], outgoingDocs: [] };
      const result = buildCorrespondenceMatrix(emptyPairs, [], unassignedOut);

      expect(result).toHaveLength(2);
      result.forEach((row) => {
        expect(row.outgoing).toBeDefined();
        expect(row.outgoing!.isUnassigned).toBe(true);
        expect(row.incoming).toBeUndefined();
      });
    });
  });

  // --------------------------------------------------------------------------
  // Phase 1: parent_record_id chain pairing
  // --------------------------------------------------------------------------

  describe('Phase 1: parent_record_id chain pairing', () => {
    it('outgoing with parent_record_id matching incoming record.id → paired', () => {
      const inRecord = makeIncomingRecord(10, '2026-01-10');
      const outRecord = makeOutgoingRecord(20, '2026-01-20', {
        parent_record_id: 10,
      });
      const pairs = makePairsFromRecords([inRecord, outRecord]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Should have 1 paired row
      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
      expect(result[0]!.incoming!.docId).toBe(inRecord.incoming_doc!.id);
      expect(result[0]!.outgoing!.docId).toBe(outRecord.outgoing_doc!.id);
    });

    it('multiple parent_record_id pairings', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const out1 = makeOutgoingRecord(20, '2026-01-05', { parent_record_id: 10 });
      const in2 = makeIncomingRecord(30, '2026-02-01');
      const out2 = makeOutgoingRecord(40, '2026-02-05', { parent_record_id: 30 });
      const pairs = makePairsFromRecords([in1, out1, in2, out2]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(2);
      // Both rows should be paired
      result.forEach((row) => {
        expect(row.incoming).toBeDefined();
        expect(row.outgoing).toBeDefined();
      });
    });

    it('parent_record_id pointing to non-incoming record → not paired in Phase 1', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      // parent_record_id points to 999 which is not an incoming record
      const out1 = makeOutgoingRecord(20, '2026-01-05', { parent_record_id: 999 });
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Phase 1 fails, Phase 2 should pair by date proximity
      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
    });

    it('outgoing without parent_record_id → skipped in Phase 1, handled in Phase 2', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const out1 = makeOutgoingRecord(20, '2026-01-10');
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Should still pair via Phase 2 date proximity
      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
    });

    it('same incoming record cannot be used twice in Phase 1', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      // Two outgoing records both point to same incoming
      const out1 = makeOutgoingRecord(20, '2026-01-05', { parent_record_id: 10 });
      const out2 = makeOutgoingRecord(30, '2026-01-10', { parent_record_id: 10 });
      const pairs = makePairsFromRecords([in1, out1, out2]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // First match pairs in Phase 1, second goes to Phase 2/3
      // in1 is used, so out2 ends up standalone
      expect(result).toHaveLength(2);

      const pairedRow = result.find((r) => r.incoming && r.outgoing);
      expect(pairedRow).toBeDefined();

      const standaloneRow = result.find((r) => !r.incoming || !r.outgoing);
      expect(standaloneRow).toBeDefined();
    });
  });

  // --------------------------------------------------------------------------
  // Phase 2: Date proximity pairing
  // --------------------------------------------------------------------------

  describe('Phase 2: date proximity pairing', () => {
    it('outgoing date >= incoming date → paired (closest first)', () => {
      const in1 = makeIncomingRecord(10, '2026-01-10');
      const out1 = makeOutgoingRecord(20, '2026-01-15');
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
    });

    it('outgoing date < incoming date → NOT paired, separate rows', () => {
      // Outgoing date is BEFORE incoming date
      const in1 = makeIncomingRecord(10, '2026-02-01');
      const out1 = makeOutgoingRecord(20, '2026-01-15');
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // They should NOT pair because outDate < inDate
      expect(result).toHaveLength(2);
      const inRow = result.find((r) => r.incoming && !r.outgoing);
      const outRow = result.find((r) => r.outgoing && !r.incoming);
      expect(inRow).toBeDefined();
      expect(outRow).toBeDefined();
    });

    it('multiple incoming/outgoing → greedy closest pairing', () => {
      // in1(Jan-01) should pair with out1(Jan-05) not out2(Jan-20) - closest
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const in2 = makeIncomingRecord(11, '2026-01-15');
      const out1 = makeOutgoingRecord(20, '2026-01-05');
      const out2 = makeOutgoingRecord(21, '2026-01-20');
      const pairs = makePairsFromRecords([in1, in2, out1, out2]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(2);
      // in1(Jan-01) → out1(Jan-05) (closest outgoing >= incoming)
      // in2(Jan-15) → out2(Jan-20) (closest remaining)
      const row1 = result[0]!;
      const row2 = result[1]!;

      // Sorted by earliest date, so Jan-01 pair first
      expect(row1.incoming!.docDate).toBe('2026-01-01');
      expect(row1.outgoing!.docDate).toBe('2026-01-05');
      expect(row2.incoming!.docDate).toBe('2026-01-15');
      expect(row2.outgoing!.docDate).toBe('2026-01-20');
    });

    it('outgoing date == incoming date → should pair (>= condition)', () => {
      const in1 = makeIncomingRecord(10, '2026-01-10');
      const out1 = makeOutgoingRecord(20, '2026-01-10');
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
    });

    it('unassigned docs merge into Phase 2 pool', () => {
      // Assigned incoming, but no assigned outgoing
      // Unassigned outgoing should pair with it
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const pairs = makePairsFromRecords([in1]);
      const unassignedOut = [makeUnassignedOutgoing(601, '2026-01-10')];
      const result = buildCorrespondenceMatrix(pairs, [], unassignedOut);

      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.incoming!.isUnassigned).toBe(false);
      expect(result[0]!.outgoing).toBeDefined();
      expect(result[0]!.outgoing!.isUnassigned).toBe(true);
    });

    it('unassigned incoming pairs with unassigned outgoing', () => {
      const emptyPairs: DocPairs = { incomingDocs: [], outgoingDocs: [] };
      const unassignedIn = [makeUnassignedIncoming(501, '2026-01-01')];
      const unassignedOut = [makeUnassignedOutgoing(601, '2026-01-10')];
      const result = buildCorrespondenceMatrix(emptyPairs, unassignedIn, unassignedOut);

      expect(result).toHaveLength(1);
      expect(result[0]!.incoming!.isUnassigned).toBe(true);
      expect(result[0]!.outgoing!.isUnassigned).toBe(true);
    });

    it('assigned incoming + unassigned incoming sorted together before pairing', () => {
      // Assigned incoming at Jan-10, unassigned at Jan-05
      // Outgoing at Jan-08 should pair with closest incoming with date <= outgoing
      const in1 = makeIncomingRecord(10, '2026-01-10');
      const pairs = makePairsFromRecords([in1]);
      const unassignedIn = [makeUnassignedIncoming(501, '2026-01-05')];
      const unassignedOut = [makeUnassignedOutgoing(601, '2026-01-08')];
      const result = buildCorrespondenceMatrix(pairs, unassignedIn, unassignedOut);

      // unassigned incoming Jan-05 processes first (sorted), pairs with outgoing Jan-08
      // assigned incoming Jan-10 has no outgoing left → standalone
      expect(result).toHaveLength(2);

      const pairedRow = result.find((r) => r.incoming && r.outgoing);
      expect(pairedRow).toBeDefined();
      expect(pairedRow!.incoming!.docDate).toBe('2026-01-05');
      expect(pairedRow!.outgoing!.docDate).toBe('2026-01-08');
    });
  });

  // --------------------------------------------------------------------------
  // Phase 3: Remaining unpaired → standalone rows
  // --------------------------------------------------------------------------

  describe('Phase 3: remaining unpaired as standalone rows', () => {
    it('extra incoming without matching outgoing → standalone incoming rows', () => {
      const records = [
        makeIncomingRecord(10, '2026-01-01'),
        makeIncomingRecord(11, '2026-01-05'),
        makeIncomingRecord(12, '2026-01-10'),
        makeOutgoingRecord(20, '2026-01-03'),
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // in10(Jan-01) pairs with out20(Jan-03)
      // in11(Jan-05) and in12(Jan-10) standalone
      expect(result).toHaveLength(3);
      const standaloneRows = result.filter((r) => !r.outgoing);
      expect(standaloneRows).toHaveLength(2);
    });

    it('extra outgoing without matching incoming → standalone outgoing rows', () => {
      const records = [
        makeIncomingRecord(10, '2026-01-10'),
        makeOutgoingRecord(20, '2026-01-05'), // date < incoming, won't pair
        makeOutgoingRecord(21, '2026-01-03'), // date < incoming, won't pair
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Neither outgoing date >= incoming date for Phase 2
      // All three standalone
      expect(result).toHaveLength(3);
    });

    it('remaining unpaired outgoing after all incoming matched', () => {
      const records = [
        makeIncomingRecord(10, '2026-01-01'),
        makeOutgoingRecord(20, '2026-01-05'),
        makeOutgoingRecord(21, '2026-01-10'),
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // in10 pairs with out20 (closest >= Jan-01)
      // out21 standalone
      expect(result).toHaveLength(2);
      const standaloneOut = result.find((r) => !r.incoming && r.outgoing);
      expect(standaloneOut).toBeDefined();
      expect(standaloneOut!.outgoing!.docDate).toBe('2026-01-10');
    });
  });

  // --------------------------------------------------------------------------
  // Final sort by earliest date
  // --------------------------------------------------------------------------

  describe('final sort by earliest date', () => {
    it('results sorted by earliest date (incoming or outgoing)', () => {
      const records = [
        makeOutgoingRecord(20, '2026-03-01'),
        makeIncomingRecord(10, '2026-01-01'),
        makeIncomingRecord(11, '2026-02-01'),
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Should be sorted: Jan → Feb → Mar
      const dates = result.map(
        (r) => r.incoming?.docDate || r.outgoing?.docDate || '',
      );
      expect(dates).toEqual([...dates].sort());
    });

    it('Phase 1 paired rows also sorted by date', () => {
      const in1 = makeIncomingRecord(30, '2026-03-01');
      const out1 = makeOutgoingRecord(40, '2026-03-10', { parent_record_id: 30 });
      const in2 = makeIncomingRecord(10, '2026-01-01');
      const out2 = makeOutgoingRecord(20, '2026-01-10', { parent_record_id: 10 });
      const pairs = makePairsFromRecords([in1, out1, in2, out2]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(2);
      // Jan pair first, Mar pair second
      expect(result[0]!.incoming!.docDate).toBe('2026-01-01');
      expect(result[1]!.incoming!.docDate).toBe('2026-03-01');
    });

    it('outgoing-only row uses outgoing date for sort', () => {
      const emptyPairs: DocPairs = { incomingDocs: [], outgoingDocs: [] };
      const unassignedIn = [makeUnassignedIncoming(501, '2026-02-01')];
      const unassignedOut = [
        makeUnassignedOutgoing(601, '2026-01-01'), // earlier
        makeUnassignedOutgoing(602, '2026-03-01'), // later
      ];
      const result = buildCorrespondenceMatrix(emptyPairs, unassignedIn, unassignedOut);

      // out601(Jan-01) cannot pair with in501(Feb-01) because Jan < Feb
      // Actually out601 date is Jan-01, in501 date is Feb-01
      // Phase 2: for in501, find outgoing >= Feb-01 → out602(Mar-01) is the closest
      // out601 remains standalone
      // Sort: Jan-01 (out601 standalone), Feb-01 (in501+out602)
      expect(result).toHaveLength(2);
      const firstDate = result[0]!.incoming?.docDate || result[0]!.outgoing?.docDate;
      const secondDate = result[1]!.incoming?.docDate || result[1]!.outgoing?.docDate;
      expect(firstDate! <= secondDate!).toBe(true);
    });
  });

  // --------------------------------------------------------------------------
  // Mixed scenarios (all phases together)
  // --------------------------------------------------------------------------

  describe('mixed scenarios', () => {
    it('Phase 1 + Phase 2 + Phase 3 combined', () => {
      // Phase 1 pair: in10 ← out20 (parent_record_id)
      const in10 = makeIncomingRecord(10, '2026-01-01');
      const out20 = makeOutgoingRecord(20, '2026-01-05', { parent_record_id: 10 });

      // Phase 2 pair: in11 ← out21 (date proximity)
      const in11 = makeIncomingRecord(11, '2026-02-01');
      const out21 = makeOutgoingRecord(21, '2026-02-10');

      // Phase 3 standalone: in12 has no outgoing
      const in12 = makeIncomingRecord(12, '2026-03-01');

      const pairs = makePairsFromRecords([in10, out20, in11, out21, in12]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(3);

      // All sorted by date
      const dates = result.map(
        (r) => r.incoming?.docDate || r.outgoing?.docDate || '',
      );
      expect(dates).toEqual([...dates].sort());

      // Row 1: Jan pair (Phase 1)
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();

      // Row 2: Feb pair (Phase 2)
      expect(result[1]!.incoming).toBeDefined();
      expect(result[1]!.outgoing).toBeDefined();

      // Row 3: Mar standalone
      expect(result[2]!.incoming).toBeDefined();
      expect(result[2]!.outgoing).toBeUndefined();
    });

    it('assigned + unassigned mixed correctly', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const pairs = makePairsFromRecords([in1]);
      const unassignedIn = [makeUnassignedIncoming(501, '2026-02-01')];
      const unassignedOut = [
        makeUnassignedOutgoing(601, '2026-01-10'),
        makeUnassignedOutgoing(602, '2026-02-15'),
      ];
      const result = buildCorrespondenceMatrix(pairs, unassignedIn, unassignedOut);

      // in1(Jan-01) pairs with out601(Jan-10): closest outgoing >= Jan-01
      // unassigned in501(Feb-01) pairs with out602(Feb-15): closest outgoing >= Feb-01
      expect(result).toHaveLength(2);
      expect(result[0]!.incoming!.isUnassigned).toBe(false); // assigned
      expect(result[0]!.outgoing!.isUnassigned).toBe(true);  // unassigned
      expect(result[1]!.incoming!.isUnassigned).toBe(true);  // unassigned
      expect(result[1]!.outgoing!.isUnassigned).toBe(true);  // unassigned
    });

    it('Phase 1 consumes records so Phase 2 does not re-use them', () => {
      const in10 = makeIncomingRecord(10, '2026-01-01');
      const out20 = makeOutgoingRecord(20, '2026-01-05', { parent_record_id: 10 });
      // Another outgoing with no parent - should not pair with in10 (already used)
      const out21 = makeOutgoingRecord(21, '2026-01-03');

      const pairs = makePairsFromRecords([in10, out20, out21]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Phase 1: in10 + out20 paired
      // Phase 2: in10 already used, out21 standalone
      expect(result).toHaveLength(2);

      const pairedRow = result.find((r) => r.incoming && r.outgoing);
      expect(pairedRow).toBeDefined();

      const standaloneRow = result.find((r) => !r.incoming);
      expect(standaloneRow).toBeDefined();
      expect(standaloneRow!.outgoing!.docDate).toBe('2026-01-03');
    });
  });

  // --------------------------------------------------------------------------
  // MatrixDocItem field mapping
  // --------------------------------------------------------------------------

  describe('MatrixDocItem field mapping', () => {
    it('assigned doc maps to MatrixDocItem with correct fields', () => {
      const inRecord = makeIncomingRecord(10, '2026-01-10');
      inRecord.description = '收文處理說明';
      const pairs = makePairsFromRecords([inRecord]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      const item = result[0]!.incoming!;
      expect(item.docId).toBe(inRecord.incoming_doc!.id);
      expect(item.docNumber).toBe(inRecord.incoming_doc!.doc_number);
      expect(item.docDate).toBe(inRecord.incoming_doc!.doc_date);
      // subject comes from record.description || doc.subject
      expect(item.subject).toBe('收文處理說明');
      expect(item.record).toBe(inRecord);
      expect(item.isUnassigned).toBe(false);
      expect(item.linkedDoc).toBeUndefined();
    });

    it('assigned doc without description uses doc.subject', () => {
      const inRecord = makeIncomingRecord(10, '2026-01-10');
      inRecord.description = undefined;
      const pairs = makePairsFromRecords([inRecord]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      const item = result[0]!.incoming!;
      expect(item.subject).toBe(inRecord.incoming_doc!.subject);
    });

    it('unassigned doc maps to MatrixDocItem with linkedDoc', () => {
      const emptyPairs: DocPairs = { incomingDocs: [], outgoingDocs: [] };
      const link = makeUnassignedIncoming(501, '2026-01-01');
      const result = buildCorrespondenceMatrix(emptyPairs, [link], []);

      const item = result[0]!.incoming!;
      expect(item.docId).toBe(link.document_id);
      expect(item.docNumber).toBe(link.doc_number);
      expect(item.docDate).toBe(link.doc_date);
      expect(item.subject).toBe(link.subject);
      expect(item.linkedDoc).toBe(link);
      expect(item.isUnassigned).toBe(true);
      expect(item.record).toBeUndefined();
    });
  });

  // --------------------------------------------------------------------------
  // Edge cases
  // --------------------------------------------------------------------------

  describe('edge cases', () => {
    it('docs with missing dates treated as empty string in comparisons', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      in1.incoming_doc = makeDocBrief({ id: 100, doc_date: undefined });
      const out1 = makeOutgoingRecord(20, '2026-01-05');
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // Empty string '' < '2026-01-05' so outDate >= inDate → should pair
      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
    });

    it('single incoming + single outgoing with correct dates → one paired row', () => {
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const out1 = makeOutgoingRecord(20, '2026-01-15');
      const pairs = makePairsFromRecords([in1, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(1);
      expect(result[0]!.incoming).toBeDefined();
      expect(result[0]!.outgoing).toBeDefined();
    });

    it('many incoming, one outgoing → one pair + rest standalone', () => {
      const records = [
        makeIncomingRecord(10, '2026-01-01'),
        makeIncomingRecord(11, '2026-01-05'),
        makeIncomingRecord(12, '2026-01-10'),
        makeOutgoingRecord(20, '2026-01-06'),
      ];
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // in10(Jan-01) processes first, pairs with out20(Jan-06) as closest >= Jan-01
      // in11(Jan-05) and in12(Jan-10) standalone
      expect(result).toHaveLength(3);
      const pairedRows = result.filter((r) => r.incoming && r.outgoing);
      expect(pairedRows).toHaveLength(1);
    });

    it('greedy algorithm: earlier incoming claims closest outgoing even if suboptimal', () => {
      // in1(Jan-01) will greedily take out1(Jan-02) even though
      // in2(Jan-01) also exists and could have used out1 "better"
      const in1 = makeIncomingRecord(10, '2026-01-01');
      const in2 = makeIncomingRecord(11, '2026-01-01');
      const out1 = makeOutgoingRecord(20, '2026-01-02');
      const pairs = makePairsFromRecords([in1, in2, out1]);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      expect(result).toHaveLength(2);
      const pairedRows = result.filter((r) => r.incoming && r.outgoing);
      const standaloneRows = result.filter((r) => r.incoming && !r.outgoing);
      expect(pairedRows).toHaveLength(1);
      expect(standaloneRows).toHaveLength(1);
    });

    it('large dataset: 10 incoming + 10 outgoing pairs correctly', () => {
      const records: WorkRecord[] = [];
      for (let i = 1; i <= 10; i++) {
        const day = String(i).padStart(2, '0');
        records.push(makeIncomingRecord(i, `2026-01-${day}`));
        records.push(makeOutgoingRecord(i + 100, `2026-02-${day}`));
      }
      const pairs = makePairsFromRecords(records);
      const result = buildCorrespondenceMatrix(pairs, [], []);

      // All should pair (each outgoing Feb-XX >= incoming Jan-XX)
      expect(result).toHaveLength(10);
      result.forEach((row) => {
        expect(row.incoming).toBeDefined();
        expect(row.outgoing).toBeDefined();
      });

      // Sorted by date
      for (let i = 1; i < result.length; i++) {
        const prevDate = result[i - 1]!.incoming?.docDate || '';
        const currDate = result[i]!.incoming?.docDate || '';
        expect(prevDate <= currDate).toBe(true);
      }
    });
  });
});
