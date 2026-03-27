/**
 * useDocumentDetail - 公文詳情頁面狀態管理與事件處理 Hook
 *
 * 從 DocumentDetailPage.tsx 提取，封裝所有 state、data loading、event handlers。
 * v2.0.0 - 委派附件/關聯操作至 useDocumentAttachments / useDocumentLinks
 *
 * @version 2.0.0
 * @date 2026-03-10
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { Form, App } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import { useProjectsDropdown, useUsersDropdown, useFileSettings } from '../../../hooks/business/useDropdownData';
import { queryKeys } from '../../../config/queryConfig';
import dayjs from 'dayjs';

// API
import { documentsApi } from '../../../api/documentsApi';
import { filesApi } from '../../../api/filesApi';

// 類型
import { Document } from '../../../types';
import type { ProjectStaff, Project, User } from '../../../types/api';
import type { DocumentAttachment } from '../../../types/document';
import type {
  DocumentDispatchLink, DocumentProjectLink, TaoyuanProjectCreate,
} from '../../../types/taoyuan';
import type { UploadFile } from 'antd/es/upload';

// 常數 & 工具
import { logger } from '../../../utils/logger';
import { hasProjectFeature } from '../../../config/projectModules';

// 提取的子 Hooks
import { useDocumentAttachments } from './useDocumentAttachments';
import { useDocumentLinks } from './useDocumentLinks';
import type { UseDocumentLinksReturn } from './useDocumentLinks';
import { useDocumentProjectStaff } from './useDocumentProjectStaff';

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
  agencyContacts: UseDocumentLinksReturn['agencyContacts'];
  projectVendors: UseDocumentLinksReturn['projectVendors'];
  availableDispatches: UseDocumentLinksReturn['availableDispatches'];
  availableProjects: UseDocumentLinksReturn['availableProjects'];
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
  handleCreateAndLinkProject: (data: TaoyuanProjectCreate) => Promise<void>;
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

  // 上傳相關狀態（仍在此處，因與 handleSave 耦合）
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // 下拉選項資料（共用 React Query 快取 hooks）
  const { projects: cases, isLoading: casesLoading } = useProjectsDropdown();
  const { users, isLoading: usersLoading } = useUsersDropdown();
  const fileSettings = useFileSettings();

  // 專案人員子 Hook
  const staffHook = useDocumentProjectStaff();

  // 行事曆模態框
  const [showIntegratedEventModal, setShowIntegratedEventModal] = useState(false);

  // =============================================================================
  // 案件功能模組判斷
  // =============================================================================

  const hasDispatchFeature = hasProjectFeature(
    document?.contract_project_id,
    'dispatch-management'
  );
  const hasProjectLinkFeature = hasProjectFeature(
    document?.contract_project_id,
    'project-linking'
  );

  // =============================================================================
  // 委派的子 Hooks
  // =============================================================================

  const attachmentsHook = useDocumentAttachments();

  const linksHook = useDocumentLinks({
    documentId: id,
    document,
    isEditing,
    hasDispatchFeature,
    hasProjectLinkFeature,
  });

  // =============================================================================
  // 公文載入
  // =============================================================================

  // 待設置的表單值（延遲到 loading 結束後設置）
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Ant Design form values are Record<string, any>
  const [pendingFormValues, setPendingFormValues] = useState<Record<string, any> | null>(null);

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

      // 公文 + 附件並行載入
      const [doc] = await Promise.all([
        documentsApi.getDocument(docId),
        attachmentsHook.loadAttachments(docId),
      ]);

      setDocument(doc);
      // atts already set inside attachmentsHook

      const assigneeArray = staffHook.parseAssignee(doc.assignee);
      staffHook.setCurrentAssigneeValues(assigneeArray);

      setPendingFormValues({
        ...doc,
        doc_date: doc.doc_date ? dayjs(doc.doc_date) : null,
        receive_date: doc.receive_date ? dayjs(doc.receive_date) : null,
        send_date: doc.send_date ? dayjs(doc.send_date) : null,
        assignee: assigneeArray,
      });

      const projectId = doc.contract_project_id;
      if (projectId) {
        staffHook.setSelectedContractProjectId(projectId);
        const staffList = await staffHook.fetchProjectStaff(projectId);
        if ((!assigneeArray || assigneeArray.length === 0) && staffList && staffList.length > 0) {
          const staffNames = staffList.map((s: ProjectStaff) => s.user_name).filter((name): name is string => !!name);
          setPendingFormValues(prev => prev ? { ...prev, assignee: staffNames } : null);
          staffHook.setCurrentAssigneeValues(staffNames);
        }
      }
    } catch (error) {
      logger.error('載入公文失敗:', error);
      message.error('載入公文失敗');
      setDocument(null);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- form is stable from useForm but used in callback
  }, [id, message]);

  // 初始載入公文資料
  useEffect(() => {
    loadDocument();
  }, [loadDocument]);

  // 條件載入派工/工程關聯資料
  const documentId = document?.id;
  const contractProjectId = document?.contract_project_id;
  useEffect(() => {
    if (documentId) {
      if (hasDispatchFeature) {
        linksHook.loadDispatchLinks();
      }
      if (hasProjectLinkFeature) {
        linksHook.loadProjectLinks();
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- 僅依賴 ID 層級而非整個 document 物件
  }, [documentId, contractProjectId, hasDispatchFeature, hasProjectLinkFeature]);

  // =============================================================================
  // 事件處理
  // =============================================================================

  const handleProjectChange = async (projectId: number | null | undefined) => {
    await staffHook.handleProjectChange(projectId, form, message);
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

      // getFieldsValue(true) 取得所有欄位（含未渲染 Tab），避免遺漏
      // validateFields() 只取已渲染的 Form.Item，其他 Tab 的值會丟失
      const allValues = form.getFieldsValue(true);
      const merged = { ...allValues, ...values };

      // 日期欄位：dayjs → 'YYYY-MM-DD' 字串（null 保持 null 以支援清除）
      const DATE_KEYS = ['doc_date', 'receive_date', 'send_date'] as const;
      for (const key of DATE_KEYS) {
        const v = merged[key];
        if (v && typeof v === 'object' && v.format) {
          merged[key] = v.format('YYYY-MM-DD');
        } else if (v === null) {
          merged[key] = null;   // 使用者主動清除
        } else {
          delete merged[key];   // undefined → 不送出，不覆蓋後端
        }
      }

      merged.assignee = assigneeStr;

      const documentData = Object.fromEntries(
        Object.entries(merged).filter(([, v]) => v !== undefined),
      );

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
      await linksHook.loadDispatchLinks();
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
      const assigneeArray = staffHook.parseAssignee(document.assignee);
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
    queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
  };

  // 附件操作 — 適配原始介面（handleDeleteAttachment 接受單參數）
  const handleDeleteAttachment = useCallback(async (attachmentId: number) => {
    if (!id) return;
    await attachmentsHook.handleDeleteAttachment(attachmentId, parseInt(id, 10));
  }, [id, attachmentsHook]);

  return {
    // State
    document,
    loading,
    saving,
    activeTab,
    setActiveTab,
    isEditing,
    setIsEditing,
    // Attachments (from sub-hook + local upload state)
    attachments: attachmentsHook.attachments,
    attachmentsLoading: attachmentsHook.attachmentsLoading,
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
    projectStaffMap: staffHook.projectStaffMap,
    staffLoading: staffHook.staffLoading,
    selectedContractProjectId: staffHook.selectedContractProjectId,
    currentAssigneeValues: staffHook.currentAssigneeValues,
    // Dispatch & Project links (from sub-hook)
    dispatchLinks: linksHook.dispatchLinks,
    dispatchLinksLoading: linksHook.dispatchLinksLoading,
    projectLinks: linksHook.projectLinks,
    projectLinksLoading: linksHook.projectLinksLoading,
    // Feature flags
    hasDispatchFeature,
    hasProjectLinkFeature,
    // Query data (from sub-hook)
    agencyContacts: linksHook.agencyContacts,
    projectVendors: linksHook.projectVendors,
    availableDispatches: linksHook.availableDispatches,
    availableProjects: linksHook.availableProjects,
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
    handleDownload: attachmentsHook.handleDownload,
    handlePreview: attachmentsHook.handlePreview,
    handleDeleteAttachment,
    handleCreateDispatch: linksHook.handleCreateDispatch,
    handleLinkDispatch: linksHook.handleLinkDispatch,
    handleUnlinkDispatch: linksHook.handleUnlinkDispatch,
    handleLinkProject: linksHook.handleLinkProject,
    handleUnlinkProject: linksHook.handleUnlinkProject,
    handleCreateAndLinkProject: linksHook.handleCreateAndLinkProject,
    // Form
    form,
    // Navigation
    returnTo,
  };
}
