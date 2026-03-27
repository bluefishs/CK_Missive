/**
 * useDocumentProjectStaff - 公文詳情頁的專案人員管理 Hook
 *
 * 從 useDocumentDetail 提取，封裝 staff loading、project change、assignee 解析。
 *
 * @version 1.0.0
 * @date 2026-03-27
 */

import { useState, useRef, useCallback } from 'react';
import type { FormInstance } from 'antd';
import { apiClient } from '../../../api/client';
import { API_ENDPOINTS } from '../../../api/endpoints';
import type { ProjectStaff } from '../../../types/api';
import { logger } from '../../../utils/logger';

export interface UseDocumentProjectStaffReturn {
  projectStaffMap: Record<number, ProjectStaff[]>;
  staffLoading: boolean;
  selectedContractProjectId: number | null;
  currentAssigneeValues: string[];
  setCurrentAssigneeValues: (values: string[]) => void;
  setSelectedContractProjectId: (id: number | null) => void;
  fetchProjectStaff: (projectId: number) => Promise<ProjectStaff[]>;
  handleProjectChange: (projectId: number | null | undefined, form: FormInstance, message: { info: (msg: string) => void; success: (msg: string) => void }) => Promise<void>;
  parseAssignee: (rawAssignee: unknown) => string[];
}

export function useDocumentProjectStaff(): UseDocumentProjectStaffReturn {
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, ProjectStaff[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedContractProjectId, setSelectedContractProjectId] = useState<number | null>(null);
  const [currentAssigneeValues, setCurrentAssigneeValues] = useState<string[]>([]);
  const projectStaffCacheRef = useRef<Record<number, ProjectStaff[]>>({});

  const fetchProjectStaff = useCallback(async (projectId: number): Promise<ProjectStaff[]> => {
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      setProjectStaffMap(prev => ({ ...prev, [projectId]: cachedData }));
      return cachedData;
    }
    setStaffLoading(true);
    try {
      const data = await apiClient.post<{ staff?: ProjectStaff[] }>(
        API_ENDPOINTS.PROJECT_STAFF.PROJECT_LIST(projectId),
        {}
      );
      const staffData = data.staff || [];
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      logger.error('載入專案業務同仁失敗:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  }, []);

  const handleProjectChange = useCallback(async (
    projectId: number | null | undefined,
    form: FormInstance,
    message: { info: (msg: string) => void; success: (msg: string) => void },
  ) => {
    const effectiveProjectId = projectId ?? null;
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      setSelectedContractProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    const staffList = await fetchProjectStaff(effectiveProjectId);
    if (!staffList || staffList.length === 0) {
      setSelectedContractProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    setSelectedContractProjectId(effectiveProjectId);

    setTimeout(() => {
      const currentStaff = projectStaffCacheRef.current[effectiveProjectId];
      if (currentStaff && currentStaff.length > 0) {
        const names = currentStaff.map((s: ProjectStaff) => s.user_name).filter((name): name is string => !!name);
        form.setFieldsValue({ assignee: names });
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  }, [fetchProjectStaff]);

  const parseAssignee = useCallback((rawAssignee: unknown): string[] => {
    if (!rawAssignee) return [];
    if (Array.isArray(rawAssignee)) return rawAssignee;
    if (typeof rawAssignee === 'string') {
      return rawAssignee.split(',').map((s: string) => s.trim()).filter(Boolean);
    }
    return [];
  }, []);

  return {
    projectStaffMap,
    staffLoading,
    selectedContractProjectId,
    currentAssigneeValues,
    setCurrentAssigneeValues,
    setSelectedContractProjectId,
    fetchProjectStaff,
    handleProjectChange,
    parseAssignee,
  };
}
