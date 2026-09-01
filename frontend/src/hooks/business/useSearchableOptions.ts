/**
 * 伺服器端搜尋的下拉選項 —— 通用 Hook
 *
 * ## 為什麼需要它（2026-09-01）
 *
 * 「一次抓 N 筆、前端過濾」這個做法有一個**會被時間追上**的上限：
 *
 *   承攬案件 226 筆、PM 案件 253 筆，而 owner 要選的那一筆排第 144 名。
 *   固定 `limit: 100` ⇒ 選不到；改 200 ⇒ 端點上限 100 而回 **422** ⇒ 整個下拉變空；
 *   改成分頁續抓 ⇒ 讀錯 `total` 欄位 ⇒ 迴圈一次都沒跑。
 *
 * 三次修法、三種失敗，**共同點是「先把全部拿下來」這個前提**。
 * owner：「案件只會變多」⇒ 改成把搜尋交給後端，資料量就不再是變數。
 *
 * ## 這支處理三件容易漏的事
 *
 * 1. **防抖** —— 每打一個字就打一次 API 會把後端打爆。
 * 2. **已選值的標籤** —— 伺服器端搜尋最常見的 bug：使用者已選的值不在
 *    當前搜尋結果裡，AntD 就直接顯示**原始 id 數字**（本 repo 記過同型：
 *    `useUsersDropdown` 的「同仁變成代碼」）。這裡會單獨把已選值查回來並併入。
 * 3. **載入失敗要出聲** —— 回空陣列與「真的沒有資料」在畫面上一模一樣。
 *    `isError` 往外給，呼叫端才有機會說出來。
 *
 * ## 用法
 *
 *     const { options, onSearch, isLoading, isError } =
 *       useSearchableOptions({
 *         queryKey: 'contract-projects',
 *         endpoint: PROJECTS_ENDPOINTS.LIST,
 *         value: form.getFieldValue('contract_project_id'),
 *         toOption: (p) => ({ value: p.id, label: p.project_name }),
 *       });
 *
 *     <Select showSearch filterOption={false} onSearch={onSearch}
 *             options={options} loading={isLoading} />
 *
 * ⚠️ `filterOption={false}` 是必要的 —— 不關掉的話 AntD 會**再過濾一次**
 * 伺服器回來的結果，等於把伺服器端搜尋的成果又砍掉一半。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

/** 搜尋防抖（毫秒）。300ms 是打字停頓與反應速度的常見折衷。 */
const SEARCH_DEBOUNCE_MS = 300;
/** 每次搜尋回傳的上限。搜尋已經收斂了結果，不需要更多。 */
const SEARCH_LIMIT = 50;

export interface SearchableOption {
  value: string | number;
  label: string;
}

interface Params<T> {
  /** React Query 快取鍵的前綴，各資料源要不同 */
  queryKey: string;
  /** POST 端點 */
  endpoint: string;
  /** 目前已選的值 —— 用來確保它的標籤解析得出來 */
  value?: string | number | null;
  /** 把一筆資料轉成選項 */
  toOption: (row: T) => SearchableOption;
  /** 額外的固定查詢參數（例如 include_converted） */
  extraParams?: Record<string, unknown>;
  /**
   * 依「值」取回那一筆 —— 用來解析已選項目的標籤。
   *
   * ⚠️ **不能用 `search` 代替**：後端的 `search` 比對的是名稱
   * （`project_name.ilike`），而這裡的 value 是 **id**，查不到。
   * 我第一版就是這樣寫的，等於這段防護完全沒有作用。
   * 呼叫端請給 detail 端點（例如 `PROJECTS_ENDPOINTS.DETAIL(id)`）。
   *
   * 不提供時跳過解析 —— 那表示已選值若不在搜尋結果裡會顯示原始值，
   * 呼叫端要自己確保不會發生。
   */
  fetchSelected?: (value: string | number) => Promise<T | null>;
}

type ListResp<T> = {
  items?: T[];
  projects?: T[];
  options?: T[];
  total?: number;
  pagination?: { total?: number };
};

/** 端點的回應形狀不只一種 —— 三種都收，不要在呼叫端各判一次。 */
function pickRows<T>(resp: ListResp<T>): T[] {
  const rows = resp.items ?? resp.projects ?? resp.options ?? [];
  return Array.isArray(rows) ? rows : [];
}

export function useSearchableOptions<T>({
  queryKey, endpoint, value, toOption, extraParams, fetchSelected,
}: Params<T>) {
  const [term, setTerm] = useState('');
  const [debounced, setDebounced] = useState('');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const onSearch = useCallback((next: string) => {
    setTerm(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setDebounced(next), SEARCH_DEBOUNCE_MS);
  }, []);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  // 主查詢：沒打字時給最近的一批（下拉一打開就要有東西，不能是空的）
  const { data: rows = [], isLoading, isError } = useQuery({
    queryKey: [queryKey, 'search', debounced, extraParams],
    queryFn: async () => {
      const resp = await apiClient.post<ListResp<T>>(endpoint, {
        page: 1, limit: SEARCH_LIMIT,
        ...(debounced ? { search: debounced } : {}),
        ...(extraParams ?? {}),
      });
      return pickRows(resp);
    },
    staleTime: 60 * 1000,
    refetchOnWindowFocus: false,
  });

  // 已選值的標籤：它可能不在當前搜尋結果裡。
  // 不補這一段，畫面會顯示原始 id —— 本 repo 記過的「同仁變成代碼」同型。
  const { data: selectedRow } = useQuery({
    queryKey: [queryKey, 'selected', value],
    enabled: !!fetchSelected && value !== undefined && value !== null && value !== '',
    queryFn: async () => (fetchSelected ? fetchSelected(value as string | number) : null),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  const selectedRows = useMemo(() => (selectedRow ? [selectedRow] : []), [selectedRow]);

  const options = useMemo(() => {
    const seen = new Set<string | number>();
    const out: SearchableOption[] = [];
    // 已選的排前面，且不論搜尋結果如何都必須在
    for (const src of [selectedRows, rows]) {
      for (const r of src) {
        const o = toOption(r);
        if (o.value === undefined || o.value === null || seen.has(o.value)) continue;
        seen.add(o.value);
        out.push(o);
      }
    }
    return out;
    // toOption 由呼叫端每次 render 重建，放進相依會造成無限迴圈；
    // 它是純轉換函式，內容不變。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, selectedRows]);

  return { options, onSearch, searchTerm: term, isLoading, isError };
}
