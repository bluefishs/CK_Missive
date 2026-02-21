/**
 * useDocumentDetail - 公文詳情頁面狀態管理與事件處理 Hook
 *
 * 從 DocumentDetailPage.tsx 提取，封裝所有 state、data loading、event handlers。
 *
 * @version 1.0.0
 * @date 2026-02-19
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Form, App } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../../config/queryConfig';
import dayjs from 'dayjs';

// API
import { documentsApi } from '../../../api/documentsApi';
import { filesApi } from '../../../api/filesApi';
import { apiClient } from '../../../api/client';
import {
  dispatchOrdersApi,
  documentLinksApi,
  documentProjectLinksApi,
  taoyuanProjectsApi,
} from '../../../api/taoyuanDispatchApi';
import { getProjectAgencyContacts } from '../../../api/projectAgencyContacts';
import { projectVendorsApi } from '../../../api/projectVendorsApi';
import type { ProjectVendor } from '../../../api/projectVendorsApi';

// 類型
import { Document } from '../../../types';
import type {
  DispatchOrderCreate, LinkType, ProjectStaff, Project, User,
} from '../../../types/api';
import { isReceiveDocument } from '../../../types/api';
import type { DocumentAttachment } from '../../../types/document';
import type {
  DispatchOrder, DocumentDispatchLink, DocumentProjectLink, TaoyuanProject,
} from '../../../types/taoyuan';
import type { ProjectAgencyContact } from '../../../types/admin-system';
import type { UploadFile } from 'antd/es/upload';

// 常數 & 工具
import { DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_MAX_FILE_SIZE_MB } from '../tabs';
import { logger } from '../../../utils/logger';
import { TAOYUAN_CONTRACT } from '../../../constants/taoyuanOptions';
import { hasProjectFeature } from '../../../config/projectModules';

export interface UseDocumentDetailReturn {
  // State
  document: Document | null;
  loading: boolean;
  saving: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isEditing: boolean;
  setIsEditing: (editing: boolean) => void;
  // Attachments
  attachments: DocumentAttachment[];
  attachmentsLoading: boolean;
  fileList: UploadFile[];
  setFileList: (files: UploadFile[]) => void;
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  setUploadErrors: (errors: string[]) => void;
  fileSettings: { allowedExtensions: string[]; maxFileSizeMB: number };
  // Cases & Users
  cases: Project[];
  casesLoading: boolean;
  users: User[];
  usersLoading: boolean;
  projectStaffMap: Record<number, ProjectStaff[]>;
  staffLoading: boolean;
  selectedContractProjectId: number | null;
  currentAssigneeValues: string[];
  // Dispatch & Project links
  dispatchLinks: DocumentDispatchLink[];
  dispatchLinksLoading: boolean;
  projectLinks: DocumentProjectLink[];
  projectLinksLoading: boolean;
  // Feature flags
  hasDispatchFeature: boolean;
  hasProjectLinkFeature: boolean;
  // Query data
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
  availableDispatches: DispatchOrder[];
  availableProjects: TaoyuanProject[];
  // Calendar modal
  showIntegratedEventModal: boolean;
  setShowIntegratedEventModal: (show: boolean) => void;
  // Handlers
  handleProjectChange: (projectId: number | null | undefined) => Promise<void>;
  handleSave: () => Promise<void>;
  handleCancelEdit: () => void;
  handleDelete: () => Promise<void>;
  handleAddToCalendar: () => void;
  handleEventCreated: (eventId: number) => void;
  handleDownload: (attachmentId: number, filename: string) => Promise<void>;
  handlePreview: (attachmentId: number, filename: string) => Promise<void>;
  handleDeleteAttachment: (attachmentId: number) => Promise<void>;
  handleCreateDispatch: (formValues: Record<string, unknown>) => Promise<void>;
  handleLinkDispatch: (dispatchId: number) => Promise<void>;
  handleUnlinkDispatch: (linkId: number) => Promise<void>;
  handleLinkProject: (projectId: number) => Promise<void>;
  handleUnlinkProject: (linkId: number) => Promise<void>;
  // Form
  form: ReturnType<typeof Form.useForm>[0];
  // Navigation
  returnTo: string | undefined;
}

export function useDocumentDetail(): UseDocumentDetailReturn {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 從 state 讀取返回路徑（支援從函文紀錄等頁面返回）
  const returnTo = (location.state as { returnTo?: string })?.returnTo;

  // 基本狀態
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [document, setDocument] = useState<Document | null>(null);
  const [activeTab, setActiveTab] = useState('info');
  const [isEditing, setIsEditing] = useState(false);

  // 附件相關狀態
  const [attachments, setAttachments] = useState<DocumentAttachment[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [fileSettings, setFileSettings] = useState({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  // 下拉選項資料
  const [cases, setCases] = useState<Project[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, ProjectStaff[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedContractProjectId, setSelectedContractProjectId] = useState<number | null>(null);
  const projectStaffCacheRef = useRef<Record<number, ProjectStaff[]>>({});
  const [currentAssigneeValues, setCurrentAssigneeValues] = useState<string[]>([]);

  // 派工安排相關狀態
  const [dispatchLinks, setDispatchLinks] = useState<DocumentDispatchLink[]>([]);
  const [dispatchLinksLoading, setDispatchLinksLoading] = useState(false);

  // 工程關聯相關狀態
  const [projectLinks, setProjectLinks] = useState<DocumentProjectLink[]>([]);
  const [projectLinksLoading, setProjectLinksLoading] = useState(false);

  // 行事曆模態框
  const [showIntegratedEventModal, setShowIntegratedEventModal] = useState(false);

  // =============================================================================
  // 案件功能模組判斷
  // =============================================================================

  // 判斷是否為有派工功能的案件 (根據 contract_project_id)
  const hasDispatchFeature = hasProjectFeature(
    document?.contract_project_id,
    'dispatch-management'
  );
  const hasProjectLinkFeature = hasProjectFeature(
    document?.contract_project_id,
    'project-linking'
  );

  // =============================================================================
  // 桃園派工專屬 API 查詢 (僅在有權限時啟用)
  // =============================================================================

  // 查詢機關承辦清單
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
    enabled: isEditing && hasDispatchFeature,
  });
  const agencyContacts = useMemo(
    () => agencyContactsData?.items ?? [],
    [agencyContactsData?.items]
  );

  // 查詢協力廠商清單
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
    enabled: isEditing && hasDispatchFeature,
  });
  const projectVendors = useMemo(
    () => vendorsData?.associations ?? [],
    [vendorsData?.associations]
  );

  // 查詢可關聯的派工紀錄
  const { data: availableDispatchesData } = useQuery({
    queryKey: ['dispatch-orders-for-link'],
    queryFn: () => dispatchOrdersApi.getList({ page: 1, limit: 50 }),
    enabled: isEditing && hasDispatchFeature,
  });
  const availableDispatches = useMemo(
    () => availableDispatchesData?.items ?? [],
    [availableDispatchesData?.items]
  );

  // 查詢可關聯的工程 (僅桃園案件)
  const { data: availableProjectsData } = useQuery({
    queryKey: ['projects-for-link'],
    queryFn: () => taoyuanProjectsApi.getList({ page: 1, limit: 50 }),
    enabled: isEditing && hasProjectLinkFeature,
  });
  const availableProjects = useMemo(
    () => availableProjectsData?.items ?? [],
    [availableProjectsData?.items]
  );

  // =============================================================================
  // 資料載入函數
  // =============================================================================

  const loadDispatchLinks = useCallback(async () => {
    if (!id) return;
    setDispatchLinksLoading(true);
    try {
      const docId = parseInt(id, 10);
      logger.info('[loadDispatchLinks] 開始載入', { docId });
      const result = await documentLinksApi.getDispatchLinks(docId);
      logger.info('[loadDispatchLinks] API 回應', {
        success: result.success,
        document_id: result.document_id,
        total: result.total,
        dispatch_orders_count: result.dispatch_orders?.length || 0,
      });
      setDispatchLinks(result.dispatch_orders || []);
    } catch (error) {
      logger.error('[loadDispatchLinks] 載入派工關聯失敗:', error);
      // 重要：錯誤時不清空現有列表，避免「紀錄消失」問題
      // setDispatchLinks([]); // 移除這行
      message.error('載入派工關聯失敗，請重新整理頁面');
    } finally {
      setDispatchLinksLoading(false);
    }
  }, [id]);

  const loadProjectLinks = useCallback(async () => {
    if (!id) return;
    setProjectLinksLoading(true);
    try {
      const docId = parseInt(id, 10);
      const result = await documentProjectLinksApi.getProjectLinks(docId);
      setProjectLinks(result.projects || []);
    } catch (error) {
      logger.error('載入工程關聯失敗:', error);
      // 重要：錯誤時不清空現有列表，避免「紀錄消失」問題
      // setProjectLinks([]);
      message.error('載入工程關聯失敗，請重新整理頁面');
    } finally {
      setProjectLinksLoading(false);
    }
  }, [id, message]);

  const fetchProjectStaff = async (projectId: number): Promise<ProjectStaff[]> => {
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
  };

  // 待設置的表單值（延遲到 loading 結束後設置）
  const [pendingFormValues, setPendingFormValues] = useState<Record<string, any> | null>(null);

  // 當 loading 結束且有待設置的值時，設置表單
  useEffect(() => {
    if (!loading && pendingFormValues) {
      form.setFieldsValue(pendingFormValues);
      setPendingFormValues(null);
    }
  }, [loading, pendingFormValues, form]);

  const loadDocument = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const docId = parseInt(id, 10);
      const doc = await documentsApi.getDocument(docId);
      setDocument(doc);

      let assigneeArray: string[] = [];
      const rawAssignee = (doc as any).assignee;
      if (rawAssignee) {
        if (Array.isArray(rawAssignee)) {
          assigneeArray = rawAssignee;
        } else if (typeof rawAssignee === 'string') {
          assigneeArray = rawAssignee.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
      }
      setCurrentAssigneeValues(assigneeArray);

      // 延遲設置表單值，等待 Form 組件渲染完成
      setPendingFormValues({
        ...doc,
        doc_date: doc.doc_date ? dayjs(doc.doc_date) : null,
        receive_date: doc.receive_date ? dayjs(doc.receive_date) : null,
        send_date: doc.send_date ? dayjs(doc.send_date) : null,
        assignee: assigneeArray,
      });

      const projectId = (doc as any).contract_project_id;
      if (projectId) {
        setSelectedContractProjectId(projectId);
        const staffList = await fetchProjectStaff(projectId);
        if ((!assigneeArray || assigneeArray.length === 0) && staffList && staffList.length > 0) {
          const staffNames = staffList.map((s: ProjectStaff) => s.user_name).filter((name): name is string => !!name);
          // 更新待設置值中的 assignee
          setPendingFormValues(prev => prev ? { ...prev, assignee: staffNames } : null);
          setCurrentAssigneeValues(staffNames);
        }
      }

      // 載入附件
      setAttachmentsLoading(true);
      try {
        const atts = await filesApi.getDocumentAttachments(docId);
        setAttachments(atts);
      } finally {
        setAttachmentsLoading(false);
      }
    } catch (error) {
      logger.error('載入公文失敗:', error);
      message.error('載入公文失敗');
      setDocument(null);
    } finally {
      setLoading(false);
    }
  }, [id, message, form]);

  const loadCases = async () => {
    setCasesLoading(true);
    try {
      const data = await apiClient.post<{ projects?: Project[]; items?: Project[] }>(
        '/projects/list',
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
  };

  const loadUsers = async () => {
    setUsersLoading(true);
    try {
      const data = await apiClient.post<{ users?: User[]; items?: User[] }>(
        '/users/list',
        { page: 1, limit: 100 }
      );
      const usersData = data.users || data.items || [];
      setUsers(Array.isArray(usersData) ? usersData : []);
    } catch (error) {
      logger.error('[loadUsers] 載入使用者失敗:', error);
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  };

  const loadFileSettings = async () => {
    try {
      const info = await filesApi.getStorageInfo();
      setFileSettings({
        allowedExtensions: info.allowed_extensions,
        maxFileSizeMB: info.max_file_size_mb,
      });
    } catch (error) {
      logger.warn('載入檔案設定失敗，使用預設值:', error);
    }
  };

  // 初始載入 (通用資料)
  useEffect(() => {
    loadDocument();
    loadCases();
    loadUsers();
    loadFileSettings();
  }, [loadDocument]);

  // 條件載入派工/工程關聯資料 (依賴 document 載入後的功能判斷)
  useEffect(() => {
    if (document) {
      // 僅在有派工功能時載入派工關聯
      if (hasDispatchFeature) {
        loadDispatchLinks();
      }
      // 僅在有工程關聯功能時載入工程關聯
      if (hasProjectLinkFeature) {
        loadProjectLinks();
      }
    }
  }, [document, hasDispatchFeature, hasProjectLinkFeature, loadDispatchLinks, loadProjectLinks]);


  // =============================================================================
  // 事件處理
  // =============================================================================

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
        const names = currentStaff.map((s: ProjectStaff) => s.user_name).filter((name): name is string => !!name);
        form.setFieldsValue({ assignee: names });
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

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

      await documentsApi.updateDocument(parseInt(id!, 10), documentData);

      // 上傳新附件
      if (fileList.length > 0) {
        const fileObjects = fileList
          .map(f => f.originFileObj)
          .filter((f): f is NonNullable<typeof f> => f !== undefined) as File[];
        if (fileObjects.length > 0) {
          setUploading(true);
          try {
            const result = await filesApi.uploadFiles(parseInt(id!, 10), fileObjects, {
              onProgress: (percent) => setUploadProgress(percent),
            });
            if (result.errors && result.errors.length > 0) {
              setUploadErrors(result.errors);
            }
          } finally {
            setUploading(false);
          }
        }
        setFileList([]);
      }

      message.success('儲存成功');
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
      await loadDocument();
      await loadDispatchLinks();
      setIsEditing(false);
    } catch (error) {
      logger.error('儲存失敗:', error);
      message.error('儲存失敗');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setFileList([]);
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

  const handleDelete = async () => {
    if (!document || !id) return;
    try {
      await documentsApi.deleteDocument(parseInt(id, 10));
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
      message.success('公文刪除成功');
      navigate(returnTo || '/documents');
    } catch (error) {
      logger.error('刪除公文失敗:', error);
      message.error('刪除公文失敗');
    }
  };

  const handleAddToCalendar = () => {
    if (!document) return;
    setShowIntegratedEventModal(true);
  };

  const handleEventCreated = (eventId: number) => {
    message.success('行事曆事件建立成功');
    logger.debug('[handleEventCreated] 新建事件 ID:', eventId);
    // 刷新行事曆相關的 React Query 緩存，確保新事件在行事曆頁面顯示
    queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
  };

  // 附件操作
  const handleDownload = async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename);
    } catch (error) {
      logger.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  };

  const handlePreview = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      logger.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  const handleDeleteAttachment = async (attachmentId: number) => {
    try {
      await filesApi.deleteAttachment(attachmentId);
      message.success('附件刪除成功');
      if (id) {
        const atts = await filesApi.getDocumentAttachments(parseInt(id, 10));
        setAttachments(atts);
      }
    } catch (error) {
      logger.error('刪除附件失敗:', error);
      message.error('附件刪除失敗');
    }
  };

  // 派工操作
  const handleCreateDispatch = async (formValues: Record<string, unknown>) => {
    try {
      const docId = parseInt(id || '0', 10);
      const isReceiveDoc = isReceiveDocument(document?.category);

      logger.info('[handleCreateDispatch] 開始建立派工', {
        docId,
        isReceiveDoc,
        category: document?.category,
      });

      // work_type 是多選欄位，需轉換為逗號分隔字符串
      const workTypeString = Array.isArray(formValues.work_type)
        ? formValues.work_type.join(', ')
        : formValues.work_type as string | undefined;

      const dispatchData: DispatchOrderCreate = {
        dispatch_no: formValues.dispatch_no as string,
        project_name: (formValues.project_name as string) || document?.subject || '',
        work_type: workTypeString,
        sub_case_name: formValues.sub_case_name as string | undefined,
        deadline: formValues.deadline as string | undefined,
        case_handler: formValues.case_handler as string | undefined,
        survey_unit: formValues.survey_unit as string | undefined,
        contact_note: formValues.contact_note as string | undefined,
        cloud_folder: formValues.cloud_folder as string | undefined,
        project_folder: formValues.project_folder as string | undefined,
        contract_project_id: (document as any)?.contract_project_id || undefined,
        // 傳入公文 ID，後端 _sync_document_links 會自動建立關聯
        agency_doc_id: isReceiveDoc ? docId : undefined,
        company_doc_id: !isReceiveDoc ? docId : undefined,
      };

      logger.info('[handleCreateDispatch] 發送請求', { dispatchData });

      const newDispatch = await dispatchOrdersApi.create(dispatchData);
      logger.info('[handleCreateDispatch] API 回應', { newDispatch });

      if (newDispatch && newDispatch.id) {
        // 注意: 不需要再調用 linkDispatch，因為後端 create 時已經自動同步公文關聯
        message.success('派工新增成功');
        logger.info('[handleCreateDispatch] 準備重新載入關聯');

        // 短暫延遲確保後端事務完成，避免競態條件
        await new Promise(resolve => setTimeout(resolve, 300));

        // 失效所有相關快取，確保前端獲取最新資料
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
        queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
        queryClient.invalidateQueries({ queryKey: ['document-dispatch-links'] });
        queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });

        // 重新載入關聯資料
        await loadDispatchLinks();
        logger.info('[handleCreateDispatch] 關聯載入完成', { dispatchLinksCount: dispatchLinks.length });
      } else {
        logger.warn('[handleCreateDispatch] API 回應無 id', { newDispatch });
      }
    } catch (error: unknown) {
      logger.error('[handleCreateDispatch] 錯誤:', error);
      const errorMessage = error instanceof Error ? error.message : '新增派工失敗';
      message.error(errorMessage);
      // 重新拋出錯誤，讓子元件知道操作失敗（避免表單被清空）
      throw error;
    }
  };

  const handleLinkDispatch = async (dispatchId: number) => {
    const docId = parseInt(id || '0', 10);
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';
    await documentLinksApi.linkDispatch(docId, dispatchId, linkType);
    message.success('關聯成功');
    await loadDispatchLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
  };

  const handleUnlinkDispatch = async (linkId: number) => {
    const docId = parseInt(id || '0', 10);
    await documentLinksApi.unlinkDispatch(docId, linkId);
    message.success('已移除關聯');
    await loadDispatchLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allDispatches });
  };

  // 工程關聯操作
  const handleLinkProject = async (projectId: number) => {
    const docId = parseInt(id || '0', 10);
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';
    await documentProjectLinksApi.linkProject(docId, projectId, linkType);
    message.success('關聯成功');
    await loadProjectLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allProjects });
  };

  const handleUnlinkProject = async (linkId: number) => {
    const docId = parseInt(id || '0', 10);
    await documentProjectLinksApi.unlinkProject(docId, linkId);
    message.success('已移除關聯');
    await loadProjectLinks();
    queryClient.invalidateQueries({ queryKey: queryKeys.documentRelations.allProjects });
  };

  return {
    // State
    document,
    loading,
    saving,
    activeTab,
    setActiveTab,
    isEditing,
    setIsEditing,
    // Attachments
    attachments,
    attachmentsLoading,
    fileList,
    setFileList,
    uploading,
    uploadProgress,
    uploadErrors,
    setUploadErrors,
    fileSettings,
    // Cases & Users
    cases,
    casesLoading,
    users,
    usersLoading,
    projectStaffMap,
    staffLoading,
    selectedContractProjectId,
    currentAssigneeValues,
    // Dispatch & Project links
    dispatchLinks,
    dispatchLinksLoading,
    projectLinks,
    projectLinksLoading,
    // Feature flags
    hasDispatchFeature,
    hasProjectLinkFeature,
    // Query data
    agencyContacts,
    projectVendors,
    availableDispatches,
    availableProjects,
    // Calendar modal
    showIntegratedEventModal,
    setShowIntegratedEventModal,
    // Handlers
    handleProjectChange,
    handleSave,
    handleCancelEdit,
    handleDelete,
    handleAddToCalendar,
    handleEventCreated,
    handleDownload,
    handlePreview,
    handleDeleteAttachment,
    handleCreateDispatch,
    handleLinkDispatch,
    handleUnlinkDispatch,
    handleLinkProject,
    handleUnlinkProject,
    // Form
    form,
    // Navigation
    returnTo,
  };
}
