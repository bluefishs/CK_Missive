/**
 * `buildServerFilters` 的判準鎖 —— 2026-09-09 owner 問題 2：
 * 「若表格調整欄位呈現項目，那表標頭篩選排序機制是否又會失效或再次設定」。
 *
 * 答案是**會**，因為在此之前同一條篩選鏈有三處各自宣告：
 * 欄位的 `key`、`filteredValue` 讀的參數名、`onChange` 裡手寫的字串。
 * `/erp/quotations` 的「年度」欄實例：`key: 'case_code'`、值存 `params.year`、
 * onChange 寫 `first('case_code')` —— 同一件事三個名字，改任一處另兩處不會報錯。
 *
 * 這支測試守的是「收成一份之後，那三處必然同步」。
 */
import { describe, it, expect } from 'vitest';
import { buildServerFilters } from '../tableFilters';

const YEARS = [{ value: 2026, label: '2026' }, { value: 2025, label: '2025' }] as const;
const STATUS = [{ value: 'active', label: '執行中' }, { value: 'closed', label: '已結案' }] as const;

/** 這一頁的查詢參數型別。`param` 的合法值就是它的鍵集合 —— 打錯字由 tsc 擋。 */
type Params = { year?: number; status?: string };
const EMPTY: Params = {};

const DEFS = [
  { columnKey: 'case_code', param: 'year', options: YEARS, numeric: true },
  { columnKey: 'status', param: 'status', options: STATUS },
] as const;

describe('buildServerFilters', () => {
  it('bind 用欄位鍵取，值卻是從參數名讀的（兩者可以不同名，這正是重點）', () => {
    const f = buildServerFilters(DEFS, { year: 2026, status: undefined });
    expect(f.bind('case_code').filteredValue).toEqual([2026]);
    expect(f.bind('status').filteredValue).toBeNull();
  });

  it('bind 不回傳 onFilter —— 後端分頁帶了會被剝除器連 filters 一起刪掉', () => {
    const f = buildServerFilters(DEFS, EMPTY);
    expect(f.bind('case_code')).not.toHaveProperty('onFilter');
    expect(f.bind('case_code').filters).toHaveLength(2);
  });

  it('read 以欄位鍵解讀 antd 的 filters，寫回參數名', () => {
    const f = buildServerFilters(DEFS, EMPTY);
    expect(f.read({ case_code: [2025], status: ['closed'] })).toEqual({ year: 2025, status: 'closed' });
  });

  it('⭐ read 必須涵蓋每一個宣告過的參數 —— 取消勾選要回 undefined，不能整個 key 消失', () => {
    const f = buildServerFilters(DEFS, { year: 2026, status: 'active' });
    const out = f.read({ case_code: null, status: null });
    // 若這裡少了任一個 key，展開進 params 時舊值會留著 ⇒ 畫面說沒篩、資料仍被篩
    expect(Object.keys(out).sort()).toEqual(['status', 'year']);
    expect(out.year).toBeUndefined();
    expect(out.status).toBeUndefined();
  });

  it('numeric 的欄位回數字、非 numeric 回字串', () => {
    const f = buildServerFilters(DEFS, EMPTY);
    const out = f.read({ case_code: ['2025'], status: ['closed'] });
    expect(out.year).toBe(2025);
    expect(out.status).toBe('closed');
  });

  it('帶 sorter 時一併回後端排序參數；沒排序時兩欄都是 undefined（要能清掉）', () => {
    const f = buildServerFilters(DEFS, EMPTY);
    expect(f.read({}, { field: 'total_price', order: 'descend' })).toMatchObject({ sort_by: 'total_price', sort_order: 'desc' });
    expect(f.read({}, { field: 'total_price', order: undefined })).toMatchObject({ sort_by: undefined, sort_order: undefined });
  });

  it('不傳 sorter 就不碰排序參數（有些頁面的排序另外管）', () => {
    const f = buildServerFilters(DEFS, EMPTY);
    expect(f.read({})).not.toHaveProperty('sort_by');
  });

  it('sortField 可改寫欄位名 —— 前端欄名與後端排序鍵不同時（議價金額 ⇒ total_price）', () => {
    const f = buildServerFilters(DEFS, EMPTY, { sortField: (k) => (k === 'contract_amount' ? 'total_price' : k) });
    expect(f.read({}, { field: 'contract_amount', order: 'ascend' })).toMatchObject({ sort_by: 'total_price', sort_order: 'asc' });
  });
  it('⭐ 打錯字兩層都會吵：tsc 先擋，執行期再擋（不是靜靜地少一個漏斗）', () => {
    // @ts-expect-error `yaer` 不是 Params 的鍵 —— 這一行若不再報錯，代表型別防護掉了。
    const bad = buildServerFilters([{ columnKey: 'x', param: 'yaer', options: YEARS }] as const, EMPTY);
    expect(bad).toBeDefined();

    // @ts-expect-error `case_cod` 不在 defs 的 columnKey 裡。
    expect(() => buildServerFilters(DEFS, EMPTY).bind('case_cod')).toThrow('未宣告');

    // 對照：正確的鍵不得拋錯
    expect(() => buildServerFilters(DEFS, EMPTY).bind('case_code')).not.toThrow();
  });
});
