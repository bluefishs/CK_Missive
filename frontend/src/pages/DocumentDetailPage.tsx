/**
 * 公文詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構：
 * - 公文資訊：發文形式（發文）/文件類型（收文）、字號、發文/受文機關、主旨、說明
 * - 日期狀態：發文/收文/發送日期、優先等級、處理狀態
 * - 承案人資：承攬案件、業務同仁、備註
 * - 附件紀錄：附件上傳與管理
 * - 派工安排：派工建立與關聯
 * - 工程關聯：工程關聯管理
 *
 * @version 3.0.0 - 重構為模組化 Tab 元件
 * @date 2026-01-23
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Form,
  Button,
  App,
  Space,
  Popconfirm,
} from 'antd';
import {
  FileTextOutlined,
  CalendarOutlined,
  TeamOutlined,
  PaperClipOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
  SendOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../config/queryConfig';
import dayjs from 'dayjs';

// API
import { documentsApi } from '../api/documentsApi';
import { filesApi } from '../api/filesApi';
import { apiClient } from '../api/client';
import {
  dispatchOrdersApi,
  documentLinksApi,
  documentProjectLinksApi,
  taoyuanProjectsApi,
} from '../api/taoyuanDispatchApi';
import { getProjectAgencyContacts } from '../api/projectAgencyContacts';
import { projectVendorsApi } from '../api/projectVendorsApi';

// 類型
import { Document } from '../types';
import type { DispatchOrderCreate, LinkType, ProjectStaff, Project, User } from '../types/api';
import { isReceiveDocument } from '../types/api';

// 元件
import {
  DetailPageLayout,
  createTabItem,
  getTagColor,
} from '../components/common/DetailPage';
import { IntegratedEventModal } from '../components/calendar/IntegratedEventModal';

// Tab 元件
import {
  DocumentInfoTab,
  DocumentDateStatusTab,
  DocumentCaseStaffTab,
  DocumentAttachmentsTab,
  DocumentDispatchTab,
  DocumentProjectLinkTab,
  DOC_TYPE_OPTIONS,
  STATUS_OPTIONS,
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
} from './document/tabs';

// 工具
import { logger } from '../utils/logger';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';
import { hasProjectFeature } from '../config/projectModules';

export const DocumentDetailPage: React.FC = () => {
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
  const [attachments, setAttachments] = useState<any[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [fileSettings, setFileSettings] = useState({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  // 下拉選項資料
  const [cases, setCases] = useState<any[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [users, setUsers] = useState<any[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, any[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedContractProjectId, setSelectedContractProjectId] = useState<number | null>(null);
  const projectStaffCacheRef = React.useRef<Record<number, any[]>>({});
  const [currentAssigneeValues, setCurrentAssigneeValues] = useState<string[]>([]);

  // 派工安排相關狀態
  const [dispatchLinks, setDispatchLinks] = useState<any[]>([]);
  const [dispatchLinksLoading, setDispatchLinksLoading] = useState(false);

  // 工程關聯相關狀態
  const [projectLinks, setProjectLinks] = useState<any[]>([]);
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
  const agencyContacts = agencyContactsData?.items ?? [];

  // 查詢協力廠商清單
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
    enabled: isEditing && hasDispatchFeature,
  });
  const projectVendors = vendorsData?.associations ?? [];

  // 查詢可關聯的派工紀錄
  const { data: availableDispatchesData } = useQuery({
    queryKey: ['dispatch-orders-for-link'],
    queryFn: () => dispatchOrdersApi.getList({ page: 1, limit: 50 }),
    enabled: isEditing && hasDispatchFeature,
  });
  const availableDispatches = availableDispatchesData?.items ?? [];

  // 查詢可關聯的工程 (僅桃園案件)
  const { data: availableProjectsData } = useQuery({
    queryKey: ['projects-for-link'],
    queryFn: () => taoyuanProjectsApi.getList({ page: 1, limit: 50 }),
    enabled: isEditing && hasProjectLinkFeature,
  });
  const availableProjects = availableProjectsData?.items ?? [];

  // =============================================================================
  // 資料載入函數
  // =============================================================================

  const loadDispatchLinks = useCallback(async () => {
    if (!id) return;
    setDispatchLinksLoading(true);
    try {
      const docId = parseInt(id, 10);
      const result = await documentLinksApi.getDispatchLinks(docId);
      setDispatchLinks(result.dispatch_orders || []);
    } catch (error) {
      logger.error('[loadDispatchLinks] 載入派工關聯失敗:', error);
      setDispatchLinks([]);
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
      setProjectLinks([]);
    } finally {
      setProjectLinksLoading(false);
    }
  }, [id]);

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
  const [pendingFormValues, setPendingFormValues] = React.useState<Record<string, any> | null>(null);

  // 當 loading 結束且有待設置的值時，設置表單
  React.useEffect(() => {
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
        const fileObjects: File[] = fileList
          .map(f => f.originFileObj)
          .filter((f): f is File => f !== undefined);
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
    queryClient.invalidateQueries({ queryKey: ['dashboardCalendar'] });
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
      const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';

      const dispatchData: DispatchOrderCreate = {
        dispatch_no: formValues.dispatch_no as string,
        project_name: (formValues.project_name as string) || document?.subject || '',
        work_type: formValues.work_type as string | undefined,
        sub_case_name: formValues.sub_case_name as string | undefined,
        deadline: formValues.deadline as string | undefined,
        case_handler: formValues.case_handler as string | undefined,
        survey_unit: formValues.survey_unit as string | undefined,
        contact_note: formValues.contact_note as string | undefined,
        cloud_folder: formValues.cloud_folder as string | undefined,
        project_folder: formValues.project_folder as string | undefined,
        contract_project_id: (document as any)?.contract_project_id || undefined,
        agency_doc_id: isReceiveDoc ? docId : undefined,
        company_doc_id: !isReceiveDoc ? docId : undefined,
      };

      const newDispatch = await dispatchOrdersApi.create(dispatchData);
      if (newDispatch && newDispatch.id) {
        await documentLinksApi.linkDispatch(docId, newDispatch.id, linkType);
        message.success('派工新增成功');
        await loadDispatchLinks();
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
        queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
      }
    } catch (error: unknown) {
      logger.error('[handleCreateDispatch] 錯誤:', error);
      const errorMessage = error instanceof Error ? error.message : '新增派工失敗';
      message.error(errorMessage);
    }
  };

  const handleLinkDispatch = async (dispatchId: number) => {
    const docId = parseInt(id || '0', 10);
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';
    await documentLinksApi.linkDispatch(docId, dispatchId, linkType);
    message.success('關聯成功');
    await loadDispatchLinks();
    queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
  };

  const handleUnlinkDispatch = async (linkId: number) => {
    const docId = parseInt(id || '0', 10);
    await documentLinksApi.unlinkDispatch(docId, linkId);
    message.success('已移除關聯');
    await loadDispatchLinks();
    queryClient.invalidateQueries({ queryKey: ['dispatch-orders-for-link'] });
  };

  // 工程關聯操作
  const handleLinkProject = async (projectId: number) => {
    const docId = parseInt(id || '0', 10);
    const isReceiveDoc = isReceiveDocument(document?.category);
    const linkType: LinkType = isReceiveDoc ? 'agency_incoming' : 'company_outgoing';
    await documentProjectLinksApi.linkProject(docId, projectId, linkType);
    message.success('關聯成功');
    await loadProjectLinks();
    queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
  };

  const handleUnlinkProject = async (linkId: number) => {
    const docId = parseInt(id || '0', 10);
    await documentProjectLinksApi.unlinkProject(docId, linkId);
    message.success('已移除關聯');
    await loadProjectLinks();
    queryClient.invalidateQueries({ queryKey: ['projects-for-link'] });
  };

  // =============================================================================
  // Tab 配置
  // =============================================================================

  // =============================================================================
  // 通用 Tab (所有公文都顯示)
  // =============================================================================
  const commonTabs = [
    createTabItem(
      'info',
      { icon: <FileTextOutlined />, text: '公文資訊' },
      <DocumentInfoTab form={form} document={document} isEditing={isEditing} />
    ),
    createTabItem(
      'date-status',
      { icon: <CalendarOutlined />, text: '日期狀態' },
      <DocumentDateStatusTab form={form} document={document} isEditing={isEditing} />
    ),
    createTabItem(
      'case-staff',
      { icon: <TeamOutlined />, text: '承案人資' },
      <DocumentCaseStaffTab
        form={form}
        document={document}
        isEditing={isEditing}
        cases={cases}
        casesLoading={casesLoading}
        users={users}
        usersLoading={usersLoading}
        projectStaffMap={projectStaffMap}
        staffLoading={staffLoading}
        selectedContractProjectId={selectedContractProjectId}
        currentAssigneeValues={currentAssigneeValues}
        onProjectChange={handleProjectChange}
      />
    ),
    createTabItem(
      'attachments',
      { icon: <PaperClipOutlined />, text: '附件紀錄', count: attachments.length },
      <DocumentAttachmentsTab
        documentId={id ? parseInt(id, 10) : null}
        isEditing={isEditing}
        attachments={attachments}
        attachmentsLoading={attachmentsLoading}
        fileList={fileList}
        setFileList={setFileList}
        uploading={uploading}
        uploadProgress={uploadProgress}
        uploadErrors={uploadErrors}
        setUploadErrors={setUploadErrors}
        fileSettings={fileSettings}
        onDownload={handleDownload}
        onPreview={handlePreview}
        onDelete={handleDeleteAttachment}
      />
    ),
  ];

  // =============================================================================
  // 專屬 Tab (根據案件功能模組條件顯示)
  // =============================================================================
  const projectSpecificTabs = [
    // 派工安排 Tab (僅有派工功能的案件顯示)
    ...(hasDispatchFeature ? [
      createTabItem(
        'dispatch',
        { icon: <SendOutlined />, text: '派工安排', count: dispatchLinks.length },
        <DocumentDispatchTab
          documentId={id ? parseInt(id, 10) : null}
          document={document}
          isEditing={isEditing}
          dispatchLinks={dispatchLinks}
          dispatchLinksLoading={dispatchLinksLoading}
          agencyContacts={agencyContacts}
          projectVendors={projectVendors}
          availableDispatches={availableDispatches}
          availableProjects={availableProjects}
          onCreateDispatch={handleCreateDispatch}
          onLinkDispatch={handleLinkDispatch}
          onUnlinkDispatch={handleUnlinkDispatch}
        />
      ),
    ] : []),
    // 工程關聯 Tab (僅有工程關聯功能的案件顯示)
    ...(hasProjectLinkFeature ? [
      createTabItem(
        'project-link',
        { icon: <EnvironmentOutlined />, text: '工程關聯', count: projectLinks.length },
        <DocumentProjectLinkTab
          documentId={id ? parseInt(id, 10) : null}
          document={document}
          isEditing={isEditing}
          projectLinks={projectLinks}
          projectLinksLoading={projectLinksLoading}
          availableProjects={availableProjects}
          onLinkProject={handleLinkProject}
          onUnlinkProject={handleUnlinkProject}
        />
      ),
    ] : []),
  ];

  // 合併所有 Tab
  const tabs = [...commonTabs, ...projectSpecificTabs];

  // =============================================================================
  // Header 配置
  // =============================================================================

  const headerConfig = {
    title: document?.subject || '公文詳情',
    icon: <FileTextOutlined />,
    backText: returnTo?.includes('taoyuan/dispatch/')
      ? '返回派工單'
      : returnTo?.includes('taoyuan/dispatch')
        ? '返回函文紀錄'
        : '返回公文列表',
    backPath: returnTo || '/documents',
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
              <Button danger icon={<DeleteOutlined />}>
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
