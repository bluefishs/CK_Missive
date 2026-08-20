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

/**
 * 承攬案件下拉選單 Hook
 *
 * staleTime 10 分鐘 — 承攬案件幾乎不變，跨頁面共享快取。
 */
export const useProjectsDropdown = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['projects-dropdown'],
    queryFn: async () => {
      const resp = await apiClient.post<{ projects?: Project[]; items?: Project[] }>(
        PROJECTS_ENDPOINTS.LIST,
        { page: 1, limit: 100 }
      );
      const items = resp.projects || resp.items || [];
      return Array.isArray(items) ? items : [];
    },
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { projects: data ?? [], isLoading };
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
  const { data, isLoading } = useQuery({
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
  return { users: data ?? [], isLoading };
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
  const { data, isLoading } = useQuery({
    queryKey: ['subcontractors-dropdown'],
    queryFn: async () => {
      const { vendorsApi } = await import('../../api/vendorsApi');
      const resp = await vendorsApi.getVendors({ vendor_type: 'subcontractor', limit: 200 });
      return resp.items ?? [];
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  return { subcontractors: data ?? [], isLoading };
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
