import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  App,
  Upload,
  Card,
  Space,
  Row,
  Col,
  Tag,
  Tabs,
  List,
  Popconfirm,
  Spin,
  Empty,
  Progress,
  Alert,
} from 'antd';
import type { UploadFile, UploadChangeParam } from 'antd/es/upload';
import {
  InboxOutlined,
  FileTextOutlined,
  SendOutlined,
  CopyOutlined,
  CalendarOutlined,
  DownloadOutlined,
  DeleteOutlined,
  PaperClipOutlined,
  CloudUploadOutlined,
  FileOutlined,
  LoadingOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileImageOutlined,
} from '@ant-design/icons';
import { Document, Project, User, DocumentAttachment, ProjectStaff } from '../../types';
import dayjs from 'dayjs';
import { calendarIntegrationService } from '../../services/calendarIntegrationService';
import { apiClient } from '../../api/client';
import { filesApi } from '../../api/filesApi';
import { logger } from '../../utils/logger';
// 子組件與共用型別
import {
  CriticalChangeConfirmModal,
  DuplicateFileModal,
  CRITICAL_FIELDS,
  type CriticalFieldKey,
  type CriticalChange,
  type CriticalChangeModalState,
  type DuplicateModalState,
} from './operations';

const { TextArea } = Input;
const { Option } = Select;
const { Dragger } = Upload;

// ============================================================================
// 預設檔案驗證常數（作為後備，實際值從後端載入）
// ============================================================================
const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
  '.zip', '.rar', '.7z', '.txt', '.csv', '.xml', '.json',
  '.dwg', '.dxf', '.shp', '.kml', '.kmz',
];
const DEFAULT_MAX_FILE_SIZE_MB = 50;

// 關鍵欄位定義已移至 ./operations/types.ts (SSOT)

/**
 * 檢測關鍵欄位變更
 */
const detectCriticalChanges = (
  original: Document | null,
  updated: Partial<Document>
): CriticalChange[] => {
  if (!original) return [];

  const changes: CriticalChange[] = [];

  (Object.keys(CRITICAL_FIELDS) as CriticalFieldKey[]).forEach((field) => {
    const oldVal = String(original[field] || '');
    const newVal = String(updated[field] || '');

    if (oldVal !== newVal && updated[field] !== undefined) {
      changes.push({
        field,
        label: CRITICAL_FIELDS[field].label,
        icon: CRITICAL_FIELDS[field].icon,
        oldValue: oldVal || '(空白)',
        newValue: newVal || '(空白)',
      });
    }
  });

  return changes;
};

interface DocumentOperationsProps {
  document: Document | null;
  operation: 'view' | 'edit' | 'create' | 'copy' | null;
  visible: boolean;
  onClose: () => void;
  onSave: (document: Partial<Document>) => Promise<Document | void>;
}

export const DocumentOperations: React.FC<DocumentOperationsProps> = ({
  document,
  operation,
  visible,
  onClose,
  onSave,
}) => {
  // Force refresh timestamp: 2025-09-16-13:01
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
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
  const [duplicateModal, setDuplicateModal] = useState<{
    visible: boolean;
    file: File | null;
    existingAttachment: DocumentAttachment | null;
  }>({ visible: false, file: null, existingAttachment: null });
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  // 關鍵欄位變更確認狀態
  const [criticalChangeModal, setCriticalChangeModal] = useState<{
    visible: boolean;
    changes: CriticalChange[];
    pendingData: Partial<Document> | null;
  }>({ visible: false, changes: [], pendingData: null });
  // 檔案驗證設定（從後端動態載入）
  const [fileSettings, setFileSettings] = useState<{
    allowedExtensions: string[];
    maxFileSizeMB: number;
  }>({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  const isReadOnly = operation === 'view';
  const isCreate = operation === 'create';
  const isCopy = operation === 'copy';

  // 專案同仁資料 (依專案 ID 快取)
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, ProjectStaff[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  // 專案同仁快取 ref（避免閉包問題）
  const projectStaffCacheRef = React.useRef<Record<number, ProjectStaff[]>>({});

  // 根據專案 ID 取得業務同仁列表
  const fetchProjectStaff = async (projectId: number): Promise<ProjectStaff[]> => {
    // 檢查快取 (使用 ref 避免閉包問題)
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      // 確保 state 也有資料（觸發 re-render）
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
      // 同時更新 ref 和 state
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      logger.error('Failed to fetch project staff:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  };

  // 選擇專案後自動填入所有業務同仁
  const handleProjectChange = async (projectId: number | null | undefined) => {
    logger.debug('[handleProjectChange] 選擇專案:', projectId);

    // 處理 undefined (allowClear 時會傳入 undefined)
    const effectiveProjectId = projectId ?? null;

    // 先更新承攬案件欄位
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      // 清除專案時，也清除業務同仁欄位
      setSelectedProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    // 取得專案業務同仁資料
    const staffList = await fetchProjectStaff(effectiveProjectId);
    logger.debug('[handleProjectChange] 取得業務同仁:', staffList);

    // 直接填入所有業務同仁（不等待 state 更新）
    if (!staffList || staffList.length === 0) {
      setSelectedProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    const allStaffNames = staffList.map((s) => s.user_name);
    logger.debug('[handleProjectChange] 準備填入:', allStaffNames);

    // 同時更新 selectedProjectId 和 form 值
    // 使用函數式更新確保順序正確
    setSelectedProjectId(effectiveProjectId);

    // 延遲設定 form 值，等待 projectStaffMap 更新後 options 會包含正確選項
    setTimeout(() => {
      // 再次檢查確保有資料
      const currentStaff = projectStaffCacheRef.current[effectiveProjectId];
      if (currentStaff && currentStaff.length > 0) {
        const names = currentStaff.map((s) => s.user_name);
        form.setFieldsValue({ assignee: names });
        logger.debug('[handleProjectChange] 已填入業務同仁:', names);
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  };

  // 載入檔案驗證設定（從後端）
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

  // 取得公文附件列表 - 使用 filesApi
  const fetchAttachments = async (documentId: number) => {
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
  };

  // 上傳檔案 - 使用 filesApi（含進度追蹤）
  // 最小顯示時間確保用戶能看到進度條
  const MIN_PROGRESS_DISPLAY_MS = 800;

  const uploadFiles = async (documentId: number, files: UploadFile[]) => {
    if (files.length === 0) return { success: true, files: [], errors: [] as string[] };

    // 提取原始 File 物件
    const fileObjects = files
      .map(f => f.originFileObj)
      .filter((f): f is NonNullable<typeof f> => f != null) as File[];

    if (fileObjects.length === 0) {
      return { success: true, files: [], errors: [] };
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

      // 處理部分失敗
      if (result.errors && result.errors.length > 0) {
        setUploadErrors(result.errors);
      }

      // 確保進度條至少顯示一段時間，讓用戶能看到
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
  };

  // 下載附件 - 使用 filesApi
  const handleDownload = async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename || 'download');
    } catch (error) {
      logger.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  };

  // 刪除附件 - 使用 filesApi
  const handleDeleteAttachment = async (attachmentId: number) => {
    try {
      await filesApi.deleteAttachment(attachmentId);
      message.success('附件刪除成功');
      // 重新載入附件列表
      if (document?.id) {
        fetchAttachments(document.id);
      }
    } catch (error) {
      logger.error('Failed to delete attachment:', error);
      message.error('附件刪除失敗');
    }
  };

  // 判斷是否可預覽的檔案類型
  const isPreviewable = (contentType?: string, filename?: string): boolean => {
    if (contentType) {
      if (contentType.startsWith('image/') ||
          contentType === 'application/pdf' ||
          contentType.startsWith('text/')) {
        return true;
      }
    }
    // 也根據副檔名判斷
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  // 預覽附件 - 在新視窗開啟
  const handlePreviewAttachment = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      // 延遲釋放 URL，讓新視窗有時間載入
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      logger.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  // 取得檔案圖示
  const getFileIcon = (contentType?: string, filename?: string) => {
    const ext = filename?.toLowerCase().split('.').pop();
    if (contentType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '')) {
      return <FileImageOutlined style={{ fontSize: 20, color: '#52c41a' }} />;
    }
    if (contentType === 'application/pdf' || ext === 'pdf') {
      return <FilePdfOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />;
    }
    return <PaperClipOutlined style={{ fontSize: 20, color: '#1890ff' }} />;
  };

  // 檢查是否有重複檔名
  const checkDuplicateFile = (filename: string): DocumentAttachment | undefined => {
    return existingAttachments.find(
      (att) => (att.original_filename || att.filename)?.toLowerCase() === filename.toLowerCase()
    );
  };

  // 處理重複檔案 - 覆蓋（刪除舊檔案）
  const handleOverwriteFile = async () => {
    if (!duplicateModal.file || !duplicateModal.existingAttachment) return;

    try {
      // 先刪除舊檔案
      await filesApi.deleteAttachment(duplicateModal.existingAttachment.id);
      message.success(`已刪除舊檔案：${duplicateModal.existingAttachment.original_filename || duplicateModal.existingAttachment.filename}`);

      // 將檔案加入待上傳列表
      const newFile: UploadFile = {
        uid: `${Date.now()}-${duplicateModal.file.name}`,
        name: duplicateModal.file.name,
        status: 'done' as const,
        originFileObj: duplicateModal.file as UploadFile['originFileObj'],
        size: duplicateModal.file.size,
      };
      setFileList((prev) => [...prev, newFile]);

      // 刷新附件列表
      if (document?.id) {
        fetchAttachments(document.id);
      }
    } catch (error) {
      logger.error('刪除舊檔案失敗:', error);
      message.error('刪除舊檔案失敗');
    } finally {
      setDuplicateModal({ visible: false, file: null, existingAttachment: null });
    }
  };

  // 處理重複檔案 - 同時保留
  const handleKeepBoth = () => {
    if (!duplicateModal.file) return;

    // 直接加入待上傳列表（後端會自動加 UUID 前綴）
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
  };

  // 處理重複檔案 - 取消
  const handleCancelDuplicate = () => {
    setDuplicateModal({ visible: false, file: null, existingAttachment: null });
  };

  // 載入承攬案件數據
  useEffect(() => {
    const fetchCases = async () => {
      setCasesLoading(true);
      try {
        // POST-only 資安機制 (使用 apiClient 確保正確的 base URL)
        const data = await apiClient.post<{
          projects?: Project[];
          items?: Project[];
          total?: number;
        }>('/projects/list', { page: 1, limit: 100 });
        // 適應新的API回應格式
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
        // POST-only 資安機制 (使用 apiClient 確保正確的 base URL)
        const data = await apiClient.post<{
          users?: User[];
          items?: User[];
          total?: number;
        }>('/users/list', { page: 1, limit: 100 });
        // 處理可能的不同回應格式
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

  React.useEffect(() => {
    if (visible && document) {
      // 處理 assignee 欄位：字串轉陣列（支援逗號分隔）
      let assigneeArray: string[] = [];
      const rawAssignee = document.assignee;
      if (rawAssignee) {
        if (Array.isArray(rawAssignee)) {
          assigneeArray = rawAssignee;
        } else if (typeof rawAssignee === 'string') {
          assigneeArray = rawAssignee.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
      }

      const formValues = {
        ...document,
        doc_date: document.doc_date ? dayjs(document.doc_date) : null,
        receive_date: document.receive_date ? dayjs(document.receive_date) : null,
        send_date: document.send_date ? dayjs(document.send_date) : null,
        assignee: assigneeArray,
      };

      if (isCopy) {
        // 複製時清除ID和重複欄位
        const formValuesWithId = formValues as { id?: number };
        delete formValuesWithId.id;
        formValues.doc_number = `${document.doc_number}-副本`;
      }

      form.setFieldsValue(formValues);

      // 設定選中的專案 ID 並載入該專案的業務同仁
      const projectId = document.contract_project_id;
      if (projectId) {
        setSelectedProjectId(projectId);
        // 載入專案業務同仁，如果公文沒有指定 assignee 則自動填入
        fetchProjectStaff(projectId).then(staffList => {
          if (staffList && staffList.length > 0 && assigneeArray.length === 0) {
            // 公文沒有指定業務同仁，自動從專案填入
            const allStaffNames = staffList.map((s) => s.user_name);
            setTimeout(() => {
              form.setFieldsValue({ assignee: allStaffNames });
              logger.debug('[載入公文] 自動填入專案業務同仁:', allStaffNames);
            }, 100);
          }
        });
      } else {
        setSelectedProjectId(null);
      }

      // 載入公文附件列表
      if (document.id && !isCopy) {
        fetchAttachments(document.id);
      }
    } else if (visible && isCreate) {
      form.resetFields();
      setSelectedProjectId(null);
      setExistingAttachments([]);
      setFileList([]);
    }
  }, [visible, document, form, isCreate, isCopy]);

  /**
   * 執行實際儲存操作
   */
  const performSave = async (documentData: Partial<Document>) => {
    try {
      setLoading(true);
      const savedDocument = await onSave(documentData);

      // 上傳新附件（支援新建和編輯）
      const targetDocumentId = (savedDocument as Document)?.id || document?.id;

      if (targetDocumentId && fileList.length > 0) {
        try {
          const uploadResult = await uploadFiles(targetDocumentId, fileList);
          const successCount = uploadResult.files?.length || 0;
          const errorCount = uploadResult.errors?.length || 0;

          if (successCount > 0 && errorCount === 0) {
            message.success(`附件上傳成功（共 ${successCount} 個檔案）`);
          } else if (successCount > 0 && errorCount > 0) {
            message.warning(`部分附件上傳成功（成功 ${successCount} 個，失敗 ${errorCount} 個）`);
          } else if (successCount === 0 && errorCount > 0) {
            message.error(`附件上傳失敗（共 ${errorCount} 個錯誤）`);
          }
          setFileList([]);
        } catch (uploadError) {
          logger.error('File upload failed:', uploadError);
          const errorMsg = uploadError instanceof Error ? uploadError.message : '上傳失敗';
          message.error(`附件上傳失敗: ${errorMsg}`);
        }
      } else if (fileList.length > 0 && !targetDocumentId) {
        message.warning('無法取得公文 ID，附件稍後上傳');
      }

      message.success(`${getOperationText()}成功！`);
      onClose();
    } catch (error) {
      logger.error('Save document failed:', error);
      message.error(`${getOperationText()}失敗`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 處理關鍵欄位變更確認
   */
  const handleCriticalChangeConfirm = async () => {
    if (criticalChangeModal.pendingData) {
      setCriticalChangeModal({ visible: false, changes: [], pendingData: null });
      await performSave(criticalChangeModal.pendingData);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // 處理 assignee：陣列轉逗號分隔字串
      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = values.assignee.join(', ');
      } else if (values.assignee) {
        assigneeStr = values.assignee;
      }

      const documentData = {
        ...values,
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
        assignee: assigneeStr,
      };

      // 編輯模式：檢查關鍵欄位變更
      if (operation === 'edit' && document) {
        const criticalChanges = detectCriticalChanges(document, documentData);

        if (criticalChanges.length > 0) {
          // 顯示確認對話框
          setCriticalChangeModal({
            visible: true,
            changes: criticalChanges,
            pendingData: documentData,
          });
          return; // 等待使用者確認
        }
      }

      // 直接執行儲存（建立/複製或無關鍵欄位變更）
      await performSave(documentData);
    } catch (error) {
      logger.error('Form validation failed:', error);
    }
  };

  const handleAddToCalendar = async () => {
    if (!document) return;

    try {
      setCalendarLoading(true);
      await calendarIntegrationService.addDocumentToCalendar(document);
      // 成功訊息已在服務中處理
    } catch (error) {
      logger.error('Add to calendar failed:', error);
      // 錯誤訊息已在服務中處理
    } finally {
      setCalendarLoading(false);
    }
  };

  const getOperationText = () => {
    switch (operation) {
      case 'create': return '新增儲存';
      case 'edit': return '儲存變更';
      case 'copy': return '複製儲存';
      default: return '儲存';
    }
  };

  const getModalTitle = () => {
    const icons = {
      view: <FileTextOutlined />,
      edit: <FileTextOutlined />,
      create: <FileTextOutlined />,
      copy: <CopyOutlined />,
    };

    const titles = {
      view: '查看公文詳情',
      edit: '編輯公文',
      create: '新增公文',
      copy: '複製公文',
    };

    return (
      <Space>
        {operation && icons[operation]}
        {operation && titles[operation]}
      </Space>
    );
  };

  // 檔案驗證函數（使用動態載入的設定）
  const validateFile = (file: File): { valid: boolean; error?: string } => {
    const { allowedExtensions, maxFileSizeMB } = fileSettings;

    // 檢查副檔名
    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');
    if (!allowedExtensions.includes(ext)) {
      return {
        valid: false,
        error: `不支援 ${ext} 檔案格式。允許的格式: ${allowedExtensions.slice(0, 5).join(', ')} 等`,
      };
    }

    // 檢查檔案大小
    const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `檔案 "${file.name}" 大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`,
      };
    }

    return { valid: true };
  };

  const uploadProps = {
    multiple: true,
    fileList,
    showUploadList: false, // 隱藏預設列表，使用自定義卡片顯示
    beforeUpload: (file: File) => {
      // 前端驗證
      const validation = validateFile(file);
      if (!validation.valid) {
        message.error(validation.error);
        return Upload.LIST_IGNORE; // 不加入列表
      }

      // 檢查是否有重複檔名（僅在編輯模式下檢查已上傳附件）
      if (!isCreate && !isCopy) {
        const existingFile = checkDuplicateFile(file.name);
        if (existingFile) {
          // 顯示重複檔案確認對話框
          setDuplicateModal({
            visible: true,
            file: file,
            existingAttachment: existingFile,
          });
          return Upload.LIST_IGNORE; // 先不加入列表，等用戶確認
        }
      }

      return false; // 阻止自動上傳，我們將手動處理
    },
    onChange: ({ fileList: newFileList }: UploadChangeParam<UploadFile>) => {
      setFileList(newFileList);
    },
    onRemove: (file: UploadFile) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
    onPreview: (file: UploadFile) => {
      // 可以添加檔案預覽功能
      logger.debug('Preview file:', file.name);
    },
  };

  return (
    <Modal
      title={getModalTitle()}
      open={visible}
      onCancel={onClose}
      width={800}
      footer={
        isReadOnly ? (
          <Space>
            {document && (
              <Button
                icon={<CalendarOutlined />}
                loading={calendarLoading}
                onClick={handleAddToCalendar}
              >
                加入行事曆
              </Button>
            )}
            <Button onClick={onClose}>關閉</Button>
          </Space>
        ) : (
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button
              type="primary"
              loading={loading}
              onClick={handleSubmit}
            >
              {getOperationText()}
            </Button>
          </Space>
        )
      }
    >
      <Form
        form={form}
        layout="vertical"
        disabled={isReadOnly}
      >
        <Tabs
          defaultActiveKey="1"
          items={[
            {
              key: '1',
              label: '基本資料',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={12}>
                      {/* 根據文件類別顯示不同欄位：發文用發文形式，收文用文件類型 */}
                      {document?.category === '發文' ? (
                        <Form.Item
                          label="發文形式"
                          name="delivery_method"
                          rules={[{ required: true, message: '請選擇發文形式' }]}
                        >
                          <Select placeholder="請選擇發文形式">
                            <Option value="電子交換">電子交換</Option>
                            <Option value="紙本郵寄">紙本郵寄</Option>
                          </Select>
                        </Form.Item>
                      ) : (
                        <Form.Item
                          label="文件類型"
                          name="doc_type"
                          rules={[{ required: true, message: '請選擇文件類型' }]}
                        >
                          <Select placeholder="請選擇文件類型">
                            <Option value="函">函</Option>
                            <Option value="開會通知單">開會通知單</Option>
                            <Option value="會勘通知單">會勘通知單</Option>
                          </Select>
                        </Form.Item>
                      )}
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="公文字號"
                        name="doc_number"
                        rules={[{ required: true, message: '請輸入公文字號' }]}
                      >
                        <Input placeholder="如：乾坤字第1130001號" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="發文機關"
                        name="sender"
                        rules={[{ required: true, message: '請輸入發文機關' }]}
                      >
                        <Input placeholder="請輸入發文機關" />
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="受文者"
                        name="receiver"
                      >
                        <Input placeholder="請輸入受文者" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="主旨"
                    name="subject"
                    rules={[{ required: true, message: '請輸入主旨' }]}
                  >
                    <TextArea
                      rows={2}
                      placeholder="請輸入公文主旨"
                      maxLength={200}
                      showCount
                    />
                  </Form.Item>

                  <Form.Item
                    label="說明"
                    name="content"
                  >
                    <TextArea
                      rows={4}
                      placeholder="請輸入公文內容說明"
                      maxLength={1000}
                      showCount
                    />
                  </Form.Item>

                  <Form.Item
                    label="備註"
                    name="notes"
                  >
                    <TextArea
                      rows={3}
                      placeholder="請輸入備註"
                      maxLength={500}
                      showCount
                    />
                  </Form.Item>

                  <Form.Item
                    label="簡要說明(乾坤備註)"
                    name="ck_note"
                  >
                    <TextArea
                      rows={3}
                      placeholder="請輸入乾坤內部簡要說明或備註"
                      maxLength={1000}
                      showCount
                    />
                  </Form.Item>
                </>
              )
            },
            {
              key: '2',
              label: '日期與狀態',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        label="發文日期"
                        name="doc_date"
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          placeholder="請選擇發文日期"
                        />
                      </Form.Item>
                    </Col>

                    <Col span={8}>
                      <Form.Item
                        label="收文日期"
                        name="receive_date"
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          placeholder="請選擇收文日期"
                        />
                      </Form.Item>
                    </Col>

                    <Col span={8}>
                      <Form.Item
                        label="發送日期"
                        name="send_date"
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          placeholder="請選擇發送日期"
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="優先等級"
                        name="priority"
                      >
                        <Select placeholder="請選擇優先等級">
                          <Option value={1}>
                            <Tag color="blue">1 - 最高</Tag>
                          </Option>
                          <Option value={2}>
                            <Tag color="green">2 - 高</Tag>
                          </Option>
                          <Option value={3}>
                            <Tag color="orange">3 - 普通</Tag>
                          </Option>
                          <Option value={4}>
                            <Tag color="red">4 - 低</Tag>
                          </Option>
                          <Option value={5}>
                            <Tag color="purple">5 - 最低</Tag>
                          </Option>
                        </Select>
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="處理狀態"
                        name="status"
                      >
                        <Select placeholder="請選擇處理狀態">
                          <Option value="收文完成">收文完成</Option>
                          <Option value="使用者確認">使用者確認</Option>
                          <Option value="收文異常">收文異常</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                </>
              )
            },
            {
              key: '3',
              label: '案件與人員',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="承攬案件"
                        name="contract_project_id"
                      >
                        <Select
                          placeholder="請選擇承攬案件"
                          loading={casesLoading || staffLoading}
                          allowClear
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          onChange={handleProjectChange}
                          options={Array.isArray(cases) ? cases.map(case_ => ({
                            value: case_.id,
                            label: case_.project_name || '未命名案件',
                            key: case_.id
                          })) : []}
                        />
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="業務同仁"
                        name="assignee"
                      >
                        <Select
                          mode="multiple"
                          placeholder="請選擇業務同仁（可複選）"
                          loading={usersLoading || staffLoading}
                          allowClear
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          options={
                            // 優先顯示專案指定的業務同仁，若無則顯示全部使用者
                            selectedProjectId && (projectStaffMap[selectedProjectId]?.length ?? 0) > 0
                              ? (projectStaffMap[selectedProjectId] ?? []).map(staff => ({
                                  value: staff.user_name,
                                  label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name,
                                  key: staff.user_id || staff.id
                                }))
                              : Array.isArray(users) ? users.map(user => ({
                                  value: user.full_name || user.username,
                                  label: user.full_name || user.username,
                                  key: user.id
                                })) : []
                          }
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </>
              )
            },
            {
              key: '4',
              label: (
                <span>
                  附件上傳
                  {existingAttachments.length > 0 && (
                    <Tag color="blue" style={{ marginLeft: 8 }}>{existingAttachments.length}</Tag>
                  )}
                </span>
              ),
              children: (
                <Spin spinning={attachmentsLoading}>
                  {/* 既有附件列表 */}
                  {existingAttachments.length > 0 && (
                    <Card
                      size="small"
                      title={
                        <Space>
                          <PaperClipOutlined />
                          <span>已上傳附件（{existingAttachments.length} 個）</span>
                        </Space>
                      }
                      style={{ marginBottom: 16 }}
                    >
                      <List
                        size="small"
                        dataSource={existingAttachments}
                        renderItem={(item: DocumentAttachment) => (
                          <List.Item
                            actions={[
                              // 預覽按鈕（僅支援 PDF/圖片/文字檔）
                              isPreviewable(item.content_type, item.original_filename || item.filename) && (
                                <Button
                                  key="preview"
                                  type="link"
                                  size="small"
                                  icon={<EyeOutlined />}
                                  onClick={() => handlePreviewAttachment(item.id, item.original_filename || item.filename)}
                                  style={{ color: '#52c41a' }}
                                >
                                  預覽
                                </Button>
                              ),
                              <Button
                                key="download"
                                type="link"
                                size="small"
                                icon={<DownloadOutlined />}
                                onClick={() => handleDownload(item.id, item.original_filename || item.filename)}
                              >
                                下載
                              </Button>,
                              !isReadOnly && (
                                <Popconfirm
                                  key="delete"
                                  title="確定要刪除此附件嗎？"
                                  onConfirm={() => handleDeleteAttachment(item.id)}
                                  okText="確定"
                                  cancelText="取消"
                                >
                                  <Button
                                    type="link"
                                    size="small"
                                    danger
                                    icon={<DeleteOutlined />}
                                  >
                                    刪除
                                  </Button>
                                </Popconfirm>
                              ),
                            ].filter(Boolean)}
                          >
                            <List.Item.Meta
                              avatar={getFileIcon(item.content_type, item.original_filename || item.filename)}
                              title={item.original_filename || item.filename}
                              description={
                                <span style={{ fontSize: 12, color: '#999' }}>
                                  {item.file_size ? `${(item.file_size / 1024).toFixed(1)} KB` : ''}
                                  {item.created_at && ` · ${dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}`}
                                </span>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    </Card>
                  )}

                  {/* 上傳區域（非唯讀模式才顯示）*/}
                  {!isReadOnly ? (
                    <Form.Item label="上傳新附件">
                      <Dragger {...uploadProps} disabled={uploading}>
                        <p className="ant-upload-drag-icon">
                          <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">點擊或拖拽文件到此區域上傳</p>
                        <p className="ant-upload-hint">
                          支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 {fileSettings.maxFileSizeMB}MB
                        </p>
                      </Dragger>

                      {/* 待上傳檔案預覽 */}
                      {fileList.length > 0 && !uploading && (
                        <Card
                          size="small"
                          style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}
                          title={
                            <span style={{ color: '#52c41a' }}>
                              <CloudUploadOutlined style={{ marginRight: 8 }} />
                              待上傳檔案（{fileList.length} 個）
                            </span>
                          }
                        >
                          <List
                            size="small"
                            dataSource={fileList}
                            renderItem={(file: UploadFile) => (
                              <List.Item>
                                <List.Item.Meta
                                  avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                                  title={file.name}
                                  description={file.size ? `${(file.size / 1024).toFixed(1)} KB` : ''}
                                />
                              </List.Item>
                            )}
                          />
                          <p style={{ color: '#999', fontSize: 12, marginTop: 8, marginBottom: 0 }}>
                            點擊下方「儲存變更」按鈕後開始上傳
                          </p>
                        </Card>
                      )}

                      {/* 上傳進度條 */}
                      {uploading && (
                        <Card
                          size="small"
                          style={{ marginTop: 16, background: '#e6f7ff', border: '1px solid #91d5ff' }}
                          title={
                            <span style={{ color: '#1890ff' }}>
                              <LoadingOutlined style={{ marginRight: 8 }} />
                              正在上傳檔案...
                            </span>
                          }
                        >
                          <Progress
                            percent={uploadProgress}
                            status="active"
                            strokeColor={{
                              '0%': '#108ee9',
                              '100%': '#87d068',
                            }}
                            strokeWidth={12}
                          />
                          <p style={{ textAlign: 'center', color: '#1890ff', marginTop: 12, marginBottom: 0, fontWeight: 500 }}>
                            上傳進度：{uploadProgress}%
                          </p>
                        </Card>
                      )}

                      {/* 上傳錯誤訊息 */}
                      {uploadErrors.length > 0 && (
                        <Alert
                          type="warning"
                          showIcon
                          closable
                          onClose={() => setUploadErrors([])}
                          style={{ marginTop: 16 }}
                          message="部分檔案上傳失敗"
                          description={
                            <ul style={{ margin: 0, paddingLeft: 20 }}>
                              {uploadErrors.map((err, idx) => (
                                <li key={idx}>{err}</li>
                              ))}
                            </ul>
                          }
                        />
                      )}
                    </Form.Item>
                  ) : (
                    existingAttachments.length === 0 && (
                      <Empty
                        description="此公文尚無附件"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                      />
                    )
                  )}
                </Spin>
              )
            },
            ...(isReadOnly && document ? [{
              key: '5',
              label: '系統資訊',
              children: (
                <Card size="small" title="系統資訊" type="inner">
                  <Row gutter={16}>
                    <Col span={8}>
                      <strong>建立時間:</strong><br />
                      {document.created_at ? dayjs(document.created_at).format('YYYY-MM-DD HH:mm') : '未知'}
                    </Col>
                    <Col span={8}>
                      <strong>修改時間:</strong><br />
                      {document.updated_at ? dayjs(document.updated_at).format('YYYY-MM-DD HH:mm') : '未知'}
                    </Col>
                    <Col span={8}>
                      <strong>建立者:</strong><br />
                      {document.creator || '系統'}
                    </Col>
                  </Row>
                </Card>
              )
            }] : [])
          ]}
        />
      </Form>

      {/* 關鍵欄位變更確認 Modal - 使用子組件 */}
      <CriticalChangeConfirmModal
        visible={criticalChangeModal.visible}
        changes={criticalChangeModal.changes}
        loading={loading}
        onConfirm={handleCriticalChangeConfirm}
        onCancel={() => setCriticalChangeModal({ visible: false, changes: [], pendingData: null })}
      />

      {/* 重複檔案確認對話框 - 使用子組件 */}
      <DuplicateFileModal
        visible={duplicateModal.visible}
        file={duplicateModal.file}
        existingAttachment={duplicateModal.existingAttachment}
        onOverwrite={handleOverwriteFile}
        onKeepBoth={handleKeepBoth}
        onCancel={handleCancelDuplicate}
      />
    </Modal>
  );
};

// 發送公文Modal
interface DocumentSendModalProps {
  document: Document | null;
  visible: boolean;
  onClose: () => void;
  onSend: (sendData: any) => Promise<void>;
}

export const DocumentSendModal: React.FC<DocumentSendModalProps> = ({
  document,
  visible,
  onClose,
  onSend,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      await onSend(values);
      message.success('公文發送成功！');
      onClose();
    } catch (error) {
      logger.error('Send document failed:', error);
      message.error('公文發送失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <SendOutlined />
          發送公文
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={loading} onClick={handleSend}>
            發送
          </Button>
        </Space>
      }
    >
      {document && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <strong>公文字號:</strong> {document.doc_number}
            </Col>
            <Col span={12}>
              <strong>主旨:</strong> {document.subject}
            </Col>
          </Row>
        </Card>
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          label="收件人"
          name="recipients"
          rules={[{ required: true, message: '請選擇收件人' }]}
        >
          <Select
            mode="multiple"
            placeholder="請選擇收件人"
            options={[
              { label: '張三', value: 'zhang.san@example.com' },
              { label: '李四', value: 'li.si@example.com' },
              { label: '王五', value: 'wang.wu@example.com' },
            ]}
          />
        </Form.Item>

        <Form.Item
          label="發送方式"
          name="sendMethod"
          initialValue="email"
        >
          <Select>
            <Option value="email">電子郵件</Option>
            <Option value="internal">內部系統</Option>
            <Option value="both">兩者皆是</Option>
          </Select>
        </Form.Item>

        <Form.Item
          label="發送備註"
          name="sendNotes"
        >
          <TextArea rows={3} placeholder="請輸入發送備註" />
        </Form.Item>
      </Form>
    </Modal>
  );
};