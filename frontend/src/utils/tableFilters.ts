/**
 * 表頭篩選的兩種寫法 —— 一支工具，讓「這一種要不要帶 onFilter」不再靠人記。
 *
 * ⭐ 2026-09-09 owner：「表頭篩選請完善，已多次要求」。
 *
 * ## 為什麼會需要這支工具
 *
 * 同一件事（表頭漏斗）在兩種表格上要**用相反的寫法**，而寫錯不會報錯：
 *
 * | 表格 | 漏斗要怎麼寫 | 寫錯的下場 |
 * |---|---|---|
 * | **後端分頁**（`total` 來自伺服器） | `filters` ＋ `filteredValue`，**不得帶 `onFilter`** | 帶了 ⇒ `stripClientOnlyColumnFeatures` 把 `onFilter` **連同 `filters` 一起刪掉** ⇒ 原始碼看得到漏斗、線上看不到 |
 * | **全量在手**（前端分頁、詳情頁分頁） | `filters` ＋ **必須帶 `onFilter`** | 沒帶 ⇒ 漏斗畫得出來但點了不篩 |
 *
 * 2026-09-09 的實查：全庫「有排序沒篩選」不是一個 bug，是三個機制疊加
 * （自動強化的篩選白名單只有 11 個字／伺服器分頁的表格連自動強化都不跑／
 * 宣告了漏斗卻被剝除器整組刪掉），而**三種在畫面上長得一模一樣、都不會報錯**。
 *
 * ⇒ 把分岔收進函式，呼叫端只要回答「這張表的資料是不是全在手上」。
 *
 * ## 用法
 *
 * ```ts
 * // 後端分頁：值由 Table onChange 送進查詢參數
 * serverFilter(STATUS_OPTIONS, params.status)
 *
 * // 全量在手：就地篩
 * clientFilter(STATUS_OPTIONS, (r) => r.status)
 *
 * // onChange 取值（取消勾選要拿到 undefined，不是空字串）
 * onChange={(_p, filters) => setParams((p) => ({ ...p, status: pickFilter(filters, 'status'), page: 1 }))}
 * ```
 */
import type { ColumnType } from 'antd/es/table';

export interface FilterOption {
  value: string | number;
  label: React.ReactNode;
}

type AntdFilters = Record<string, (React.Key | boolean)[] | null> | undefined;

/**
 * 後端分頁的表格用。**刻意不回傳 `onFilter`** —— 帶了會被剝除器連 `filters` 一起刪掉。
 *
 * @param current 目前選中的值（來自查詢參數），用來讓漏斗顯示勾選狀態。
 *                不傳 `filteredValue` 的話，漏斗與工具列下拉會各持一份狀態。
 */
export function serverFilter<T>(
  options: readonly FilterOption[],
  current?: string | number | null,
  opts?: { multiple?: boolean; search?: boolean },
): Pick<ColumnType<T>, 'filters' | 'filterMultiple' | 'filteredValue' | 'filterSearch'> {
  return {
    filters: options.map((o) => ({ text: o.label as string, value: o.value })),
    filterMultiple: opts?.multiple ?? false,
    // null（不是 undefined）才會讓 antd 認為「這一欄目前沒有篩選」
    filteredValue: current === undefined || current === null || current === '' ? null : [current],
    ...(opts?.search ? { filterSearch: true } : {}),
  };
}

/**
 * 全量在手的表格用（前端分頁、詳情頁分頁）。**必須帶 `onFilter`**，否則漏斗點了不篩。
 *
 * @param get 從一列取出要比對的值
 */
export function clientFilter<T>(
  options: readonly FilterOption[],
  get: (record: T) => string | number | null | undefined,
  opts?: { multiple?: boolean; search?: boolean },
): Pick<ColumnType<T>, 'filters' | 'filterMultiple' | 'onFilter' | 'filterSearch'> {
  return {
    filters: options.map((o) => ({ text: o.label as string, value: o.value })),
    filterMultiple: opts?.multiple ?? false,
    onFilter: (value, record) => String(get(record) ?? '') === String(value),
    ...(opts?.search ? { filterSearch: true } : {}),
  };
}

/**
 * 從 antd `Table onChange` 的 filters 取單一值。
 *
 * ⚠️ 取消勾選時必須回 `undefined` 而不是空字串 —— 空字串會被後端當成
 * 「篩一個叫空字串的值」，結果是列表變空而畫面上看起來像沒篩。
 */
export function pickFilter(filters: AntdFilters, key: string): string | undefined {
  const v = filters?.[key]?.[0];
  if (v === undefined || v === null || v === '') return undefined;
  return String(v);
}

/** 同上，但回數字（年度那類欄位用）。非數字一律回 undefined。 */
export function pickFilterNumber(filters: AntdFilters, key: string): number | undefined {
  const raw = pickFilter(filters, key);
  if (raw === undefined) return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

/**
 * 從 antd `Table onChange` 的 sorter 取後端排序參數。
 *
 * ⚠️ 只對 `sorter: true`（伺服器端排序）有意義。函式型 sorter 在後端分頁的表格上
 * 會被剝除器刪掉，因為它只排得動當前這一頁。
 */
export function pickSort(
  sorter: unknown,
): { sort_by?: string; sort_order?: 'asc' | 'desc' } {
  const s = Array.isArray(sorter) ? sorter[0] : sorter;
  const field = (s as { field?: unknown })?.field;
  const order = (s as { order?: unknown })?.order;
  if (!field || !order) return { sort_by: undefined, sort_order: undefined };
  return {
    sort_by: String(field),
    sort_order: order === 'ascend' ? 'asc' : 'desc',
  };
}

/**
 * 全量在手、而**欄位值是陣列**時用（一個委託單位名下有多個計畫類別／承辦／案件狀態）。
 *
 * 語意是「**包含**」不是「等於」—— 用 `clientFilter` 的等值比對會全部不中，
 * 而畫面上只會看到「篩了之後一列都沒有」，看起來像沒有資料而不像判準錯了。
 */
export function clientFilterAny<T>(
  options: readonly FilterOption[],
  getAll: (record: T) => (string | number | null | undefined)[] | undefined,
  opts?: { multiple?: boolean; search?: boolean },
): Pick<ColumnType<T>, 'filters' | 'filterMultiple' | 'onFilter' | 'filterSearch'> {
  return {
    filters: options.map((o) => ({ text: o.label as string, value: o.value })),
    filterMultiple: opts?.multiple ?? false,
    onFilter: (value, record) =>
      (getAll(record) ?? []).some((v) => String(v ?? '') === String(value)),
    ...(opts?.search ? { filterSearch: true } : {}),
  };
}

/**
 * 從已載入的資料推導出漏斗選項（去重、排序）。
 *
 * 全量在手時這樣做是對的 —— 選項必然與資料一致。
 * ⚠️ **後端分頁的表格不可用這一支**：它只看得到當前這一頁，
 * 下拉會只列得出本頁有的值（2026-08-31 owner 回報的三種症狀之一）。
 */
export function distinctOptions<T>(
  rows: T[] | undefined,
  getAll: (record: T) => (string | number | null | undefined)[] | string | number | null | undefined,
): FilterOption[] {
  const set = new Set<string>();
  for (const r of rows ?? []) {
    const v = getAll(r);
    const arr = Array.isArray(v) ? v : [v];
    for (const x of arr) {
      if (x !== null && x !== undefined && String(x) !== '') set.add(String(x));
    }
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'zh-Hant')).map((v) => ({ value: v, label: v }));
}
