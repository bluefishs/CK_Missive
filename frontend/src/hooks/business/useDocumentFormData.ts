/**
 * 公文建立表單資料載入 Hook
 *
 * 從 useDocumentCreateForm 拆分，負責所有下拉選項與表單資料載入
 *
 * @version 1.0.0
 * @date 2026-03-29
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { App } from 'antd';
import { agenciesApi, AgencyOption } from '../../api/agenciesApi';
import { filesApi } from '../../api/filesApi';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { documentsApi, NextSendNumberResponse } from '../../api/documentsApi';
import type { Project, User, ProjectStaff } from '../../types/api';
import { logger } from '../../utils/logger';
import {
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  type DocumentCreateMode,
  type FileSettings,
} from './useDocumentCreateForm';

export interface UseDocumentFormDataResult {
  loading: boolean;
  agencies: AgencyOption[];
  agenciesLoading: boolean;
  cases: Project[];
  casesLoading: boolean;
  users: User[];
  usersLoading: boolean;
  projectStaffMap: Record<number, ProjectStaff[]>;
  staffLoading: boolean;
  fileSettings: FileSettings;
  nextNumber: NextSendNumberResponse | null;
  nextNumberLoading: boolean;
  fetchProjectStaff: (projectId: number) => Promise<ProjectStaff[]>;
}

export function useDocumentFormData(mode: DocumentCreateMode): UseDocumentFormDataResult {
  const { message } = App.useApp();

  const [loading, setLoading] = useState(true);
  const [agencies, setAgencies] = useState<AgencyOption[]>([]);
  const [agenciesLoading, setAgenciesLoading] = useState(false);
  const [cases, setCases] = useState<Project[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, ProjectStaff[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const projectStaffCacheRef = useRef<Record<number, ProjectStaff[]>>({});

  const [fileSettings, setFileSettings] = useState<FileSettings>({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  const [nextNumber, setNextNumber] = useState<NextSendNumberResponse | null>(null);
  const [nextNumberLoading, setNextNumberLoading] = useState(false);

  const loadNextNumber = useCallback(async () => {
    if (mode !== 'send') return;
    setNextNumberLoading(true);
    try {
      const result = await documentsApi.getNextSendNumber();
      setNextNumber(result);
    } catch (error) {
      logger.error('載入下一個字號失敗:', error);
      message.warning('無法取得下一個發文字號，請手動填寫');
    } finally {
      setNextNumberLoading(false);
    }
  }, [mode, message]);

  const loadAgencies = useCallback(async () => {
    setAgenciesLoading(true);
    try {
      const options = await agenciesApi.getAgencyOptions();
      setAgencies(options);
    } catch (error) {
      logger.error('載入機關選項失敗:', error);
      setAgencies([]);
    } finally {
      setAgenciesLoading(false);
    }
  }, []);

  const loadCases = useCallback(async () => {
    setCasesLoading(true);
    try {
      const data = await apiClient.post<{ projects?: Project[]; items?: Project[] }>(
        API_ENDPOINTS.PROJECTS.LIST,
        { page: 1, limit: 100 }
      );
      const projectsData = data.projects || data.items || [];
      setCases(Array.isArray(projectsData) ? projectsData : []);
    } catch (error) {
      logger.error('載入承攬案件失敗:', error);
      setCases([]);
    } finally {
      setCasesLoading(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const data = await apiClient.post<{ users?: User[]; items?: User[] }>(
        API_ENDPOINTS.USERS.LIST,
        { page: 1, limit: 100 }
      );
      const usersData = data.users || data.items || [];
      setUsers(Array.isArray(usersData) ? usersData : []);
    } catch (error) {
      logger.error('載入使用者失敗:', error);
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  }, []);

  const fetchProjectStaff = useCallback(async (projectId: number): Promise<ProjectStaff[]> => {
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      setProjectStaffMap((prev) => ({ ...prev, [projectId]: cachedData }));
      return cachedData;
    }

    setStaffLoading(true);
    try {
      const data = await apiClient.post<{ staff?: ProjectStaff[] }>(
        `/project-staff/project/${projectId}/list`,
        {}
      );
      const staffData = data.staff || [];
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap((prev) => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      logger.error('載入專案業務同仁失敗:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  }, []);

  const loadFileSettings = useCallback(async () => {
    try {
      const info = await filesApi.getStorageInfo();
      setFileSettings({
        allowedExtensions: info.allowed_extensions,
        maxFileSizeMB: info.max_file_size_mb,
      });
    } catch (error) {
      logger.warn('載入檔案設定失敗，使用預設值:', error);
    }
  }, []);

  useEffect(() => {
    const initialize = async () => {
      setLoading(true);
      const loadTasks = [loadAgencies(), loadCases(), loadUsers(), loadFileSettings()];
      if (mode === 'send') {
        loadTasks.push(loadNextNumber());
      }
      await Promise.all(loadTasks);
      setLoading(false);
    };
    initialize();
  }, [loadAgencies, loadCases, loadUsers, loadFileSettings, loadNextNumber, mode]);

  return {
    loading,
    agencies,
    agenciesLoading,
    cases,
    casesLoading,
    users,
    usersLoading,
    projectStaffMap,
    staffLoading,
    fileSettings,
    nextNumber,
    nextNumberLoading,
    fetchProjectStaff,
  };
}
