/**
 * useDocumentOperations Hook
 *
 * 管理 DocumentOperations 元件的所有狀態與附件操作邏輯
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { UploadFile } from 'antd/es/upload';
import type { MessageInstance } from 'antd/es/message/interface';
import { Document, DocumentAttachment, Project, User, ProjectStaff } from '../../../types';
import { apiClient } from '../../../api/client';
import { filesApi, type UploadResult } from '../../../api/filesApi';
import { logger } from '../../../utils/logger';
import type {
  OperationMode,
  CriticalChange,
  CriticalChangeModalState,
  DuplicateModalState,
  FileSettings,
  FileValidationResult,
} from './types';
import {
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  MIN_PROGRESS_DISPLAY_MS,
  detectCriticalChanges,
} from './documentOperationsUtils';

// ============================================================================
// Types
// ============================================================================

/** Hook 回傳介面 */
export interface UseDocumentOperationsReturn {
  // 狀態
  loading: boolean;
  calendarLoading: boolean;
  fileList: UploadFile[];
  cases: Project[];
  users: User[];
  casesLoading: boolean;
  usersLoading: boolean;
  existingAttachments: DocumentAttachment[];
  attachmentsLoading: boolean;
  uploadProgress: number;
  uploading: boolean;
  uploadErrors: string[];
  duplicateModal: DuplicateModalState;
  criticalChangeModal: CriticalChangeModalState;
  fileSettings: FileSettings;
  projectStaffMap: Record<number, ProjectStaff[]>;
  staffLoading: boolean;
  selectedProjectId: number | null;

  // 操作方法
  setLoading: (loading: boolean) => void;
  setCalendarLoading: (loading: boolean) => void;
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  setDuplicateModal: React.Dispatch<React.SetStateAction<DuplicateModalState>>;
  setCriticalChangeModal: React.Dispatch<React.SetStateAction<CriticalChangeModalState>>;
  setSelectedProjectId: React.Dispatch<React.SetStateAction<number | null>>;

  // 附件操作
  fetchAttachments: (documentId: number) => Promise<void>;
  uploadFiles: (documentId: number, files: UploadFile[]) => Promise<UploadResult>;
  handleDownload: (attachmentId: number, filename: string) => Promise<void>;
  handleDeleteAttachment: (attachmentId: number) => Promise<void>;
  handlePreviewAttachment: (attachmentId: number, filename: string) => Promise<void>;

  // 重複檔案處理
  checkDuplicateFile: (filename: string) => DocumentAttachment | undefined;
  handleOverwriteFile: () => Promise<void>;
  handleKeepBoth: () => void;
  handleCancelDuplicate: () => void;

  // 專案人員
  fetchProjectStaff: (projectId: number) => Promise<ProjectStaff[]>;

  // 檔案驗證
  validateFile: (file: File) => FileValidationResult;
  handleCheckDuplicate: (file: File) => boolean;

  // 檔案列表操作
  handleFileListChange: (newFileList: UploadFile[]) => void;
  handleRemoveFile: (file: UploadFile) => void;
  handleClearUploadErrors: () => void;

  // 關鍵欄位變更
  detectCriticalChanges: (original: Document | null, updated: Partial<Document>) => CriticalChange[];

  // 操作模式判斷
  isReadOnly: boolean;
  isCreate: boolean;
  isCopy: boolean;
}

/** Hook 參數 */
export interface UseDocumentOperationsProps {
  document: Document | null;
  operation: OperationMode | null;
  visible: boolean;
  message: MessageInstance;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export const useDocumentOperations = ({
  document,
  operation,
  visible,
  message,
}: UseDocumentOperationsProps): UseDocumentOperationsReturn => {
  // 基本載入狀態
  const [loading, setLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);

  // 檔案列表
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  // 選項資料
  const [cases, setCases] = useState<Project[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);

  // 附件相關狀態
  const [existingAttachments, setExistingAttachments] = useState<DocumentAttachment[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);

  // 上傳進度狀態
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploading, setUploading] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // 重複檔案處理狀態
  const [duplicateModal, setDuplicateModal] = useState<DuplicateModalState>({
    visible: false,
    file: null,
    existingAttachment: null,
  });

  // 關鍵欄位變更確認狀態
  const [criticalChangeModal, setCriticalChangeModal] = useState<CriticalChangeModalState>({
    visible: false,
    changes: [],
    pendingData: null,
  });

  // 檔案驗證設定
  const [fileSettings, setFileSettings] = useState<FileSettings>({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  // 專案同仁資料
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, ProjectStaff[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  // 專案同仁快取 ref（避免閉包問題）
  const projectStaffCacheRef = useRef<Record<number, ProjectStaff[]>>({});

  // 操作模式判斷
  const isReadOnly = operation === 'view';
  const isCreate = operation === 'create';
  const isCopy = operation === 'copy';

  // ============================================================================
  // 初始化
  // ============================================================================

  // 載入檔案驗證設定
  useEffect(() => {
    const loadFileSettings = async () => {
      try {
        const info = await filesApi.getStorageInfo();
        setFileSettings({
          allowedExtensions: info.allowed_extensions,
          maxFileSizeMB: info.max_file_size_mb,
        });
      } catch (error) {
        logger.warn('Failed to load file settings, using defaults:', error);
      }
    };
    loadFileSettings();
  }, []);

  // 載入承攬案件與使用者資料
  useEffect(() => {
    const fetchCases = async () => {
      setCasesLoading(true);
      try {
        const data = await apiClient.post<{
          projects?: Project[];
          items?: Project[];
          total?: number;
        }>('/projects/list', { page: 1, limit: 100 });
        const projectsData = data.projects || data.items || [];
        setCases(Array.isArray(projectsData) ? projectsData : []);
      } catch (error) {
        logger.error('Failed to fetch projects:', error);
        setCases([]);
      } finally {
        setCasesLoading(false);
      }
    };

    const fetchUsers = async () => {
      setUsersLoading(true);
      try {
        const data = await apiClient.post<{
          users?: User[];
          items?: User[];
          total?: number;
        }>('/users/list', { page: 1, limit: 100 });
        const usersData = data.users || data.items || [];
        setUsers(Array.isArray(usersData) ? usersData : []);
      } catch (error) {
        logger.error('Failed to fetch users:', error);
        setUsers([]);
      } finally {
        setUsersLoading(false);
      }
    };

    if (visible) {
      fetchCases();
      fetchUsers();
    }
  }, [visible]);

  // ============================================================================
  // 附件操作
  // ============================================================================

  const fetchAttachments = useCallback(async (documentId: number) => {
    setAttachmentsLoading(true);
    try {
      const attachments = await filesApi.getDocumentAttachments(documentId);
      setExistingAttachments(attachments);
    } catch (error) {
      logger.error('Failed to fetch attachments:', error);
      setExistingAttachments([]);
    } finally {
      setAttachmentsLoading(false);
    }
  }, []);

  const uploadFiles = useCallback(async (documentId: number, files: UploadFile[]): Promise<UploadResult> => {
    const emptyResult: UploadResult = { success: true, message: '', files: [], errors: [] };

    if (files.length === 0) return emptyResult;

    const fileObjects = files
      .map(f => f.originFileObj)
      .filter((f): f is NonNullable<typeof f> => f != null) as unknown as File[];

    if (fileObjects.length === 0) {
      return emptyResult;
    }

    const startTime = Date.now();
    setUploading(true);
    setUploadProgress(0);
    setUploadErrors([]);

    try {
      const result = await filesApi.uploadFiles(documentId, fileObjects, {
        onProgress: (percent) => {
          setUploadProgress(percent);
        },
      });

      if (result.errors && result.errors.length > 0) {
        setUploadErrors(result.errors);
      }

      const elapsed = Date.now() - startTime;
      if (elapsed < MIN_PROGRESS_DISPLAY_MS) {
        await new Promise(resolve => setTimeout(resolve, MIN_PROGRESS_DISPLAY_MS - elapsed));
      }

      return result;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '上傳失敗';
      throw new Error(errorMsg);
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDownload = useCallback(async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename || 'download');
    } catch (error) {
      logger.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  }, [message]);

  const handleDeleteAttachment = useCallback(async (attachmentId: number) => {
    try {
      await filesApi.deleteAttachment(attachmentId);
      message.success('附件刪除成功');
      if (document?.id) {
        fetchAttachments(document.id);
      }
    } catch (error) {
      logger.error('Failed to delete attachment:', error);
      message.error('附件刪除失敗');
    }
  }, [document?.id, fetchAttachments, message]);

  const handlePreviewAttachment = useCallback(async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      logger.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  }, [message]);

  // ============================================================================
  // 重複檔案處理
  // ============================================================================

  const checkDuplicateFile = useCallback((filename: string): DocumentAttachment | undefined => {
    return existingAttachments.find(
      (att) => (att.original_filename || att.filename)?.toLowerCase() === filename.toLowerCase()
    );
  }, [existingAttachments]);

  const handleOverwriteFile = useCallback(async () => {
    if (!duplicateModal.file || !duplicateModal.existingAttachment) return;

    try {
      await filesApi.deleteAttachment(duplicateModal.existingAttachment.id);
      message.success(`已刪除舊檔案：${duplicateModal.existingAttachment.original_filename || duplicateModal.existingAttachment.filename}`);

      const newFile: UploadFile = {
        uid: `${Date.now()}-${duplicateModal.file.name}`,
        name: duplicateModal.file.name,
        status: 'done' as const,
        originFileObj: duplicateModal.file as UploadFile['originFileObj'],
        size: duplicateModal.file.size,
      };
      setFileList((prev) => [...prev, newFile]);

      if (document?.id) {
        fetchAttachments(document.id);
      }
    } catch (error) {
      logger.error('刪除舊檔案失敗:', error);
      message.error('刪除舊檔案失敗');
    } finally {
      setDuplicateModal({ visible: false, file: null, existingAttachment: null });
    }
  }, [duplicateModal, document?.id, fetchAttachments, message]);

  const handleKeepBoth = useCallback(() => {
    if (!duplicateModal.file) return;

    const newFile: UploadFile = {
      uid: `${Date.now()}-${duplicateModal.file.name}`,
      name: duplicateModal.file.name,
      status: 'done' as const,
      originFileObj: duplicateModal.file as UploadFile['originFileObj'],
      size: duplicateModal.file.size,
    };
    setFileList((prev) => [...prev, newFile]);
    setDuplicateModal({ visible: false, file: null, existingAttachment: null });
    message.info('檔案已加入待上傳列表（將以不同名稱儲存）');
  }, [duplicateModal.file, message]);

  const handleCancelDuplicate = useCallback(() => {
    setDuplicateModal({ visible: false, file: null, existingAttachment: null });
  }, []);

  // ============================================================================
  // 專案人員
  // ============================================================================

  const fetchProjectStaff = useCallback(async (projectId: number): Promise<ProjectStaff[]> => {
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      setProjectStaffMap(prev => ({ ...prev, [projectId]: cachedData }));
      return cachedData;
    }

    setStaffLoading(true);
    try {
      const data = await apiClient.post<{
        staff?: ProjectStaff[];
        total?: number;
      }>(`/project-staff/project/${projectId}/list`, {});
      const staffData = data.staff || [];
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      logger.error('Failed to fetch project staff:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  }, []);

  // ============================================================================
  // 檔案驗證
  // ============================================================================

  const validateFile = useCallback((file: File): FileValidationResult => {
    const { allowedExtensions, maxFileSizeMB } = fileSettings;

    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');
    if (!allowedExtensions.includes(ext)) {
      const errorMsg = `不支援 ${ext} 檔案格式。允許的格式: ${allowedExtensions.slice(0, 5).join(', ')} 等`;
      message.error(errorMsg);
      return { valid: false, error: errorMsg };
    }

    const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      const errorMsg = `檔案 "${file.name}" 大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`;
      message.error(errorMsg);
      return { valid: false, error: errorMsg };
    }

    return { valid: true };
  }, [fileSettings, message]);

  const handleCheckDuplicate = useCallback((file: File): boolean => {
    if (isCreate || isCopy) return false;

    const existingFile = checkDuplicateFile(file.name);
    if (existingFile) {
      setDuplicateModal({
        visible: true,
        file: file,
        existingAttachment: existingFile,
      });
      return true;
    }
    return false;
  }, [isCreate, isCopy, checkDuplicateFile]);

  // ============================================================================
  // 檔案列表操作
  // ============================================================================

  const handleFileListChange = useCallback((newFileList: UploadFile[]) => {
    setFileList(newFileList);
  }, []);

  const handleRemoveFile = useCallback((file: UploadFile) => {
    setFileList(prev => prev.filter(item => item.uid !== file.uid));
  }, []);

  const handleClearUploadErrors = useCallback(() => {
    setUploadErrors([]);
  }, []);

  // ============================================================================
  // 關鍵欄位變更檢測 (委派給 utils)
  // ============================================================================

  const detectChanges = useCallback((original: Document | null, updated: Partial<Document>): CriticalChange[] => {
    return detectCriticalChanges(original as unknown as Record<string, unknown>, updated as unknown as Record<string, unknown>);
  }, []);

  return {
    // 狀態
    loading,
    calendarLoading,
    fileList,
    cases,
    users,
    casesLoading,
    usersLoading,
    existingAttachments,
    attachmentsLoading,
    uploadProgress,
    uploading,
    uploadErrors,
    duplicateModal,
    criticalChangeModal,
    fileSettings,
    projectStaffMap,
    staffLoading,
    selectedProjectId,

    // 狀態設定器
    setLoading,
    setCalendarLoading,
    setFileList,
    setDuplicateModal,
    setCriticalChangeModal,
    setSelectedProjectId,

    // 附件操作
    fetchAttachments,
    uploadFiles,
    handleDownload,
    handleDeleteAttachment,
    handlePreviewAttachment,

    // 重複檔案處理
    checkDuplicateFile,
    handleOverwriteFile,
    handleKeepBoth,
    handleCancelDuplicate,

    // 專案人員
    fetchProjectStaff,

    // 檔案驗證
    validateFile,
    handleCheckDuplicate,

    // 檔案列表操作
    handleFileListChange,
    handleRemoveFile,
    handleClearUploadErrors,

    // 關鍵欄位變更
    detectCriticalChanges: detectChanges,

    // 操作模式判斷
    isReadOnly,
    isCreate,
    isCopy,
  };
};

export default useDocumentOperations;
