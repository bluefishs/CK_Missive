/**
 * 公文詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構：
 * - 公文資訊：發文形式（發文）/文件類型（收文）、字號、發文/受文機關、主旨、說明
 * - 日期狀態：發文/收文/發送日期、優先等級、處理狀態
 * - 承案人資：承攬案件、業務同仁、備註
 * - 附件紀錄：附件上傳與管理
 *
 * @version 2.1.0
 * @date 2026-01-07
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  App,
  Upload,
  Space,
  Row,
  Col,
  Tag,
  List,
  Popconfirm,
  Spin,
  Empty,
  Progress,
  Alert,
  Descriptions,
  Divider,
  Typography,
} from 'antd';
import {
  FileTextOutlined,
  CalendarOutlined,
  TeamOutlined,
  PaperClipOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  InboxOutlined,
  CloudUploadOutlined,
  FileOutlined,
  LoadingOutlined,
  SendOutlined,
  PlusOutlined,
  LinkOutlined,
  EnvironmentOutlined,
  // CopyOutlined, // 複製功能已隱藏
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  dispatchOrdersApi,
  documentLinksApi,
  documentProjectLinksApi,
  taoyuanProjectsApi,
} from '../api/taoyuanDispatchApi';
import type {
  DispatchOrder,
  DispatchOrderCreate,
  TaoyuanProject,
  DocumentDispatchLink,
  DocumentProjectLink,
  LinkType,
} from '../types/api';
import { isReceiveDocument } from '../types/api';
import dayjs from 'dayjs';
import {
  DetailPageLayout,
  createTabItem,
  getTagColor,
} from '../components/common/DetailPage';
import { documentsApi } from '../api/documentsApi';
import { filesApi } from '../api/filesApi';
import { apiClient } from '../api/client';
import { Document } from '../types';
import { IntegratedEventModal } from '../components/calendar/IntegratedEventModal';
import { logger } from '../utils/logger';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';

const { TextArea } = Input;
const { Option } = Select;
const { Dragger } = Upload;
const { Text } = Typography;

// =============================================================================
// 常數定義
// =============================================================================

/** 文件類型選項（收文用） */
const DOC_TYPE_OPTIONS = [
  { value: '函', label: '函', color: 'blue' },
  { value: '開會通知單', label: '開會通知單', color: 'green' },
  { value: '會勘通知單', label: '會勘通知單', color: 'orange' },
];

/** 發文形式選項（電子交換/紙本郵寄） */
const DELIVERY_METHOD_OPTIONS = [
  { value: '電子交換', label: '電子交換', color: 'green' },
  { value: '紙本郵寄', label: '紙本郵寄', color: 'orange' },
];

/** 處理狀態選項 */
const STATUS_OPTIONS = [
  { value: '收文完成', label: '收文完成', color: 'processing' },
  { value: '使用者確認', label: '使用者確認', color: 'success' },
  { value: '收文異常', label: '收文異常', color: 'error' },
];

/** 優先等級選項 */
const PRIORITY_OPTIONS = [
  { value: 1, label: '1 - 最高', color: 'blue' },
  { value: 2, label: '2 - 高', color: 'green' },
  { value: 3, label: '3 - 普通', color: 'orange' },
  { value: 4, label: '4 - 低', color: 'red' },
  { value: 5, label: '5 - 最低', color: 'purple' },
];

/** 預設檔案驗證常數 */
const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
  '.zip', '.rar', '.7z', '.txt', '.csv', '.xml', '.json',
  '.dwg', '.dxf', '.shp', '.kml', '.kmz',
];
const DEFAULT_MAX_FILE_SIZE_MB = 50;

// =============================================================================
// 主元件
// =============================================================================

export const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  // 狀態
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [document, setDocument] = useState<Document | null>(null);
  const [activeTab, setActiveTab] = useState('info');
  const [isEditing, setIsEditing] = useState(false);

  // 附件相關狀態
  const [attachments, setAttachments] = useState<any[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // 下拉選項資料
  const [cases, setCases] = useState<any[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [users, setUsers] = useState<any[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, any[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedContractProjectId, setSelectedContractProjectId] = useState<number | null>(null);
  const projectStaffCacheRef = React.useRef<Record<number, any[]>>({});

  // 儲存 assignee 的狀態（作為備用）
  const [currentAssigneeValues, setCurrentAssigneeValues] = useState<string[]>([]);

  // 檔案設定
  const [fileSettings, setFileSettings] = useState({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  // 行事曆整合式事件模態框
  const [showIntegratedEventModal, setShowIntegratedEventModal] = useState(false);

  // 派工安排相關狀態
  const [dispatchLinks, setDispatchLinks] = useState<DocumentDispatchLink[]>([]);
  const [dispatchLinksLoading, setDispatchLinksLoading] = useState(false);
  const [dispatchForm] = Form.useForm();
  const queryClient = useQueryClient();

  // 工程關聯相關狀態
  const [projectLinks, setProjectLinks] = useState<DocumentProjectLink[]>([]);
  const [projectLinksLoading, setProjectLinksLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number>();
  const [projectSearch, setProjectSearch] = useState('');
  const [linkingProject, setLinkingProject] = useState(false);

  // 桃園派工作業類別 (匹配後端 WORK_TYPES)
  const TAOYUAN_WORK_TYPES_LIST = [
    '#0.專案行政作業',
    '00.專案會議',
    '01.地上物查估作業',
    '02.土地協議市價查估作業',
    '03.土地徵收市價查估作業',
    '04.相關計畫書製作',
    '05.測量作業',
    '06.樁位測釘作業',
    '07.辦理教育訓練',
    '08.作業提繳事項',
  ];

  // 查詢機關承辦清單（用於派工安排的案件承辦下拉選單）
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
    enabled: isEditing, // 只在編輯模式才載入
  });
  const agencyContacts = agencyContactsData?.items ?? [];

  // 查詢協力廠商清單（用於派工安排的查估單位下拉選單）
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
    enabled: isEditing, // 只在編輯模式才載入
  });
  const projectVendors = vendorsData?.associations ?? [];

  // =============================================================================
  // 資料載入
  // =============================================================================

  /** 載入公文關聯的派工紀錄 */
  const loadDispatchLinks = useCallback(async () => {
    if (!id) return;
    logger.debug('[loadDispatchLinks] 開始載入, docId:', id);
    setDispatchLinksLoading(true);
    try {
      const docId = parseInt(id, 10);
      const result = await documentLinksApi.getDispatchLinks(docId);
      logger.debug('[loadDispatchLinks] API 回應:', result);
      const orders = result.dispatch_orders || [];
      logger.debug('[loadDispatchLinks] 設定 dispatchLinks, 數量:', orders.length);
      setDispatchLinks(orders);
    } catch (error) {
      logger.error('[loadDispatchLinks] 載入派工關聯失敗:', error);
      setDispatchLinks([]);
    } finally {
      setDispatchLinksLoading(false);
    }
  }, [id]);

  /** 載入公文關聯的工程紀錄 */
  const loadProjectLinks = useCallback(async () => {
    if (!id) return;
    setProjectLinksLoading(true);
    try {
      const docId = parseInt(id, 10);
      const result = await documentProjectLinksApi.getProjectLinks(docId);
      setProjectLinks(result.projects || []);
    } catch (error) {
      console.error('載入工程關聯失敗:', error);
      setProjectLinks([]);
    } finally {
      setProjectLinksLoading(false);
    }
  }, [id]);

  /** 載入公文資料 */
  const loadDocument = useCallback(async () => {
    if (!id) return;

    setLoading(true);
    try {
      const docId = parseInt(id, 10);
      const doc = await documentsApi.getDocument(docId);
      logger.debug('[loadDocument] API 完整回傳:', JSON.stringify(doc, null, 2));
      logger.debug('[loadDocument] ck_note 值:', doc.ck_note);
      setDocument(doc);

      // 處理 assignee 欄位：字串轉陣列
      let assigneeArray: string[] = [];
      const rawAssignee = (doc as any).assignee;
      logger.debug('[loadDocument] 原始 assignee:', rawAssignee, '類型:', typeof rawAssignee);
      if (rawAssignee) {
        if (Array.isArray(rawAssignee)) {
          assigneeArray = rawAssignee;
        } else if (typeof rawAssignee === 'string') {
          assigneeArray = rawAssignee.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
      }
      logger.debug('[loadDocument] 處理後 assigneeArray:', assigneeArray);

      // 也檢查 assigned_staff 欄位（後端可能使用不同欄位名）
      const assignedStaff = (doc as any).assigned_staff;
      logger.debug('[loadDocument] assigned_staff:', assignedStaff);

      // 儲存到狀態變數（作為備用）
      setCurrentAssigneeValues(assigneeArray);

      // 設定表單初始值
      form.setFieldsValue({
        ...doc,
        doc_date: doc.doc_date ? dayjs(doc.doc_date) : null,
        receive_date: doc.receive_date ? dayjs(doc.receive_date) : null,
        send_date: doc.send_date ? dayjs(doc.send_date) : null,
        assignee: assigneeArray,
      });

      // 設定專案 ID 並載入業務同仁
      const projectId = (doc as any).contract_project_id;
      logger.debug('[loadDocument] contract_project_id:', projectId);
      if (projectId) {
        setSelectedContractProjectId(projectId);
        // 等待專案同仁載入完成
        const staffList = await fetchProjectStaff(projectId);
        logger.debug('[loadDocument] 載入專案同仁完成:', staffList);

        // 如果 assignee 為空但有專案同仁，自動填入
        if ((!assigneeArray || assigneeArray.length === 0) && staffList && staffList.length > 0) {
          const staffNames = staffList.map((s: any) => s.user_name);
          logger.debug('[loadDocument] 自動填入業務同仁:', staffNames);
          form.setFieldsValue({ assignee: staffNames });
          setCurrentAssigneeValues(staffNames);
        }
      }

      // 載入附件
      loadAttachments(docId);
    } catch (error) {
      console.error('載入公文失敗:', error);
      message.error('載入公文失敗');
      setDocument(null);
    } finally {
      setLoading(false);
    }
  }, [id, message, form]);

  /** 載入附件 */
  const loadAttachments = async (docId: number) => {
    setAttachmentsLoading(true);
    try {
      const atts = await filesApi.getDocumentAttachments(docId);
      setAttachments(atts);
    } catch (error) {
      console.error('載入附件失敗:', error);
      setAttachments([]);
    } finally {
      setAttachmentsLoading(false);
    }
  };

  /** 載入承攬案件選項 */
  const loadCases = async () => {
    setCasesLoading(true);
    try {
      const data = await apiClient.post<{ projects?: any[]; items?: any[] }>(
        '/projects/list',
        { page: 1, limit: 100 }
      );
      const projectsData = data.projects || data.items || [];
      setCases(Array.isArray(projectsData) ? projectsData : []);
    } catch (error) {
      console.error('載入承攬案件失敗:', error);
      setCases([]);
    } finally {
      setCasesLoading(false);
    }
  };

  /** 載入使用者列表（作為業務同仁備用選項）*/
  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      const data = await apiClient.post<{ users?: any[]; items?: any[] }>(
        '/users/list',
        { page: 1, limit: 100 }
      );
      const usersData = data.users || data.items || [];
      logger.debug('[loadUsers] 載入使用者:', usersData.length, '筆');
      setUsers(Array.isArray(usersData) ? usersData : []);
    } catch (error) {
      console.error('[loadUsers] 載入使用者失敗:', error);
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  };

  /** 載入檔案設定 */
  const loadFileSettings = async () => {
    try {
      const info = await filesApi.getStorageInfo();
      setFileSettings({
        allowedExtensions: info.allowed_extensions,
        maxFileSizeMB: info.max_file_size_mb,
      });
    } catch (error) {
      console.warn('載入檔案設定失敗，使用預設值:', error);
    }
  };

  /** 載入專案業務同仁 */
  const fetchProjectStaff = async (projectId: number): Promise<any[]> => {
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      setProjectStaffMap(prev => ({ ...prev, [projectId]: cachedData }));
      return cachedData;
    }

    setStaffLoading(true);
    try {
      const data = await apiClient.post<{ staff?: any[] }>(
        `/project-staff/project/${projectId}/list`,
        {}
      );
      const staffData = data.staff || [];
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      console.error('載入專案業務同仁失敗:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  };

  // 初始載入
  useEffect(() => {
    loadDocument();
    loadCases();
    loadUsers();
    loadFileSettings();
    loadDispatchLinks();
    loadProjectLinks();
  }, [loadDocument, loadDispatchLinks, loadProjectLinks]);

  // 當公文載入完成後且進入編輯模式時，自動設定派工表單的機關/乾坤函文號
  // 只在 isEditing 為 true 時才設定，避免 useForm 未連接 Form 元件的警告
  useEffect(() => {
    if (document?.doc_number && isEditing) {
      const isReceiveDoc = isReceiveDocument(document.category);
      dispatchForm.setFieldsValue({
        agency_doc_no: isReceiveDoc ? document.doc_number : undefined,
        company_doc_no: !isReceiveDoc ? document.doc_number : undefined,
      });
    }
  }, [document?.doc_number, document?.category, dispatchForm, isEditing]);

  // 當進入編輯模式時，自動載入下一個派工單號
  useEffect(() => {
    if (isEditing) {
      const loadNextDispatchNo = async () => {
        try {
          const result = await dispatchOrdersApi.getNextDispatchNo();
          if (result.success && result.next_dispatch_no) {
            dispatchForm.setFieldsValue({
              dispatch_no: result.next_dispatch_no,
            });
          }
        } catch (error) {
          console.error('載入派工單號失敗:', error);
        }
      };
      loadNextDispatchNo();
    }
  }, [isEditing, dispatchForm]);

  // =============================================================================
  // 事件處理
  // =============================================================================

  /** 儲存公文 */
  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();
      logger.debug('[handleSave] 表單值:', values);
      logger.debug('[handleSave] ck_note 值:', values.ck_note);
      logger.debug('[handleSave] assignee 值:', values.assignee, '類型:', typeof values.assignee);

      // 處理 assignee：陣列轉逗號分隔字串
      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = values.assignee.join(', ');
      } else if (values.assignee) {
        assigneeStr = values.assignee;
      }
      logger.debug('[handleSave] 儲存的 assigneeStr:', assigneeStr);

      const documentData = {
        ...values,
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
        assignee: assigneeStr,
      };
      logger.debug('[handleSave] 送出的 documentData.ck_note:', documentData.ck_note);

      const updatedDoc = await documentsApi.updateDocument(parseInt(id!, 10), documentData);
      logger.debug('[handleSave] API 回傳 ck_note:', updatedDoc.ck_note);

      // 上傳新附件
      if (fileList.length > 0) {
        await uploadFiles(parseInt(id!, 10), fileList);
        setFileList([]);
      }

      message.success('儲存成功');

      // 重新載入資料（在退出編輯模式之前）
      logger.debug('[handleSave] 開始重新載入資料...');
      await loadDocument();
      logger.debug('[handleSave] 重新載入完成');

      // 最後才退出編輯模式，確保表單值已更新
      setIsEditing(false);
    } catch (error) {
      console.error('儲存失敗:', error);
      message.error('儲存失敗');
    } finally {
      setSaving(false);
    }
  };

  /** 取消編輯 */
  const handleCancelEdit = () => {
    setIsEditing(false);
    setFileList([]);
    // 重置表單到原始值
    if (document) {
      let assigneeArray: string[] = [];
      const rawAssignee = (document as any).assignee;
      if (rawAssignee) {
        if (Array.isArray(rawAssignee)) {
          assigneeArray = rawAssignee;
        } else if (typeof rawAssignee === 'string') {
          assigneeArray = rawAssignee.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
      }

      form.setFieldsValue({
        ...document,
        doc_date: document.doc_date ? dayjs(document.doc_date) : null,
        receive_date: document.receive_date ? dayjs(document.receive_date) : null,
        send_date: document.send_date ? dayjs(document.send_date) : null,
        assignee: assigneeArray,
      });
    }
  };

  /** 選擇專案後處理 */
  const handleProjectChange = async (projectId: number | null | undefined) => {
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
        const names = currentStaff.map((s: any) => s.user_name);
        form.setFieldsValue({ assignee: names });
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  };

  /** 加入行事曆 - 開啟整合式事件建立模態框 */
  const handleAddToCalendar = () => {
    if (!document) return;
    setShowIntegratedEventModal(true);
  };

  /** 事件建立成功回調 */
  const handleEventCreated = (eventId: number) => {
    message.success('行事曆事件建立成功');
    logger.debug('[handleEventCreated] 新建事件 ID:', eventId);
  };

  /** 複製公文（功能已隱藏，保留備用） */
  // const handleCopy = async () => {
  //   if (!document) return;
  //   try {
  //     const copyData = {
  //       doc_number: `${document.doc_number}-副本`,
  //       doc_type: document.doc_type || '函',
  //       subject: document.subject || '',
  //       sender: document.sender,
  //       receiver: document.receiver,
  //       content: document.content,
  //       doc_date: document.doc_date,
  //       receive_date: document.receive_date,
  //       send_date: document.send_date,
  //       status: document.status,
  //       priority: (document as any).priority,
  //       contract_project_id: (document as any).contract_project_id,
  //       assignee: (document as any).assignee,
  //       notes: (document as any).notes,
  //     };
  //
  //     const newDoc = await documentsApi.createDocument(copyData);
  //     message.success('公文複製成功');
  //     navigate(`/documents/${newDoc.id}`);
  //   } catch (error) {
  //     console.error('複製公文失敗:', error);
  //     message.error('複製公文失敗');
  //   }
  // };

  /** 刪除公文 */
  const handleDelete = async () => {
    if (!document || !id) return;
    try {
      await documentsApi.deleteDocument(parseInt(id, 10));
      message.success('公文刪除成功');
      navigate('/documents');
    } catch (error) {
      console.error('刪除公文失敗:', error);
      message.error('刪除公文失敗');
    }
  };

  // =============================================================================
  // 附件處理
  // =============================================================================

  /** 上傳檔案 */
  const uploadFiles = async (documentId: number, files: any[]): Promise<any> => {
    if (files.length === 0) return { success: true, files: [], errors: [] };

    const fileObjects: File[] = files
      .map(f => f.originFileObj)
      .filter((f): f is File => f !== undefined);

    if (fileObjects.length === 0) return { success: true, files: [], errors: [] };

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

      // 重新載入附件
      await loadAttachments(documentId);

      const successCount = result.files?.length || 0;
      const errorCount = result.errors?.length || 0;

      if (successCount > 0 && errorCount === 0) {
        message.success(`附件上傳成功（共 ${successCount} 個檔案）`);
      } else if (successCount > 0 && errorCount > 0) {
        message.warning(`部分附件上傳成功（成功 ${successCount} 個，失敗 ${errorCount} 個）`);
      }

      return result;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '上傳失敗';
      message.error(`附件上傳失敗: ${errorMsg}`);
      throw error;
    } finally {
      setUploading(false);
    }
  };

  /** 下載附件 */
  const handleDownload = async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename);
    } catch (error) {
      console.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  };

  /** 預覽附件 */
  const handlePreview = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      console.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  /** 刪除附件 */
  const handleDeleteAttachment = async (attachmentId: number) => {
    try {
      await filesApi.deleteAttachment(attachmentId);
      message.success('附件刪除成功');
      if (id) {
        await loadAttachments(parseInt(id, 10));
      }
    } catch (error) {
      console.error('刪除附件失敗:', error);
      message.error('附件刪除失敗');
    }
  };

  /** 判斷是否可預覽 */
  const isPreviewable = (contentType?: string, filename?: string): boolean => {
    if (contentType) {
      if (contentType.startsWith('image/') ||
          contentType === 'application/pdf' ||
          contentType.startsWith('text/')) {
        return true;
      }
    }
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  /** 取得檔案圖示 */
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

  /** 檔案驗證 */
  const validateFile = (file: File): { valid: boolean; error?: string } => {
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
  };

  /** Upload 元件屬性 */
  const uploadProps = {
    multiple: true,
    fileList,
    showUploadList: false,
    beforeUpload: (file: File) => {
      const validation = validateFile(file);
      if (!validation.valid) {
        message.error(validation.error);
        return Upload.LIST_IGNORE;
      }
      return false;
    },
    onChange: ({ fileList: newFileList }: any) => {
      setFileList(newFileList);
    },
    onRemove: (file: any) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
  };

  // =============================================================================
  // Tab 內容渲染
  // =============================================================================

  /** Tab 1: 公文資訊 */
  const renderInfoTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
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
                {DELIVERY_METHOD_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                ))}
              </Select>
            </Form.Item>
          ) : (
            <Form.Item
              label="文件類型"
              name="doc_type"
              rules={[{ required: true, message: '請選擇文件類型' }]}
            >
              <Select placeholder="請選擇文件類型">
                {DOC_TYPE_OPTIONS.map(opt => (
                  <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                ))}
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
          <Form.Item label="受文者" name="receiver">
            <Input placeholder="請輸入受文者" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="主旨"
        name="subject"
        rules={[{ required: true, message: '請輸入主旨' }]}
      >
        <TextArea rows={2} placeholder="請輸入公文主旨" maxLength={200} showCount />
      </Form.Item>

      <Form.Item label="說明" name="content">
        <TextArea rows={4} placeholder="請輸入公文內容說明" maxLength={1000} showCount />
      </Form.Item>

      <Form.Item label="備註" name="notes">
        <TextArea rows={3} placeholder="請輸入備註" maxLength={500} showCount />
      </Form.Item>

      <Form.Item label="簡要說明(乾坤備註)" name="ck_note">
        <TextArea rows={3} placeholder="請輸入乾坤內部簡要說明或備註" maxLength={1000} showCount />
      </Form.Item>

      {/* 唯讀模式下顯示系統資訊 */}
      {!isEditing && document && (
        <>
          <Divider />
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="建立時間">
              {document.created_at ? dayjs(document.created_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="更新時間">
              {document.updated_at ? dayjs(document.updated_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="建立者">
              {(document as any).creator || '系統'}
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Form>
  );

  /** Tab 2: 日期狀態 */
  const renderDateStatusTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="發文日期" name="doc_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇發文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="收文日期" name="receive_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇收文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="發送日期" name="send_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇發送日期" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="優先等級" name="priority">
            <Select placeholder="請選擇優先等級">
              {PRIORITY_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>
                  <Tag color={opt.color}>{opt.label}</Tag>
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="處理狀態" name="status">
            <Select placeholder="請選擇處理狀態">
              {STATUS_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  // 使用 Form.useWatch 監聽 assignee 欄位變化（響應式更新）
  const watchedAssignee = Form.useWatch('assignee', form);

  // 除錯：監控 watchedAssignee 變化
  useEffect(() => {
    logger.debug('[useEffect] watchedAssignee 變化:', watchedAssignee);
  }, [watchedAssignee]);

  /** Tab 3: 承案人資 */
  const renderCaseStaffTab = () => {
    // 取得目前表單的 assignee 值，用於確保已選取的值顯示在選項中
    // 優先使用 watchedAssignee，若為空則使用狀態變數
    const currentAssignees: string[] = Array.isArray(watchedAssignee) && watchedAssignee.length > 0
      ? watchedAssignee
      : currentAssigneeValues;

    // 建立業務同仁選項
    const buildAssigneeOptions = () => {
      // 專案業務同仁選項
      const staffList = selectedContractProjectId ? projectStaffMap[selectedContractProjectId] : undefined;
      const projectStaffOptions =
        staffList && staffList.length > 0
          ? staffList.map((staff) => ({
              value: staff.user_name,
              label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name,
              key: `staff-${staff.user_id || staff.id}`,
            }))
          : [];

      // 使用者選項（作為備用）
      const userOptions = Array.isArray(users)
        ? users.map((user) => ({
            value: user.full_name || user.username,
            label: user.full_name || user.username,
            key: `user-${user.id}`,
          }))
        : [];

      // 優先使用專案同仁，若無則使用全部使用者
      const baseOptions = projectStaffOptions.length > 0 ? projectStaffOptions : userOptions;

      // 確保目前已選取的值也在選項中（避免值存在但選項沒載入的情況）
      const existingValues = new Set(baseOptions.map((o) => o.value));
      const missingOptions = currentAssignees
        .filter((v) => v && !existingValues.has(v))
        .map((v) => ({ value: v, label: v, key: `current-${v}` }));

      const finalOptions = [...baseOptions, ...missingOptions];
      logger.debug('[buildAssigneeOptions] currentAssignees:', currentAssignees, 'options count:', finalOptions.length);
      return finalOptions;
    };

    return (
      <Form form={form} layout="vertical" disabled={!isEditing}>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="承攬案件" name="contract_project_id">
              <Select
                placeholder="請選擇承攬案件"
                loading={casesLoading || staffLoading}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                onChange={handleProjectChange}
                options={cases.map((case_) => ({
                  value: case_.id,
                  label: case_.project_name || case_.case_name || '未命名案件',
                  key: case_.id,
                }))}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="業務同仁" name="assignee">
              <Select
                mode="multiple"
                placeholder="請選擇業務同仁（可複選）"
                loading={staffLoading || usersLoading}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={buildAssigneeOptions()}
              />
            </Form.Item>
          </Col>
        </Row>

      </Form>
    );
  };

  /** Tab 4: 附件紀錄 */
  const renderAttachmentsTab = () => (
    <Spin spinning={attachmentsLoading}>
      {/* 既有附件列表 */}
      {attachments.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <PaperClipOutlined />
              <span>已上傳附件（{attachments.length} 個）</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <List
            size="small"
            dataSource={attachments}
            renderItem={(item: any) => (
              <List.Item
                actions={[
                  isPreviewable(item.content_type, item.original_filename || item.filename) && (
                    <Button
                      key="preview"
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => handlePreview(item.id, item.original_filename || item.filename)}
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
                  isEditing && (
                    <Popconfirm
                      key="delete"
                      title="確定要刪除此附件嗎？"
                      onConfirm={() => handleDeleteAttachment(item.id)}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>
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

      {/* 上傳區域（編輯模式才顯示）*/}
      {isEditing ? (
        <>
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
                renderItem={(file: any) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                      title={file.name}
                      description={`${(file.size / 1024).toFixed(1)} KB`}
                    />
                  </List.Item>
                )}
              />
              <p style={{ color: '#999', fontSize: 12, marginTop: 8, marginBottom: 0 }}>
                點擊上方「儲存」按鈕後開始上傳
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
                strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                strokeWidth={12}
              />
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
        </>
      ) : (
        attachments.length === 0 && (
          <Empty description="此公文尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )
      )}
    </Spin>
  );

  // 搜尋派工紀錄的狀態
  const [dispatchSearch, setDispatchSearch] = useState('');
  const [selectedDispatchId, setSelectedDispatchId] = useState<number | undefined>();
  const [linkingDispatch, setLinkingDispatch] = useState(false);

  // 查詢可關聯的派工紀錄（排除已關聯的）
  const { data: availableDispatches } = useQuery({
    queryKey: ['dispatch-orders-for-link', dispatchSearch],
    queryFn: async () => {
      const result = await dispatchOrdersApi.getList({
        search: dispatchSearch || undefined,
        page: 1,
        limit: 50,
      });
      return result;
    },
    enabled: isEditing,
  });

  // 查詢可關聯的工程（排除已關聯的）
  const { data: availableProjects } = useQuery({
    queryKey: ['projects-for-link', projectSearch],
    queryFn: async () => {
      const result = await taoyuanProjectsApi.getList({
        search: projectSearch || undefined,
        page: 1,
        limit: 50,
      });
      return result;
    },
    enabled: isEditing,
  });

  /** Tab 5: 派工安排 */
  const renderDispatchTab = () => {
    // 判斷當前公文類型 (收文/發文)
    // 注意：category 可能是中文「收文」/「發文」或英文 'receive'/'send'
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';

    // 已關聯的派工 ID 列表，用於過濾
    const linkedDispatchIds = dispatchLinks.map(link => link.dispatch_order_id);

    // 過濾掉已關聯的派工
    const filteredDispatches = (availableDispatches?.items ?? []).filter(
      (dispatch: DispatchOrder) => !linkedDispatchIds.includes(dispatch.id)
    );

    // 新增派工
    const handleCreateDispatch = async () => {
      try {
        const values = await dispatchForm.validateFields();
        const docId = parseInt(id || '0', 10);

        // 建立派工單，自動關聯當前公文
        const dispatchData: DispatchOrderCreate = {
          dispatch_no: values.dispatch_no,
          project_name: values.project_name || document?.subject || '',
          work_type: values.work_type,
          sub_case_name: values.sub_case_name,
          deadline: values.deadline,
          case_handler: values.case_handler,
          survey_unit: values.survey_unit,
          contact_note: values.contact_note,
          cloud_folder: values.cloud_folder,
          project_folder: values.project_folder,
          contract_project_id: (document as any)?.contract_project_id || undefined,
          // 自動關聯當前公文 ID
          agency_doc_id: isReceiveDoc ? docId : undefined,
          company_doc_id: !isReceiveDoc ? docId : undefined,
        };

        logger.debug('[handleCreateDispatch] 建立派工單:', dispatchData);
        const newDispatch = await dispatchOrdersApi.create(dispatchData);
        logger.debug('[handleCreateDispatch] 派工單建立成功:', newDispatch);

        if (!newDispatch || !newDispatch.id) {
          throw new Error('派工單建立失敗：未取得派工單 ID');
        }

        // 關聯到此公文
        logger.debug('[handleCreateDispatch] 建立公文關聯:', { docId, dispatchId: newDispatch.id, linkType });
        await documentLinksApi.linkDispatch(docId, newDispatch.id, linkType);
        logger.debug('[handleCreateDispatch] 公文關聯建立成功');

        message.success('派工新增成功');

        // 先重新載入關聯列表，確保資料更新
        await loadDispatchLinks();

        // 再重置表單
        dispatchForm.resetFields();

        // 刷新派工紀錄列表
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
      } catch (error: any) {
        logger.error('[handleCreateDispatch] 錯誤:', error);
        message.error(error?.message || '新增派工失敗');
      }
    };

    // 關聯已有派工
    const handleLinkExistingDispatch = async () => {
      if (!selectedDispatchId) {
        message.warning('請選擇要關聯的派工紀錄');
        return;
      }
      setLinkingDispatch(true);
      try {
        const docId = parseInt(id || '0', 10);
        await documentLinksApi.linkDispatch(docId, selectedDispatchId, linkType);
        message.success('關聯成功');
        setSelectedDispatchId(undefined);
        // 先重新載入關聯列表，確保資料更新
        await loadDispatchLinks();
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
      } catch (error: any) {
        message.error(error?.message || '關聯失敗');
      } finally {
        setLinkingDispatch(false);
      }
    };

    // 移除關聯
    const handleUnlinkDispatch = async (linkId: number) => {
      try {
        const docId = parseInt(id || '0', 10);
        await documentLinksApi.unlinkDispatch(docId, linkId);
        message.success('已移除關聯');
        // 先重新載入關聯列表，確保資料更新
        await loadDispatchLinks();
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
      } catch (error) {
        message.error('移除關聯失敗');
      }
    };

    return (
      <Spin spinning={dispatchLinksLoading}>
        {/* 已關聯派工列表 - 完整顯示派工資訊 */}
        {dispatchLinks.length > 0 && (
          <Card
            size="small"
            title={
              <Space>
                <SendOutlined />
                <span>已關聯派工（{dispatchLinks.length} 筆）</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            {dispatchLinks.map((item, index) => (
              <Card
                key={item.link_id}
                size="small"
                type="inner"
                style={{ marginBottom: index < dispatchLinks.length - 1 ? 12 : 0 }}
                title={
                  <Space>
                    <SendOutlined style={{ color: item.link_type === 'agency_incoming' ? '#1890ff' : '#52c41a' }} />
                    <Tag color={item.link_type === 'agency_incoming' ? 'blue' : 'green'}>
                      {item.dispatch_no}
                    </Tag>
                    <span>{item.project_name || '(無工程名稱)'}</span>
                    <Tag>{item.link_type === 'agency_incoming' ? '機關來函派工' : '乾坤發文派工'}</Tag>
                  </Space>
                }
                extra={
                  <Space>
                    <Button
                      type="link"
                      size="small"
                      onClick={() => navigate(`/taoyuan/dispatch/${item.dispatch_order_id}`)}
                    >
                      查看詳情
                    </Button>
                    {isEditing && (
                      <Popconfirm
                        title="確定要移除此派工關聯嗎？"
                        onConfirm={() => handleUnlinkDispatch(item.link_id)}
                        okText="確定"
                        cancelText="取消"
                      >
                        <Button type="link" size="small" danger>
                          移除關聯
                        </Button>
                      </Popconfirm>
                    )}
                  </Space>
                }
              >
                {/* 派工基本資訊 - 使用 Row/Col 布局 */}
                <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">作業類別：</Text>
                    <Text strong>{item.work_type || '-'}</Text>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">履約期限：</Text>
                    <Text strong style={{ color: '#fa8c16' }}>{item.deadline || '-'}</Text>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">建立時間：</Text>
                    <Text>{item.created_at ? dayjs(item.created_at).format('YYYY-MM-DD HH:mm') : '-'}</Text>
                  </Col>
                </Row>

                {/* 承辦資訊 */}
                <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">案件承辦：</Text>
                    <Text>{item.case_handler || '-'}</Text>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">查估單位：</Text>
                    <Text>{item.survey_unit || '-'}</Text>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Text type="secondary">分案名稱：</Text>
                    <Text>{item.sub_case_name || '-'}</Text>
                  </Col>
                </Row>

                {/* 聯絡備註 - 獨立顯示 */}
                {item.contact_note && (
                  <div style={{ marginBottom: 12, padding: '8px 12px', backgroundColor: '#fffbe6', borderRadius: 4 }}>
                    <Text type="secondary">聯絡備註：</Text>
                    <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{item.contact_note}</div>
                  </div>
                )}

                {/* 資料夾連結 */}
                <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                  <Col xs={24} sm={12}>
                    <Text type="secondary">雲端資料夾：</Text>
                    {item.cloud_folder ? (
                      <a href={item.cloud_folder} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }}>
                        {item.cloud_folder}
                      </a>
                    ) : <Text type="secondary">-</Text>}
                  </Col>
                  <Col xs={24} sm={12}>
                    <Text type="secondary">專案資料夾：</Text>
                    <Text copyable={!!item.project_folder} style={{ wordBreak: 'break-all' }}>
                      {item.project_folder || '-'}
                    </Text>
                  </Col>
                </Row>

                {/* 公文關聯 */}
                <Divider style={{ margin: '8px 0' }} />
                <Row gutter={[16, 8]}>
                  <Col xs={24} sm={12}>
                    <Text type="secondary">機關函文號：</Text>
                    <Text>{item.agency_doc_number || '-'}</Text>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Text type="secondary">乾坤函文號：</Text>
                    <Text>{item.company_doc_number || '-'}</Text>
                  </Col>
                </Row>
              </Card>
            ))}
          </Card>
        )}

        {/* 新增派工表單 - 編輯模式才顯示，排版與「新增派工單」完全一致 */}
        {isEditing && (
          <Card
            size="small"
            title={
              <Space>
                <PlusOutlined />
                <span>新增派工</span>
              </Space>
            }
          >
            <Form form={dispatchForm} layout="vertical" size="small">
              {/* 第一行：派工單號 + 工程名稱/派工事項 */}
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="dispatch_no"
                    label="派工單號"
                    rules={[{ required: true, message: '請輸入派工單號' }]}
                  >
                    <Input placeholder="例: TY-2026-001" />
                  </Form.Item>
                </Col>
                <Col span={16}>
                  <Form.Item name="project_name" label="工程名稱/派工事項">
                    <Input placeholder="派工事項說明" />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第二行：作業類別 + 分案名稱/派工備註 + 履約期限 */}
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="work_type" label="作業類別">
                    <Select allowClear placeholder="選擇作業類別">
                      {TAOYUAN_WORK_TYPES_LIST.map((type) => (
                        <Option key={type} value={type}>
                          {type}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="sub_case_name" label="分案名稱/派工備註">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="deadline" label="履約期限">
                    <Input placeholder="例: 114/12/31" />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第三行：案件承辦 + 查估單位 + 聯絡備註 */}
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="case_handler"
                    label="案件承辦"
                    tooltip="從機關承辦清單選擇"
                  >
                    <Select
                      placeholder="選擇案件承辦"
                      allowClear
                      showSearch
                      optionFilterProp="label"
                    >
                      {agencyContacts.map((contact: ProjectAgencyContact) => (
                        <Option
                          key={contact.id}
                          value={contact.contact_name}
                          label={contact.contact_name}
                        >
                          <div style={{ lineHeight: 1.4 }}>
                            <div>{contact.contact_name}</div>
                            {(contact.position || contact.department) && (
                              <Text type="secondary" style={{ fontSize: 11 }}>
                                {[contact.position, contact.department].filter(Boolean).join(' / ')}
                              </Text>
                            )}
                          </div>
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="survey_unit"
                    label="查估單位"
                    tooltip="從協力廠商清單選擇"
                  >
                    <Select
                      placeholder="選擇查估單位"
                      allowClear
                      showSearch
                      optionFilterProp="label"
                    >
                      {projectVendors.map((vendor: ProjectVendor) => (
                        <Option
                          key={vendor.vendor_id}
                          value={vendor.vendor_name}
                          label={vendor.vendor_name}
                        >
                          <div style={{ lineHeight: 1.4 }}>
                            <div>{vendor.vendor_name}</div>
                            {(vendor.role || vendor.vendor_business_type) && (
                              <Text type="secondary" style={{ fontSize: 11 }}>
                                {[vendor.role, vendor.vendor_business_type].filter(Boolean).join(' / ')}
                              </Text>
                            )}
                          </div>
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="contact_note" label="聯絡備註">
                    <Input />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第四行：雲端資料夾 + 專案資料夾 */}
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="cloud_folder" label="雲端資料夾">
                    <Input placeholder="Google Drive 連結" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="project_folder" label="專案資料夾">
                    <Input placeholder="本地路徑" />
                  </Form.Item>
                </Col>
              </Row>

              {/* 公文關聯區塊 - 自動帶入當前公文 */}
              <Divider style={{ margin: '16px 0' }} />
              <div style={{ marginBottom: 16 }}>
                <Space>
                  <FileTextOutlined />
                  <span style={{ fontWeight: 500 }}>公文關聯</span>
                  <Tag color={isReceiveDoc ? 'blue' : 'green'}>
                    {isReceiveDoc ? '收文' : '發文'}
                  </Tag>
                </Space>
              </div>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="機關函文號"
                    tooltip={isReceiveDoc ? '自動帶入當前公文文號' : '如需關聯機關函文，請至派工紀錄編輯'}
                  >
                    <Input
                      value={isReceiveDoc ? document?.doc_number : undefined}
                      disabled
                      style={{ backgroundColor: '#f5f5f5' }}
                      placeholder={isReceiveDoc ? '' : '(非機關來函)'}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="乾坤函文號"
                    tooltip={!isReceiveDoc ? '自動帶入當前公文文號' : '如需關聯乾坤函文，請至派工紀錄編輯'}
                  >
                    <Input
                      value={!isReceiveDoc ? document?.doc_number : undefined}
                      disabled
                      style={{ backgroundColor: '#f5f5f5' }}
                      placeholder={!isReceiveDoc ? '' : '(非乾坤發文)'}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
                <Button type="primary" onClick={handleCreateDispatch}>
                  建立派工
                </Button>
              </Form.Item>
            </Form>
          </Card>
        )}

        {/* 關聯已有派工 - 編輯模式才顯示 */}
        {isEditing && (
          <Card
            size="small"
            title={
              <Space>
                <LinkOutlined />
                <span>關聯已有派工</span>
              </Space>
            }
            style={{ marginTop: 16 }}
          >
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Select
                  showSearch
                  allowClear
                  placeholder="搜尋並選擇已有的派工紀錄"
                  value={selectedDispatchId}
                  onChange={setSelectedDispatchId}
                  onSearch={setDispatchSearch}
                  filterOption={false}
                  style={{ width: '100%' }}
                  notFoundContent={filteredDispatches.length === 0 ? '無可關聯的派工紀錄' : '輸入關鍵字搜尋'}
                  options={filteredDispatches.map((dispatch: DispatchOrder) => ({
                    value: dispatch.id,
                    label: (
                      <span>
                        <Tag color="blue" style={{ marginRight: 8 }}>{dispatch.dispatch_no}</Tag>
                        {dispatch.project_name || '(無工程名稱)'}
                        {dispatch.work_type && <span style={{ color: '#999', marginLeft: 8 }}>- {dispatch.work_type}</span>}
                      </span>
                    ),
                  }))}
                />
              </Col>
              <Col>
                <Button
                  type="primary"
                  icon={<LinkOutlined />}
                  onClick={handleLinkExistingDispatch}
                  loading={linkingDispatch}
                  disabled={!selectedDispatchId}
                >
                  關聯
                </Button>
              </Col>
            </Row>
            <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              提示：選擇已存在的派工紀錄進行關聯，該派工的「{isReceiveDoc ? '機關函文號' : '乾坤函文號'}」將自動更新為當前公文文號
            </div>
          </Card>
        )}

        {/* 非編輯模式提示 */}
        {!isEditing && dispatchLinks.length === 0 && (
          <Empty
            description="此公文尚無關聯派工"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Text type="secondary">點擊右上方「編輯」按鈕可新增派工關聯</Text>
          </Empty>
        )}
      </Spin>
    );
  };

  /** Tab 6: 工程關聯 */
  const renderProjectLinkTab = () => {
    // 判斷當前公文類型 (收文/發文)
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';

    // 已關聯的工程 ID 列表，用於過濾
    const linkedProjectIds = projectLinks.map(link => link.project_id);

    // 過濾掉已關聯的工程
    const filteredProjects = (availableProjects?.items ?? []).filter(
      (project: TaoyuanProject) => !linkedProjectIds.includes(project.id)
    );

    // 關聯已有工程
    const handleLinkExistingProject = async () => {
      if (!selectedProjectId) {
        message.warning('請選擇要關聯的工程');
        return;
      }
      setLinkingProject(true);
      try {
        const docId = parseInt(id || '0', 10);
        await documentProjectLinksApi.linkProject(docId, selectedProjectId, linkType);
        message.success('關聯成功');
        setSelectedProjectId(undefined);
        loadProjectLinks();
        queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
      } catch (error: any) {
        message.error(error?.message || '關聯失敗');
      } finally {
        setLinkingProject(false);
      }
    };

    // 移除關聯
    const handleUnlinkProject = async (linkId: number) => {
      try {
        const docId = parseInt(id || '0', 10);
        await documentProjectLinksApi.unlinkProject(docId, linkId);
        message.success('已移除關聯');
        loadProjectLinks();
        queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
      } catch (error) {
        message.error('移除關聯失敗');
      }
    };

    return (
      <Spin spinning={projectLinksLoading}>
        {/* 已關聯工程列表 - 完整顯示工程資訊 */}
        {projectLinks.length > 0 && (
          <Card
            size="small"
            title={
              <Space>
                <EnvironmentOutlined />
                <span>已關聯工程（{projectLinks.length} 筆）</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            {projectLinks.map((item, index) => (
              <Card
                key={item.link_id}
                size="small"
                type="inner"
                style={{ marginBottom: index < projectLinks.length - 1 ? 12 : 0 }}
                title={
                  <Space>
                    <EnvironmentOutlined style={{ color: '#52c41a' }} />
                    <Tag color="green">{item.district || '未分區'}</Tag>
                    <span>{item.project_name || '(無工程名稱)'}</span>
                    <Tag>{item.link_type === 'agency_incoming' ? '機關來函' : '乾坤發文'}</Tag>
                  </Space>
                }
                extra={
                  isEditing && (
                    <Popconfirm
                      title="確定要移除此工程關聯嗎？"
                      onConfirm={() => handleUnlinkProject(item.link_id)}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button type="link" size="small" danger>
                        移除關聯
                      </Button>
                    </Popconfirm>
                  )
                }
              >
                <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} bordered>
                  <Descriptions.Item label="審議年度">{item.review_year || '-'}</Descriptions.Item>
                  <Descriptions.Item label="案件類型">{item.case_type || '-'}</Descriptions.Item>
                  <Descriptions.Item label="行政區">{item.district || '-'}</Descriptions.Item>
                  <Descriptions.Item label="分案名稱">{item.sub_case_name || '-'}</Descriptions.Item>
                  <Descriptions.Item label="案件承辦">{item.case_handler || '-'}</Descriptions.Item>
                  <Descriptions.Item label="查估單位">{item.survey_unit || '-'}</Descriptions.Item>
                  <Descriptions.Item label="工程起點">{item.start_point || '-'}</Descriptions.Item>
                  <Descriptions.Item label="工程迄點">{item.end_point || '-'}</Descriptions.Item>
                  <Descriptions.Item label="道路長度">
                    {item.road_length ? `${item.road_length} 公尺` : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="現況路寬">
                    {item.current_width ? `${item.current_width} 公尺` : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="計畫路寬">
                    {item.planned_width ? `${item.planned_width} 公尺` : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="審議結果">{item.review_result || '-'}</Descriptions.Item>
                  {item.notes && (
                    <Descriptions.Item label="關聯備註" span={3}>{item.notes}</Descriptions.Item>
                  )}
                  <Descriptions.Item label="關聯時間">
                    {item.created_at ? dayjs(item.created_at).format('YYYY-MM-DD HH:mm') : '-'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ))}
          </Card>
        )}

        {/* 關聯已有工程 - 編輯模式才顯示 */}
        {isEditing && (
          <Card
            size="small"
            title={
              <Space>
                <LinkOutlined />
                <span>關聯已有工程</span>
              </Space>
            }
          >
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Select
                  showSearch
                  allowClear
                  placeholder="搜尋並選擇已有的工程"
                  value={selectedProjectId}
                  onChange={setSelectedProjectId}
                  onSearch={setProjectSearch}
                  filterOption={false}
                  style={{ width: '100%' }}
                  notFoundContent={filteredProjects.length === 0 ? '無可關聯的工程' : '輸入關鍵字搜尋'}
                  options={filteredProjects.map((project: TaoyuanProject) => ({
                    value: project.id,
                    label: (
                      <span>
                        <Tag color="green" style={{ marginRight: 8 }}>{project.district || '未分區'}</Tag>
                        {project.project_name || '(無工程名稱)'}
                        {project.review_year && <span style={{ color: '#999', marginLeft: 8 }}>- {project.review_year}年度</span>}
                      </span>
                    ),
                  }))}
                />
              </Col>
              <Col>
                <Button
                  type="primary"
                  icon={<LinkOutlined />}
                  onClick={handleLinkExistingProject}
                  loading={linkingProject}
                  disabled={!selectedProjectId}
                >
                  關聯
                </Button>
              </Col>
            </Row>
            <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              提示：選擇已存在的工程進行關聯，建立公文與工程的直接對應關係
            </div>
          </Card>
        )}

        {/* 非編輯模式提示 */}
        {!isEditing && projectLinks.length === 0 && (
          <Empty
            description="此公文尚無關聯工程"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Text type="secondary">點擊右上方「編輯」按鈕可新增工程關聯</Text>
          </Empty>
        )}
      </Spin>
    );
  };

  // =============================================================================
  // Tab 配置
  // =============================================================================

  const tabs = [
    createTabItem(
      'info',
      { icon: <FileTextOutlined />, text: '公文資訊' },
      renderInfoTab()
    ),
    createTabItem(
      'date-status',
      { icon: <CalendarOutlined />, text: '日期狀態' },
      renderDateStatusTab()
    ),
    createTabItem(
      'case-staff',
      { icon: <TeamOutlined />, text: '承案人資' },
      renderCaseStaffTab()
    ),
    createTabItem(
      'attachments',
      { icon: <PaperClipOutlined />, text: '附件紀錄', count: attachments.length },
      renderAttachmentsTab()
    ),
    createTabItem(
      'dispatch',
      { icon: <SendOutlined />, text: '派工安排', count: dispatchLinks.length },
      renderDispatchTab()
    ),
    createTabItem(
      'project-link',
      { icon: <EnvironmentOutlined />, text: '工程關聯', count: projectLinks.length },
      renderProjectLinkTab()
    ),
  ];

  // =============================================================================
  // Header 配置
  // =============================================================================

  const headerConfig = {
    title: document?.subject || '公文詳情',
    icon: <FileTextOutlined />,
    backText: '返回公文列表',
    backPath: '/documents',
    tags: document ? [
      { text: document.doc_type || '函', color: getTagColor(document.doc_type, DOC_TYPE_OPTIONS, 'blue') },
      { text: document.status || '未設定', color: getTagColor(document.status, STATUS_OPTIONS, 'default') },
    ] : [],
    extra: (
      <Space>
        {isEditing ? (
          <>
            <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              儲存
            </Button>
          </>
        ) : (
          <>
            <Button
              icon={<CalendarOutlined />}
              onClick={handleAddToCalendar}
            >
              加入行事曆
            </Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => setIsEditing(true)}
            >
              編輯
            </Button>
            <Popconfirm
              title="確定要刪除此公文嗎？"
              description="刪除後將無法復原，請確認是否繼續。"
              onConfirm={handleDelete}
              okText="確定刪除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button
                danger
                icon={<DeleteOutlined />}
              >
                刪除
              </Button>
            </Popconfirm>
          </>
        )}
      </Space>
    ),
  };

  // =============================================================================
  // 渲染
  // =============================================================================

  return (
    <>
      <DetailPageLayout
        header={headerConfig}
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        loading={loading}
        hasData={!!document}
      />

      {/* 整合式事件建立模態框 */}
      <IntegratedEventModal
        visible={showIntegratedEventModal}
        document={document ? {
          id: document.id,
          doc_number: document.doc_number,
          subject: document.subject,
          doc_date: document.doc_date,
          send_date: document.send_date,
          receive_date: document.receive_date,
          sender: document.sender,
          receiver: document.receiver,
          assignee: (document as any).assignee,
          priority_level: String((document as any).priority || 3),
          doc_type: document.doc_type,
          content: document.content,
          notes: (document as any).notes,
          contract_case: (document as any).contract_project_name || undefined
        } : null}
        onClose={() => setShowIntegratedEventModal(false)}
        onSuccess={handleEventCreated}
      />
    </>
  );
};

export default DocumentDetailPage;
