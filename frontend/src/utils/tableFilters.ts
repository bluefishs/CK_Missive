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

/* ────────────────────────────────────────────────────────────────────────────
 * 收斂：一份宣告產生「欄位漏斗」與「onChange 解讀」
 * ──────────────────────────────────────────────────────────────────────────── */

/**
 * 一個後端篩選欄位的完整宣告。
 *
 * ⭐ 2026-09-09 owner 問題 2：「若表格調整欄位呈現項目，那表標頭篩選排序機制
 * 是否又會失效或再次設定」。**在此之前答案是「會」**，而且不會報錯 ——
 * 同一條篩選鏈有三處各自寫著它的名字：
 *
 *   ① 欄位的 `key` / `dataIndex`（漏斗掛在哪一欄）
 *   ② `filteredValue` 讀的查詢參數名（勾選狀態從哪裡來）
 *   ③ `onChange` 裡**手寫的字串**（值怎麼被讀回去）
 *
 * 實例（`/erp/quotations` 的「年度」欄）：`key: 'case_code'`、值存 `params.year`、
 * onChange 寫 `first('case_code')` —— **同一件事三個名字**。
 * 把年度獨立成 `dataIndex: 'year'` 這種再正常不過的欄位調整，
 * ③ 立刻對不上 ⇒ 漏斗點了沒有反應，而 tsc 全綠、主控台安靜。
 *
 * 收成一份之後：改欄位鍵只改 `columnKey` 一個字，①②③ 同時跟上；
 * 而 `bind()` 的參數型別是從 `defs` 推導的字面聯集 ⇒ **打錯字由 tsc 擋下**。
 */
export interface ServerFilterDef<K extends string = string> {
  /** 漏斗掛在哪一欄（antd column 的 `key`，沒給 key 時是 `dataIndex`） */
  columnKey: string;
  /** 值存進查詢參數的哪個欄位（可以與 columnKey 不同名）。型別是查詢參數的鍵集合 ⇒ 打錯字 tsc 會擋。 */
  param: K;
  options: readonly FilterOption[];
  /** 年度那類欄位：讀回來要是數字 */
  numeric?: boolean;
  multiple?: boolean;
  search?: boolean;
}

/**
 * 建立一組「宣告一次、兩邊都跟上」的後端篩選。
 *
 * ```tsx
 * const F = buildServerFilters(FILTER_DEFS, params);
 * // 欄位：{ title: '年度', dataIndex: 'case_code', key: 'case_code', ...F.bind('case_code') }
 * // 表格：onChange={(_p, filters, sorter) => setParams((prev) => ({ ...prev, ...F.read(filters, sorter), skip: 0 }))}
 * ```
 *
 * @param current 目前的查詢參數物件（讀 `def.param` 取勾選值）
 * @param opts.sortField 前端欄名與後端排序鍵不同時的改寫（例：議價金額 ⇒ total_price）
 */
export function buildServerFilters<
  P extends Record<string, unknown>,
  const D extends readonly ServerFilterDef<Extract<keyof P, string>>[],
>(
  defs: D,
  current: P,
  opts?: { sortField?: (field: string) => string },
) {
  const byColumn = new Map<string, ServerFilterDef>(defs.map((d) => [d.columnKey, d]));

  return {
    /** 展開進欄位定義。`columnKey` 不在 `defs` 裡時 tsc 會報錯（這是它存在的一半理由）。 */
    bind<T = unknown>(columnKey: D[number]['columnKey']) {
      const d = byColumn.get(columnKey);
      /* istanbul ignore next -- 型別已擋住，這是執行期的最後一道 */
      if (!d) throw new Error(`buildServerFilters: 欄位鍵 '${columnKey}' 未宣告`);
      const raw = current[d.param];
      return serverFilter<T>(d.options, raw as string | number | null | undefined, {
        multiple: d.multiple,
        search: d.search,
      });
    },

    /**
     * 從 antd `Table onChange` 的 `filters`（與可選的 `sorter`）解讀出要併回查詢參數的物件。
     *
     * ⚠️ **每一個宣告過的 `param` 都必然出現在回傳值裡**，取消勾選時是 `undefined`。
     * 少一個 key 的話，展開進 `params` 時舊值會留著 ⇒ **畫面說沒篩、資料仍被篩**
     * （本 repo 記過這個形狀：隱形篩選比不篩更糟，使用者不知道自己看到的是子集）。
     */
    read(filters: AntdFilters, sorter?: unknown): Record<string, unknown> {
      const out: Record<string, unknown> = {};
      for (const d of defs) {
        out[d.param] = d.numeric
          ? pickFilterNumber(filters, d.columnKey)
          : pickFilter(filters, d.columnKey);
      }
      if (sorter !== undefined) {
        const s = pickSort(sorter);
        out.sort_by = s.sort_by !== undefined && opts?.sortField ? opts.sortField(s.sort_by) : s.sort_by;
        out.sort_order = s.sort_order;
      }
      return out;
    },
  };
}
