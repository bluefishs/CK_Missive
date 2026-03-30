/**
 * 公文建立表單 Hook
 *
 * 組合 useDocumentFormData + useDocumentFileUpload 的 orchestration 層
 * 包含事件處理、工具方法與表單初始化
 *
 * @version 2.0.0
 * @date 2026-03-29
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { FormInstance } from 'antd';
import { App } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../config/queryConfig';
import { documentsApi } from '../../api/documentsApi';
import type { DocumentCreate } from '../../types/api';
import type { AgencyCandidate } from '../../types/ai';
import { logger } from '../../utils/logger';
import { useDocumentFormData } from './useDocumentFormData';
import { useDocumentFileUpload } from './useDocumentFileUpload';

// =============================================================================
// 常數
// =============================================================================

/** 預設公司名稱 */
export const DEFAULT_COMPANY_NAME = '乾坤測繪科技有限公司';

/** 預設檔案驗證常數 */
export const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
  '.zip', '.rar', '.7z', '.txt', '.csv', '.xml', '.json',
  '.dwg', '.dxf', '.shp', '.kml', '.kmz',
];
export const DEFAULT_MAX_FILE_SIZE_MB = 50;

// =============================================================================
// 型別定義
// =============================================================================

export type DocumentCreateMode = 'receive' | 'send';

export interface FileSettings {
  allowedExtensions: string[];
  maxFileSizeMB: number;
}

export interface UseDocumentCreateFormOptions {
  mode: DocumentCreateMode;
  form: FormInstance;
  onSuccess?: () => void;
}

export interface UseDocumentCreateFormResult {
  loading: boolean;
  saving: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;

  agencies: import('../../api/agenciesApi').AgencyOption[];
  agenciesLoading: boolean;
  cases: import('../../types/api').Project[];
  casesLoading: boolean;
  users: import('../../types/api').User[];
  usersLoading: boolean;
  projectStaffMap: Record<number, import('../../types/api').ProjectStaff[]>;
  staffLoading: boolean;
  selectedProjectId: number | null;
  fileSettings: FileSettings;

  fileList: import('antd/es/upload/interface').UploadFile[];
  setFileList: React.Dispatch<React.SetStateAction<import('antd/es/upload/interface').UploadFile[]>>;
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  clearUploadErrors: () => void;

  nextNumber: import('../../api/documentsApi').NextSendNumberResponse | null;
  nextNumberLoading: boolean;

  handleProjectChange: (projectId: number | null | undefined) => Promise<void>;
  handleCategoryChange: (value: string) => void;
  validateFile: (file: File) => { valid: boolean; error?: string };
  handleSave: () => Promise<void>;
  handleCancel: () => void;

  buildAssigneeOptions: () => Array<{ value: string; label: string; key: string }>;
  buildAgencyOptions: (includeCompany?: boolean) => Array<{ value: string; label: string }>;
  agencyCandidates: AgencyCandidate[];
}

// =============================================================================
// Hook 實作
// =============================================================================

export function useDocumentCreateForm(
  options: UseDocumentCreateFormOptions
): UseDocumentCreateFormResult {
  const { mode, form, onSuccess } = options;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  // 組合子 hooks
  const formData = useDocumentFormData(mode);
  const fileUpload = useDocumentFileUpload(formData.fileSettings);

  // 本地狀態
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('info');
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const projectStaffCacheRef = useRef<Record<number, import('../../types/api').ProjectStaff[]>>({});

  // 設定表單初始值
  useEffect(() => {
    if (formData.loading) return;

    if (mode === 'receive') {
      form.setFieldsValue({
        delivery_method: '電子交換',
        category: '收文',
        doc_type: '函',
        receiver: DEFAULT_COMPANY_NAME,
        receive_date: dayjs(),
      });
    } else if (mode === 'send' && formData.nextNumber) {
      form.setFieldsValue({
        doc_number: formData.nextNumber.full_number,
        delivery_method: '電子交換',
        sender: DEFAULT_COMPANY_NAME,
        doc_date: dayjs(),
        send_date: dayjs(),
        doc_type: '函',
      });
    }
  }, [formData.loading, mode, formData.nextNumber, form]);

  // =============================================================================
  // 事件處理
  // =============================================================================

  const handleCategoryChange = useCallback((value: string) => {
    if (mode !== 'receive') return;

    if (value === '收文') {
      form.setFieldsValue({
        receiver: DEFAULT_COMPANY_NAME,
        receive_date: dayjs(),
        sender: undefined,
        send_date: undefined,
      });
    } else if (value === '發文') {
      form.setFieldsValue({
        sender: DEFAULT_COMPANY_NAME,
        send_date: dayjs(),
        receiver: undefined,
        receive_date: undefined,
      });
    }
  }, [mode, form]);

  const handleProjectChange = useCallback(async (projectId: number | null | undefined) => {
    const effectiveProjectId = projectId ?? null;
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      setSelectedProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    const staffList = await formData.fetchProjectStaff(effectiveProjectId);
    if (!staffList || staffList.length === 0) {
      setSelectedProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    setSelectedProjectId(effectiveProjectId);
    projectStaffCacheRef.current[effectiveProjectId] = staffList;

    setTimeout(() => {
      if (staffList.length > 0) {
        const names = staffList.map((s) => s.user_name);
        form.setFieldsValue({ assignee: names });
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  }, [form, formData, message]);

  const handleSave = useCallback(async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = values.assignee.join(', ');
      } else if (values.assignee) {
        assigneeStr = values.assignee;
      }

      const documentData: DocumentCreate = {
        doc_number: values.doc_number,
        doc_type: values.doc_type || '函',
        subject: values.subject,
        sender: values.sender,
        receiver: values.receiver,
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
        content: values.content,
        notes: values.notes,
        ck_note: values.ck_note,
        delivery_method: values.delivery_method || '電子交換',
        contract_project_id: values.contract_project_id,
        assignee: assigneeStr,
        category: mode === 'receive' ? values.category : '發文',
        status: mode === 'receive' ? 'active' : 'sent',
      };

      const newDoc = await documentsApi.createDocument(documentData);

      if (fileUpload.fileList.length > 0) {
        await fileUpload.uploadFiles(newDoc.id, fileUpload.fileList);
      }

      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });

      if (mode === 'receive') {
        message.success('收發文紀錄建立成功！');
      } else {
        message.success('發文建立成功！');
      }

      if (onSuccess) {
        onSuccess();
      } else {
        const targetPath = mode === 'receive' ? '/documents' : '/document-numbers';
        navigate(targetPath);
      }
    } catch (error) {
      logger.error('儲存失敗:', error);
      message.error('儲存失敗，請檢查輸入資料');
    } finally {
      setSaving(false);
    }
  }, [form, mode, fileUpload, queryClient, message, navigate, onSuccess]);

  const handleCancel = useCallback(() => {
    const targetPath = mode === 'receive' ? '/documents' : '/document-numbers';
    navigate(targetPath);
  }, [mode, navigate]);

  // =============================================================================
  // 工具方法
  // =============================================================================

  const buildAssigneeOptions = useCallback((): Array<{ value: string; label: string; key: string }> => {
    const staffList = selectedProjectId ? formData.projectStaffMap[selectedProjectId] : undefined;
    const projectStaffOptions: Array<{ value: string; label: string; key: string }> =
      staffList && staffList.length > 0
        ? staffList
            .filter((staff) => staff.user_name)
            .map((staff) => ({
              value: staff.user_name!,
              label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name!,
              key: `staff-${staff.user_id || staff.id}`,
            }))
        : [];

    const userOptions: Array<{ value: string; label: string; key: string }> = Array.isArray(formData.users)
      ? formData.users
          .filter((user) => user.full_name || user.username)
          .map((user) => ({
            value: user.full_name || user.username,
            label: user.full_name || user.username,
            key: `user-${user.id}`,
          }))
      : [];

    return projectStaffOptions.length > 0 ? projectStaffOptions : userOptions;
  }, [selectedProjectId, formData.projectStaffMap, formData.users]);

  const buildAgencyOptions = useCallback((includeCompany = true) => {
    const options: Array<{ value: string; label: string }> = [];

    if (includeCompany) {
      options.push({
        value: DEFAULT_COMPANY_NAME,
        label: `${DEFAULT_COMPANY_NAME} (本公司)`,
      });
    }

    formData.agencies
      .filter(agency => agency.agency_name !== DEFAULT_COMPANY_NAME)
      .forEach(agency => {
        options.push({
          value: agency.agency_name,
          label: agency.agency_code
            ? `${agency.agency_name} (${agency.agency_code})`
            : agency.agency_name,
        });
      });

    return options;
  }, [formData.agencies]);

  const agencyCandidates = useMemo<AgencyCandidate[]>(() => {
    return formData.agencies.map((a) => ({
      id: a.id,
      name: a.agency_name,
      short_name: a.agency_short_name,
    }));
  }, [formData.agencies]);

  // =============================================================================
  // 返回結果
  // =============================================================================

  return {
    loading: formData.loading,
    saving,
    activeTab,
    setActiveTab,

    agencies: formData.agencies,
    agenciesLoading: formData.agenciesLoading,
    cases: formData.cases,
    casesLoading: formData.casesLoading,
    users: formData.users,
    usersLoading: formData.usersLoading,
    projectStaffMap: formData.projectStaffMap,
    staffLoading: formData.staffLoading,
    selectedProjectId,
    fileSettings: formData.fileSettings,

    fileList: fileUpload.fileList,
    setFileList: fileUpload.setFileList,
    uploading: fileUpload.uploading,
    uploadProgress: fileUpload.uploadProgress,
    uploadErrors: fileUpload.uploadErrors,
    clearUploadErrors: fileUpload.clearUploadErrors,

    nextNumber: formData.nextNumber,
    nextNumberLoading: formData.nextNumberLoading,

    handleProjectChange,
    handleCategoryChange,
    validateFile: fileUpload.validateFile,
    handleSave,
    handleCancel,

    buildAssigneeOptions,
    buildAgencyOptions,
    agencyCandidates,
  };
}

export default useDocumentCreateForm;
