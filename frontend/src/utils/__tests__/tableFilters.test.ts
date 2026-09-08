/**
 * 表頭篩選工具的判準鎖 —— 2026-09-09。
 *
 * 這支測試守的是「兩種寫法的差別」本身：
 * 後端分頁的欄位**不得**帶 `onFilter`（帶了會被剝除器連 filters 一起刪掉），
 * 全量在手的欄位**必須**帶。這條規則寫錯不會報錯，只會在畫面上安靜地少一個漏斗。
 */
import { describe, it, expect } from 'vitest';
import { serverFilter, clientFilter, clientFilterAny, distinctOptions, pickFilter, pickFilterNumber, pickSort } from '../tableFilters';
import { stripClientOnlyColumnFeatures } from '../tableEnhancer';

const OPTS = [
  { value: 'in_use', label: '使用中' },
  { value: 'idle', label: '閒置' },
];

describe('serverFilter（後端分頁）', () => {
  it('不得帶 onFilter —— 帶了會被剝除器連 filters 一起刪掉', () => {
    const col = serverFilter(OPTS, 'in_use');
    expect(col).not.toHaveProperty('onFilter');
    expect(col.filters).toHaveLength(2);
  });

  it('經過剝除器之後漏斗仍然在（這是它存在的理由）', () => {
    const [out] = stripClientOnlyColumnFeatures([
      { title: '狀態', dataIndex: 'status', ...serverFilter(OPTS, 'in_use') },
    ]);
    expect((out as { filters?: unknown[] }).filters).toHaveLength(2);
    expect((out as { filteredValue?: unknown }).filteredValue).toEqual(['in_use']);
  });

  it('沒選時 filteredValue 是 null 而不是 undefined 或 []', () => {
    expect(serverFilter(OPTS, undefined).filteredValue).toBeNull();
    expect(serverFilter(OPTS, '').filteredValue).toBeNull();
    expect(serverFilter(OPTS, null).filteredValue).toBeNull();
  });

  it('filterSearch 只在要求時才給（高基數欄位才需要）', () => {
    expect(serverFilter(OPTS, null)).not.toHaveProperty('filterSearch');
    expect(serverFilter(OPTS, null, { search: true }).filterSearch).toBe(true);
  });
});

describe('clientFilter（全量在手）', () => {
  it('必須帶 onFilter —— 沒帶的話漏斗點了不篩', () => {
    const col = clientFilter<{ status: string }>(OPTS, (r) => r.status);
    expect(typeof col.onFilter).toBe('function');
    expect(col.onFilter!('in_use', { status: 'in_use' })).toBe(true);
    expect(col.onFilter!('in_use', { status: 'idle' })).toBe(false);
  });

  it('值為 null／undefined 的列不會誤中', () => {
    const col = clientFilter<{ status?: string | null }>(OPTS, (r) => r.status);
    expect(col.onFilter!('in_use', { status: null })).toBe(false);
    expect(col.onFilter!('in_use', {})).toBe(false);
  });

  it('數字與字串混用時仍比得出來（antd 的 value 可能被轉型）', () => {
    const col = clientFilter<{ year: number }>([{ value: 2026, label: '2026' }], (r) => r.year);
    expect(col.onFilter!('2026', { year: 2026 })).toBe(true);
  });
});

describe('pickFilter', () => {
  it('取消勾選回 undefined 而不是空字串', () => {
    expect(pickFilter({ status: null }, 'status')).toBeUndefined();
    expect(pickFilter({ status: [] }, 'status')).toBeUndefined();
    expect(pickFilter({ status: [''] }, 'status')).toBeUndefined();
    expect(pickFilter(undefined, 'status')).toBeUndefined();
  });

  it('有勾選時回字串', () => {
    expect(pickFilter({ status: ['in_use'] }, 'status')).toBe('in_use');
    expect(pickFilter({ year: [2026] }, 'year')).toBe('2026');
  });

  it('pickFilterNumber 只回真的數字', () => {
    expect(pickFilterNumber({ year: [2026] }, 'year')).toBe(2026);
    expect(pickFilterNumber({ year: ['abc'] }, 'year')).toBeUndefined();
    expect(pickFilterNumber({ year: null }, 'year')).toBeUndefined();
  });
});

describe('pickSort', () => {
  it('沒有排序時兩個欄位都是 undefined（要能清掉先前的排序）', () => {
    expect(pickSort({ field: 'name', order: undefined })).toEqual({ sort_by: undefined, sort_order: undefined });
    expect(pickSort(undefined)).toEqual({ sort_by: undefined, sort_order: undefined });
  });

  it('ascend／descend 轉成後端的 asc／desc', () => {
    expect(pickSort({ field: 'name', order: 'ascend' })).toEqual({ sort_by: 'name', sort_order: 'asc' });
    expect(pickSort({ field: 'amount', order: 'descend' })).toEqual({ sort_by: 'amount', sort_order: 'desc' });
  });

  it('多欄排序時取第一個（後端只接受單欄）', () => {
    expect(pickSort([{ field: 'a', order: 'ascend' }, { field: 'b', order: 'descend' }]).sort_by).toBe('a');
  });
});

describe('clientFilterAny（陣列欄位）', () => {
  type Row = { statuses?: { label: string }[] };
  const col = clientFilterAny<Row>([{ value: '執行中', label: '執行中' }], (r) => r.statuses?.map((s) => s.label));

  it('包含就算中（不是等於）', () => {
    expect(col.onFilter!('執行中', { statuses: [{ label: '已結案' }, { label: '執行中' }] })).toBe(true);
  });

  it('不包含不中，空陣列與 undefined 都不中', () => {
    expect(col.onFilter!('執行中', { statuses: [{ label: '已結案' }] })).toBe(false);
    expect(col.onFilter!('執行中', { statuses: [] })).toBe(false);
    expect(col.onFilter!('執行中', {})).toBe(false);
  });
});

describe('distinctOptions', () => {
  it('陣列欄位去重（不斷言中文定序 —— 那依賴執行環境有沒有 ICU 語系資料）', () => {
    const rows = [{ c: ['乙', '甲'] }, { c: ['甲'] }, { c: [] }, { c: undefined }];
    const got = distinctOptions(rows, (r) => r.c).map((o) => o.value);
    expect(got).toHaveLength(2);
    expect(new Set(got)).toEqual(new Set(['甲', '乙']));
  });

  it('排序是穩定的：同一份資料不同輸入順序得到同一個結果', () => {
    const a = distinctOptions([{ c: ['b', 'a'] }], (r) => r.c).map((o) => o.value);
    const b = distinctOptions([{ c: ['a'] }, { c: ['b'] }], (r) => r.c).map((o) => o.value);
    expect(a).toEqual(b);
    expect(a).toEqual(['a', 'b']);
  });

  it('純量欄位也吃，空值不入選項', () => {
    const rows = [{ s: 'a' }, { s: '' }, { s: null }, { s: 'b' }, { s: 'a' }];
    expect(distinctOptions(rows, (r) => r.s).map((o) => o.value)).toEqual(['a', 'b']);
  });

  it('沒有資料時回空陣列而不是爆掉', () => {
    expect(distinctOptions(undefined, (r: { x?: string }) => r.x)).toEqual([]);
  });
});
