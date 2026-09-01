/**
 * 共用下拉選單資料 Hooks
 *
 * 承攬案件、使用者、檔案設定等全域共用下拉資料，
 * 利用 React Query staleTime 跨頁面快取，避免重複請求。
 *
 * @version 1.0.0
 * @date 2026-03-05
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { PROJECTS_ENDPOINTS, USERS_ENDPOINTS, PM_ENDPOINTS } from '../../api/endpoints';
import { filesApi } from '../../api/filesApi';
import type { Project, User } from '../../types/api';
import type { PMCase } from '../../types/pm';

/** 下拉一次抓的上限；超過就分頁續抓，直到湊齊 `total`。 */
const DROPDOWN_PAGE_SIZE = 200;
/** 續抓的頁數上限 —— 防止端點回報異常 total 時無限迴圈。 */
const DROPDOWN_MAX_PAGES = 10;

/**
 * 承攬案件下拉選單 Hook
 *
 * staleTime 10 分鐘 — 承攬案件幾乎不變，跨頁面共享快取。
 *
 * ## ⚠️ 為什麼要續抓，不是把 limit 調大就好（2026-09-01）
 *
 * 原本固定 `limit: 100`，而承攬案件已有 **226 筆** ⇒ **126 筆永遠選不到**，
 * 且 Select 的搜尋是在這 100 筆上做的，所以「搜尋不到」看起來像資料不存在。
 *
 * owner 回報 `/documents/2748` 選不到「…工程開闢分析規劃第二期」：
 * 那筆依建立時間排**第 144 名**。它昨天排第 93、剛好在界內 ——
 * 今天成案 51 筆把它擠了出去。**上限是會被時間追上的，調大只是延後。**
 *
 * 回應本來就帶 `total`，所以「我少拿了幾筆」是元件手上就有的精確答案，
 * 只是先前沒有人問它。現在問，並且補齊。
 */
export const useProjectsDropdown = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['projects-dropdown'],
    queryFn: async () => {
      type Resp = { projects?: Project[]; items?: Project[]; total?: number };
      const fetchPage = async (page: number) => {
        const resp = await apiClient.post<Resp>(
          PROJECTS_ENDPOINTS.LIST,
          { page, limit: DROPDOWN_PAGE_SIZE }
        );
        const items = resp.projects || resp.items || [];
        return { items: Array.isArray(items) ? items : [], total: resp.total ?? 0 };
      };

      const first = await fetchPage(1);
      const all = [...first.items];
      // 端點回報的總數大於已取得 ⇒ 續抓。**不靠 `items.length === limit` 猜**，
      // 那個判準在「總數剛好等於上限」時會多打一次無用的請求。
      for (let page = 2; all.length < first.total && page <= DROPDOWN_MAX_PAGES; page += 1) {
        const next = await fetchPage(page);
        if (next.items.length === 0) break;   // 端點不照 total 給資料時要停，不能空轉
        all.push(...next.items);
      }
      if (all.length < first.total) {
        // 靜默截斷是這個 bug 的本體 —— 真的湊不齊時要留下痕跡，
        // 而不是讓使用者以為那些案件不存在。
        console.warn(
          `[useProjectsDropdown] 承攬案件下拉只取得 ${all.length}/${first.total} 筆，`
          + `已達 ${DROPDOWN_MAX_PAGES} 頁上限 —— 選單會缺項目。`
        );
      }
      return all;
    },
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { projects: data ?? [], isLoading };
};

/**
 * PM 案件（邀標/報價）下拉選單 Hook
 *
 * ## 為什麼不是直接調大 limit（2026-09-01）
 *
 * `PMCaseListRequest.limit` 的驗證上限是 **100**，送 1000 會直接 422。
 * 而 PM 案件已有 **253 筆** ⇒ 一次請求拿不完，只能分頁續抓。
 *
 * ⚠️ 這一頁先前寫的是 `page_size: 200` —— 那個 key **不在 `casesApi.list`
 * 的白名單裡、從來沒有被送出去**，所以實際吃的是後端預設 `limit=20`：
 * **費用報銷的案件下拉一直只有 20 個選項**，而它不會報錯。
 * 兩個病疊在一起（送不出去的參數 ＋ 拿不完的資料），症狀都是「選不到」。
 */
export const usePMCasesDropdown = (opts?: { includeConverted?: boolean }) => {
  const includeConverted = opts?.includeConverted ?? true;
  const { data, isLoading } = useQuery({
    queryKey: ['pm-cases-dropdown', includeConverted],
    queryFn: async () => {
      type Resp = { items?: PMCase[]; pagination?: { total?: number } };
      const PAGE = 100;              // 後端驗證上限，不能再大
      const MAX_PAGES = 20;
      const fetchPage = async (page: number) => {
        const resp = await apiClient.post<Resp>(PM_ENDPOINTS.CASES_LIST, {
          page, limit: PAGE, include_converted: includeConverted,
          sort_by: 'case_code', sort_order: 'desc',
        });
        return { items: resp.items ?? [], total: resp.pagination?.total ?? 0 };
      };
      const first = await fetchPage(1);
      const all = [...first.items];
      for (let page = 2; all.length < first.total && page <= MAX_PAGES; page += 1) {
        const next = await fetchPage(page);
        if (next.items.length === 0) break;
        all.push(...next.items);
      }
      if (all.length < first.total) {
        console.warn(
          `[usePMCasesDropdown] 只取得 ${all.length}/${first.total} 筆 —— 選單會缺項目。`
        );
      }
      return all;
    },
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { pmCases: data ?? [], isLoading };
};

/**
 * 使用者下拉選單 Hook
 *
 * staleTime 10 分鐘。
 *
 * 2026-08-20：資料源由 `users/list`（`require_admin()`）改為
 * `users/assignable`（只要登入即可）。
 *
 * 原本以 `role='user'` 的帳號登入時，這支會 **403 ⇒ 回空陣列**，
 * 於是資產保管人、PM 承辦、公文承辦人這些下拉**對一般同仁一律是空的** ——
 * 而 AntD Select 在 options 空、value 有值時會直接顯示原始數字 id，
 * 也就是 owner 看到的「同仁變成代碼」。這不是那一頁的問題，
 * 是五個人員下拉共用同一條打不通的資料源。
 */
export const useUsersDropdown = () => {
  // isError 要往外給 —— 清單載不到時畫面必須說出來，
  // 否則空的 options 會讓 Select 直接顯示原始數字 id（見 utils/assignableUsers）
  const { data, isLoading, isError } = useQuery({
    queryKey: ['users-dropdown'],
    queryFn: async () => {
      const resp = await apiClient.post<{ users?: User[]; items?: User[] }>(
        USERS_ENDPOINTS.ASSIGNABLE,
        {}
      );
      const items = resp.users || resp.items || [];
      return Array.isArray(items) ? items : [];
    },
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { users: data ?? [], isLoading, isError };
};

/**
 * 委託單位下拉選單 Hook (vendor_type=client)
 */
export const useClientOptions = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['clients-dropdown'],
    queryFn: async () => {
      const { vendorsApi } = await import('../../api/vendorsApi');
      const resp = await vendorsApi.getVendors({ vendor_type: 'client', limit: 100 });
      return resp.items ?? [];
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { clients: data ?? [], isLoading };
};

/**
 * 協力廠商下拉選單 Hook (vendor_type=subcontractor)
 *
 * 2026-08-18 owner：「其協力廠商應對應資料庫提供下拉選單，非自行填列」。
 *
 * 應付填報頁原本是 `<Input placeholder="廠商名稱" />` —— 自行輸入的後果是
 * 同一家廠商會有多種寫法（有無「股份」「有限公司」、全半形），
 * 而 `_resolve_vendor_id` 是靠名稱去配對 `partner_vendors` 的 ——
 * **名字打不一樣就配不到，應付與廠商主檔從此對不起來。**
 *
 * 這是 `useClientOptions`（委託單位）的對稱面 —— 那一支早就有，
 * 而協力廠商這一側一直沒有。實測庫裡有 23 家 subcontractor。
 */
export const useSubcontractorOptions = () => {
  // isError 要往外給 —— 理由同 useUsersDropdown：清單載不到時畫面必須說出來，
  // 否則空的 options 會讓 Select 直接顯示原始 value（2026-08-27 承攬案件協力廠商同型）
  const { data, isLoading, isError } = useQuery({
    queryKey: ['subcontractors-dropdown'],
    queryFn: async () => {
      const { vendorsApi } = await import('../../api/vendorsApi');
      // ⚠️ limit 上限是 100（`schemas/vendor.py: VendorListQuery.limit` 是 `le=100`）。
      //
      // 這裡原本寫 200 —— 2026-08-18「協力廠商改下拉」那次引入的。
      // 實測 `limit=200` 回 **422**（`Input should be less than or equal to 100`），
      // 而 422 在本專案的錯誤分流裡屬「業務錯誤，交給元件自己處理」，
      // 不會被 GlobalApiErrorNotifier 接走 ⇒ useQuery 失敗 ⇒ `?? []` ⇒ **空下拉**。
      //
      // 於是那個功能從上線起就沒有正常運作過，而**沒有任何一層會出聲**：
      // 前端沒報錯、後端回的是規規矩矩的 422、畫面只是「沒有選項」——
      // 而「沒有選項」與「公司沒有協力廠商」長得一模一樣。
      //
      // 現況 23 家，100 夠用。若日後超過 100，這裡會**靜默截斷**而不是報錯 ——
      // 真的要一次載完就得改後端上限或改成分頁載入，不是把數字調大。
      const resp = await vendorsApi.getVendors({ vendor_type: 'subcontractor', limit: 100 });
      return resp.items ?? [];
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { subcontractors: data ?? [], isLoading, isError };
};

/** 作業性質下拉選項 (從 DB 取得) */
export const useCaseNatureOptions = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['case-nature-options'],
    queryFn: async () => {
      const { apiClient } = await import('../../api/client');
      return apiClient.post<{ value: string; label: string }[]>(PM_ENDPOINTS.CASE_NATURE_OPTIONS, {});
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { caseNatureOptions: data ?? [], isLoading };
};

/** 檔案設定預設值 */
const DEFAULT_FILE_SETTINGS = {
  allowedExtensions: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png', '.zip'],
  maxFileSizeMB: 50,
};

/**
 * 檔案上傳設定 Hook
 *
 * staleTime 30 分鐘 — 設定極少變動。
 */
export const useFileSettings = () => {
  const { data } = useQuery({
    queryKey: ['file-settings'],
    queryFn: async () => {
      const info = await filesApi.getStorageInfo();
      return {
        allowedExtensions: info.allowed_extensions,
        maxFileSizeMB: info.max_file_size_mb,
      };
    },
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return data ?? DEFAULT_FILE_SETTINGS;
};
