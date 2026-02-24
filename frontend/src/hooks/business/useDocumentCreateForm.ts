/**
 * 公文建立表單 Hook
 *
 * 抽取 ReceiveDocumentCreatePage 和 SendDocumentCreatePage 的共用邏輯
 * 包含狀態管理、資料載入、事件處理等功能
 *
 * @version 1.0.0
 * @date 2026-01-28
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { FormInstance } from 'antd';
import { App } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../config/queryConfig';
import { documentsApi, NextSendNumberResponse } from '../../api/documentsApi';
import { agenciesApi, AgencyOption } from '../../api/agenciesApi';
import { filesApi } from '../../api/filesApi';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { UploadFile } from 'antd/es/upload/interface';
import type { Project, User, ProjectStaff, DocumentCreate } from '../../types/api';
import { logger } from '../../utils/logger';

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
  /** 建立模式：收文或發文 */
  mode: DocumentCreateMode;
  /** Antd Form 實例 */
  form: FormInstance;
  /** 成功後回呼 */
  onSuccess?: () => void;
}

export interface UseDocumentCreateFormResult {
  // =============================================================================
  // 基本狀態
  // =============================================================================
  /** 初始載入中 */
  loading: boolean;
  /** 儲存中 */
  saving: boolean;
  /** 當前 Tab */
  activeTab: string;
  /** 設定當前 Tab */
  setActiveTab: (tab: string) => void;

  // =============================================================================
  // 資料選項
  // =============================================================================
  /** 機關選項 */
  agencies: AgencyOption[];
  /** 機關載入中 */
  agenciesLoading: boolean;
  /** 承攬案件 */
  cases: Project[];
  /** 案件載入中 */
  casesLoading: boolean;
  /** 使用者列表 */
  users: User[];
  /** 使用者載入中 */
  usersLoading: boolean;
  /** 專案人員對照表 */
  projectStaffMap: Record<number, ProjectStaff[]>;
  /** 人員載入中 */
  staffLoading: boolean;
  /** 已選專案 ID */
  selectedProjectId: number | null;
  /** 檔案設定 */
  fileSettings: FileSettings;

  // =============================================================================
  // 附件相關
  // =============================================================================
  /** 待上傳檔案列表 */
  fileList: UploadFile[];
  /** 設定檔案列表 */
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  /** 上傳中 */
  uploading: boolean;
  /** 上傳進度 */
  uploadProgress: number;
  /** 上傳錯誤 */
  uploadErrors: string[];
  /** 清除上傳錯誤 */
  clearUploadErrors: () => void;

  // =============================================================================
  // 發文模式專用
  // =============================================================================
  /** 下一個發文字號（僅 send 模式） */
  nextNumber: NextSendNumberResponse | null;
  /** 字號載入中（僅 send 模式） */
  nextNumberLoading: boolean;

  // =============================================================================
  // 事件處理
  // =============================================================================
  /** 專案變更處理 */
  handleProjectChange: (projectId: number | null | undefined) => Promise<void>;
  /** 類別變更處理（僅 receive 模式） */
  handleCategoryChange: (value: string) => void;
  /** 檔案驗證 */
  validateFile: (file: File) => { valid: boolean; error?: string };
  /** 儲存 */
  handleSave: () => Promise<void>;
  /** 取消 */
  handleCancel: () => void;

  // =============================================================================
  // 工具方法
  // =============================================================================
  /** 建立業務同仁選項 */
  buildAssigneeOptions: () => Array<{ value: string; label: string; key: string }>;
  /** 建立機關選項（含本公司置頂） */
  buildAgencyOptions: (includeCompany?: boolean) => Array<{ value: string; label: string }>;
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

  // =============================================================================
  // 基本狀態
  // =============================================================================
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('info');

  // =============================================================================
  // 資料選項狀態
  // =============================================================================
  const [agencies, setAgencies] = useState<AgencyOption[]>([]);
  const [agenciesLoading, setAgenciesLoading] = useState(false);
  const [cases, setCases] = useState<Project[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, ProjectStaff[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const projectStaffCacheRef = useRef<Record<number, ProjectStaff[]>>({});

  // =============================================================================
  // 檔案設定
  // =============================================================================
  const [fileSettings, setFileSettings] = useState<FileSettings>({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  // =============================================================================
  // 附件狀態
  // =============================================================================
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // =============================================================================
  // 發文模式專用狀態
  // =============================================================================
  const [nextNumber, setNextNumber] = useState<NextSendNumberResponse | null>(null);
  const [nextNumberLoading, setNextNumberLoading] = useState(false);

  // =============================================================================
  // 資料載入函數
  // =============================================================================

  /** 載入下一個發文字號（僅 send 模式） */
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

  /** 載入機關選項 */
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

  /** 載入承攬案件選項 */
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

  /** 載入使用者列表 */
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

  /** 載入專案業務同仁 */
  const fetchProjectStaff = useCallback(async (projectId: number): Promise<ProjectStaff[]> => {
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      setProjectStaffMap(prev => ({ ...prev, [projectId]: cachedData }));
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
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      logger.error('載入專案業務同仁失敗:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  }, []);

  /** 載入檔案設定 */
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

  // =============================================================================
  // 初始化
  // =============================================================================

  useEffect(() => {
    const initialize = async () => {
      setLoading(true);

      const loadTasks = [
        loadAgencies(),
        loadCases(),
        loadUsers(),
        loadFileSettings(),
      ];

      // 發文模式需載入下一個字號
      if (mode === 'send') {
        loadTasks.push(loadNextNumber());
      }

      await Promise.all(loadTasks);
      setLoading(false);
    };
    initialize();
  }, [loadAgencies, loadCases, loadUsers, loadFileSettings, loadNextNumber, mode]);

  // 設定表單初始值
  useEffect(() => {
    if (loading) return;

    if (mode === 'receive') {
      form.setFieldsValue({
        delivery_method: '電子交換',
        category: '收文',
        doc_type: '函',
        receiver: DEFAULT_COMPANY_NAME,
        receive_date: dayjs(),
      });
    } else if (mode === 'send' && nextNumber) {
      form.setFieldsValue({
        doc_number: nextNumber.full_number,
        delivery_method: '電子交換',
        sender: DEFAULT_COMPANY_NAME,
        doc_date: dayjs(),
        doc_type: '函',
      });
    }
  }, [loading, mode, nextNumber, form]);

  // =============================================================================
  // 事件處理
  // =============================================================================

  /** 類別變更處理（收文模式專用） */
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

  /** 專案變更處理 */
  const handleProjectChange = useCallback(async (projectId: number | null | undefined) => {
    const effectiveProjectId = projectId ?? null;
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      setSelectedProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    const staffList = await fetchProjectStaff(effectiveProjectId);
    if (!staffList || staffList.length === 0) {
      setSelectedProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    setSelectedProjectId(effectiveProjectId);

    // 自動填入業務同仁
    setTimeout(() => {
      const currentStaff = projectStaffCacheRef.current[effectiveProjectId];
      if (currentStaff && currentStaff.length > 0) {
        const names = currentStaff.map((s) => s.user_name);
        form.setFieldsValue({ assignee: names });
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  }, [form, fetchProjectStaff, message]);

  /** 檔案驗證 */
  const validateFile = useCallback((file: File): { valid: boolean; error?: string } => {
    const { allowedExtensions, maxFileSizeMB } = fileSettings;
    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');

    if (!allowedExtensions.includes(ext)) {
      return {
        valid: false,
        error: `不支援 ${ext} 檔案格式`,
      };
    }

    const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `檔案大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`,
      };
    }

    return { valid: true };
  }, [fileSettings]);

  /** 上傳檔案 */
  const uploadFiles = useCallback(async (documentId: number, files: UploadFile[]): Promise<void> => {
    if (files.length === 0) return;

    const fileObjects: File[] = files
      .map(f => f.originFileObj as File | undefined)
      .filter((f): f is File => f !== undefined);

    if (fileObjects.length === 0) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadErrors([]);

    try {
      const result = await filesApi.uploadFiles(documentId, fileObjects, {
        onProgress: (percent) => setUploadProgress(percent),
      });

      if (result.errors && result.errors.length > 0) {
        setUploadErrors(result.errors);
      }

      const successCount = result.files?.length || 0;
      const errorCount = result.errors?.length || 0;

      if (successCount > 0 && errorCount === 0) {
        message.success(`附件上傳成功（共 ${successCount} 個檔案）`);
      } else if (successCount > 0 && errorCount > 0) {
        message.warning(`部分附件上傳成功（成功 ${successCount} 個，失敗 ${errorCount} 個）`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '上傳失敗';
      message.error(`附件上傳失敗: ${errorMsg}`);
      throw error;
    } finally {
      setUploading(false);
    }
  }, [message]);

  /** 儲存 */
  const handleSave = useCallback(async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

      // 處理 assignee：陣列轉逗號分隔字串
      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = values.assignee.join(', ');
      } else if (values.assignee) {
        assigneeStr = values.assignee;
      }

      // 準備資料
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
        contract_project_id: values.contract_project_id,
        assignee: assigneeStr,
        category: mode === 'receive' ? values.category : '發文',
        status: mode === 'receive' ? 'active' : 'sent',
      };

      // 建立公文
      const newDoc = await documentsApi.createDocument(documentData);

      // 上傳附件
      if (fileList.length > 0) {
        await uploadFiles(newDoc.id, fileList);
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
  }, [form, mode, fileList, uploadFiles, queryClient, message, navigate, onSuccess]);

  /** 取消 */
  const handleCancel = useCallback(() => {
    const targetPath = mode === 'receive' ? '/documents' : '/document-numbers';
    navigate(targetPath);
  }, [mode, navigate]);

  /** 清除上傳錯誤 */
  const clearUploadErrors = useCallback(() => {
    setUploadErrors([]);
  }, []);

  // =============================================================================
  // 工具方法
  // =============================================================================

  /** 建立業務同仁選項 */
  const buildAssigneeOptions = useCallback((): Array<{ value: string; label: string; key: string }> => {
    const staffList = selectedProjectId ? projectStaffMap[selectedProjectId] : undefined;
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

    const userOptions: Array<{ value: string; label: string; key: string }> = Array.isArray(users)
      ? users
          .filter((user) => user.full_name || user.username)
          .map((user) => ({
            value: user.full_name || user.username,
            label: user.full_name || user.username,
            key: `user-${user.id}`,
          }))
      : [];

    return projectStaffOptions.length > 0 ? projectStaffOptions : userOptions;
  }, [selectedProjectId, projectStaffMap, users]);

  /** 建立機關選項（含本公司置頂） */
  const buildAgencyOptions = useCallback((includeCompany = true) => {
    const options: Array<{ value: string; label: string }> = [];

    if (includeCompany) {
      options.push({
        value: DEFAULT_COMPANY_NAME,
        label: `${DEFAULT_COMPANY_NAME} (本公司)`,
      });
    }

    agencies
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
  }, [agencies]);

  // =============================================================================
  // 返回結果
  // =============================================================================

  return {
    // 基本狀態
    loading,
    saving,
    activeTab,
    setActiveTab,

    // 資料選項
    agencies,
    agenciesLoading,
    cases,
    casesLoading,
    users,
    usersLoading,
    projectStaffMap,
    staffLoading,
    selectedProjectId,
    fileSettings,

    // 附件
    fileList,
    setFileList,
    uploading,
    uploadProgress,
    uploadErrors,
    clearUploadErrors,

    // 發文專用
    nextNumber,
    nextNumberLoading,

    // 事件處理
    handleProjectChange,
    handleCategoryChange,
    validateFile,
    handleSave,
    handleCancel,

    // 工具方法
    buildAssigneeOptions,
    buildAgencyOptions,
  };
}

export default useDocumentCreateForm;
