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
import { PROJECTS_ENDPOINTS, USERS_ENDPOINTS } from '../../api/endpoints';
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
 */
export const useUsersDropdown = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['users-dropdown'],
    queryFn: async () => {
      const resp = await apiClient.post<{ users?: User[]; items?: User[] }>(
        USERS_ENDPOINTS.LIST,
        { page: 1, limit: 100 }
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
