/**
 * chainUtils 單元測試
 *
 * 測試鏈式時間軸工具函數：
 * - buildChains / flattenChains
 * - isOutgoingDocNumber
 * - getEffectiveDocId / getEffectiveDoc
 * - buildDocPairs / getDocDirection
 */
import { describe, it, expect } from 'vitest';
import {
  buildChains,
  flattenChains,
  isOutgoingDocNumber,
  getEffectiveDocId,
  getEffectiveDoc,
  buildDocPairs,
  getDocDirection,
} from '../chainUtils';
import type { WorkRecord, DocBrief } from '../../../../types/taoyuan';

// ============================================================================
// Helpers
// ============================================================================

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
  } as DocBrief;
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

  it('無公文回傳 undefined', () => {
    const r = makeRecord({ id: 1 });
    expect(getEffectiveDoc(r)).toBeUndefined();
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
});
