/**
 * 桃園查估派工詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構：
 * - 派工資訊：派工單號、工程名稱、作業類別、承辦人等
 * - 公文對照：公文關聯 + 作業歷程整合為公文對照矩陣
 * - 派工附件：附件上傳與管理
 * - 工程關聯：關聯的工程資訊
 * - 契金維護：契金紀錄管理
 *
 * @version 3.0.0 - 公文關聯 + 作業歷程整合為「公文對照」Tab
 * @date 2026-02-13
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Form, Button, App, Space, Popconfirm, Modal } from 'antd';
import type { UploadFile } from 'antd/es/upload';
import {
  SendOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ProjectOutlined,
  PaperClipOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../config/queryConfig';
import dayjs from 'dayjs';

import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import {
  dispatchOrdersApi,
  taoyuanProjectsApi,
  projectLinksApi,
  dispatchAttachmentsApi,
  contractPaymentsApi,
} from '../api/taoyuanDispatchApi';
import { getProjectAgencyContacts } from '../api/projectAgencyContacts';
import { projectVendorsApi } from '../api/projectVendorsApi';
import type {
  DispatchOrderUpdate,
  TaoyuanProject,
  DispatchDocumentLink,
  ContractPaymentCreate,
} from '../types/api';
import { useAuthGuard } from '../hooks';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';

// 導入拆分的 Tab 元件
import {
  DispatchInfoTab,
  DispatchProjectsTab,
  DispatchAttachmentsTab,
  DispatchPaymentTab,
  DispatchWorkflowTab,
  type LinkedProject,
} from './taoyuanDispatch/tabs';
import {
  parseWorkTypeCodes,
  validatePaymentConsistency,
} from './taoyuanDispatch/tabs/paymentUtils';
import { logger } from '../services/logger';

export const TaoyuanDispatchDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 權限控制
  const { hasPermission } = useAuthGuard();
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  // 從 URL 參數讀取初始 Tab
  const initialTab = searchParams.get('tab') || 'info';
  const [activeTab, setActiveTab] = useState(initialTab);
  const [isEditing, setIsEditing] = useState(false);

  // 同步 URL 參數變化到 activeTab（處理瀏覽器後退/前進）
  useEffect(() => {
    const tabFromUrl = searchParams.get('tab') || 'info';
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams, activeTab]);

  // Tab 變更處理（同時更新 URL 參數）
  const handleTabChange = useCallback((tabKey: string) => {
    setActiveTab(tabKey);
    setSearchParams({ tab: tabKey }, { replace: true });
  }, [setSearchParams]);

  // 工程關聯狀態
  const [selectedProjectId, setSelectedProjectId] = useState<number>();

  // 附件上傳狀態
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // =============================================================================
  // 資料查詢
  // =============================================================================

  // 查詢派工單詳情
  const {
    data: dispatch,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['dispatch-order-detail', id],
    queryFn: () => dispatchOrdersApi.getDetail(parseInt(id || '0', 10)),
    enabled: !!id,
  });

  // 查詢機關承辦清單
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const agencyContacts = useMemo(
    () => agencyContactsData?.items ?? [],
    [agencyContactsData?.items]
  );

  // 查詢協力廠商清單
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () =>
      projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const projectVendors = useMemo(
    () => vendorsData?.associations ?? [],
    [vendorsData?.associations]
  );

  // 查詢可關聯的工程
  const { data: availableProjectsData } = useQuery({
    queryKey: [
      'taoyuan-projects-for-dispatch-link',
      dispatch?.contract_project_id,
    ],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id:
          dispatch?.contract_project_id || TAOYUAN_CONTRACT.PROJECT_ID,
        limit: 500,
      }),
    enabled: !!dispatch,
  });
  const availableProjects = useMemo(
    () => availableProjectsData?.items ?? [],
    [availableProjectsData?.items]
  );

  // 已關聯的工程 ID 列表
  const linkedProjectIds = useMemo(
    () => (dispatch?.linked_projects || []).map(
      (p: LinkedProject) => p.project_id
    ),
    [dispatch?.linked_projects]
  );

  // 過濾掉已關聯的工程
  const filteredProjects = useMemo(
    () => availableProjects.filter(
      (proj: TaoyuanProject) => !linkedProjectIds.includes(proj.id)
    ),
    [availableProjects, linkedProjectIds]
  );

  // 查詢派工單附件
  const { data: attachments, refetch: refetchAttachments } = useQuery({
    queryKey: ['dispatch-attachments', id],
    queryFn: () =>
      dispatchAttachmentsApi.getAttachments(parseInt(id || '0', 10)),
    enabled: !!id,
  });

  // 查詢契金紀錄
  const { data: paymentData, refetch: refetchPayment } = useQuery({
    queryKey: ['dispatch-payment', id],
    queryFn: async () => {
      const result = await contractPaymentsApi.getList(
        parseInt(id || '0', 10)
      );
      return result.items?.[0] || null;
    },
    enabled: !!id,
  });

  // =============================================================================
  // Form.useWatch - 必須在組件頂層呼叫
  // =============================================================================

  const watchedWorkTypes: string[] = Form.useWatch('work_type', form) || [];
  const watchedWork01Amount = Form.useWatch('work_01_amount', form) || 0;
  const watchedWork02Amount = Form.useWatch('work_02_amount', form) || 0;
  const watchedWork03Amount = Form.useWatch('work_03_amount', form) || 0;
  const watchedWork04Amount = Form.useWatch('work_04_amount', form) || 0;
  const watchedWork05Amount = Form.useWatch('work_05_amount', form) || 0;
  const watchedWork06Amount = Form.useWatch('work_06_amount', form) || 0;
  const watchedWork07Amount = Form.useWatch('work_07_amount', form) || 0;

  const watchedWorkAmounts = useMemo(() => ({
    work_01_amount: watchedWork01Amount,
    work_02_amount: watchedWork02Amount,
    work_03_amount: watchedWork03Amount,
    work_04_amount: watchedWork04Amount,
    work_05_amount: watchedWork05Amount,
    work_06_amount: watchedWork06Amount,
    work_07_amount: watchedWork07Amount,
  }), [
    watchedWork01Amount, watchedWork02Amount, watchedWork03Amount,
    watchedWork04Amount, watchedWork05Amount, watchedWork06Amount,
    watchedWork07Amount
  ]);

  // =============================================================================
  // Mutations
  // =============================================================================

  // 契金儲存 mutation
  const paymentMutation = useMutation({
    mutationFn: async (values: ContractPaymentCreate) => {
      if (paymentData?.id) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { dispatch_order_id: _dispatch_order_id, ...updateData } = values;
        return contractPaymentsApi.update(paymentData.id, updateData);
      } else {
        return contractPaymentsApi.create(values);
      }
    },
    onSuccess: () => {
      message.success('契金紀錄儲存成功');
      refetchPayment();
      // 同步更新契金管控列表（PaymentsTab）
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanPayments.all });
    },
    onError: (error: Error) => {
      logger.error('[paymentMutation] 契金儲存失敗:', error);
      message.error('契金儲存失敗，請重新編輯');
      // 即使契金失敗也重新整理數據
      refetchPayment();
    },
  });

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: DispatchOrderUpdate) =>
      dispatchOrdersApi.update(parseInt(id || '0', 10), data),
    onSuccess: () => {
      message.success('派工單更新成功');
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      setIsEditing(false);
    },
    onError: () => message.error('更新失敗'),
  });

  // 刪除 mutation
  const deleteMutation = useMutation({
    mutationFn: () => dispatchOrdersApi.delete(parseInt(id || '0', 10)),
    onSuccess: () => {
      message.success('派工單刪除成功');
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      navigate('/taoyuan/dispatch');
    },
    onError: () => message.error('刪除失敗'),
  });

  // 關聯工程 mutation
  const linkProjectMutation = useMutation({
    mutationFn: (projectId: number) =>
      projectLinksApi.linkDispatch(projectId, parseInt(id || '0', 10)),
    onSuccess: (data) => {
      // 顯示基本成功訊息
      message.success('工程關聯成功');

      // 如果有自動同步到公文，顯示額外提示
      if (data.auto_sync && data.auto_sync.auto_linked_count > 0) {
        message.info(`已自動同步 ${data.auto_sync.auto_linked_count} 個公文的工程關聯`);
      }

      setSelectedProjectId(undefined);
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
      // 同步刷新公文關聯
      queryClient.invalidateQueries({ queryKey: ['document-project-links'] });
    },
    onError: () => message.error('關聯失敗'),
  });

  // 移除工程關聯 mutation
  const unlinkProjectMutation = useMutation({
    mutationFn: (linkId: number) => {
      if (linkId === undefined || linkId === null) {
        logger.error('[unlinkProjectMutation] linkId 無效:', linkId);
        return Promise.reject(new Error('關聯 ID 無效'));
      }

      const linkedProjects = dispatch?.linked_projects || [];
      const targetProject = linkedProjects.find((p) => p.link_id === linkId);
      if (!targetProject) {
        logger.error('[unlinkProjectMutation] 找不到 link_id:', linkId);
        return Promise.reject(new Error('找不到關聯工程，請重新整理頁面'));
      }

      const projectId = targetProject.project_id ?? targetProject.id;
      if (!projectId) {
        logger.error('[unlinkProjectMutation] project_id 無效:', targetProject);
        return Promise.reject(new Error('工程 ID 無效，請重新整理頁面'));
      }

      return projectLinksApi.unlinkDispatch(projectId, linkId);
    },
    onSuccess: () => {
      message.success('已移除工程關聯');
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
    },
    onError: (error: Error) => {
      message.error(`移除關聯失敗: ${error.message}`);
      refetch();
    },
  });

  // 上傳附件 mutation
  const uploadAttachmentsMutation = useMutation({
    mutationFn: async () => {
      if (fileList.length === 0) return;
      const files = fileList
        .map((f) => f.originFileObj as File | undefined)
        .filter((f): f is File => f !== undefined);
      if (files.length === 0) return;
      setUploading(true);
      setUploadProgress(0);
      return dispatchAttachmentsApi.uploadFiles(
        parseInt(id || '0', 10),
        files,
        (percent) => setUploadProgress(percent)
      );
    },
    onSuccess: (result) => {
      setUploading(false);
      setFileList([]);
      setUploadProgress(0);
      if (result) {
        const successCount = result.files?.length ?? 0;
        const errorCount = result.errors?.length ?? 0;
        if (errorCount > 0) {
          setUploadErrors(result.errors || []);
          message.warning(`上傳完成：${successCount} 成功，${errorCount} 失敗`);
        } else {
          message.success(`成功上傳 ${successCount} 個檔案`);
        }
      }
      refetchAttachments();
    },
    onError: (error: Error) => {
      setUploading(false);
      setUploadProgress(0);
      message.error(`上傳失敗: ${error.message}`);
    },
  });

  // 刪除附件 mutation
  const deleteAttachmentMutation = useMutation({
    mutationFn: (attachmentId: number) =>
      dispatchAttachmentsApi.deleteAttachment(attachmentId),
    onSuccess: () => {
      message.success('附件刪除成功');
      refetchAttachments();
    },
    onError: () => message.error('刪除失敗'),
  });

  // =============================================================================
  // Effects
  // =============================================================================

  // 計算派工日期（機關第一筆來函日期），供契金日期欄位自動帶入
  const dispatchDate = useMemo(() => {
    const agencyDocs = (dispatch?.linked_documents || [])
      .filter(
        (link: DispatchDocumentLink) =>
          link.link_type === 'agency_incoming' && link.doc_date
      )
      .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
        const dateA = a.doc_date || '9999-12-31';
        const dateB = b.doc_date || '9999-12-31';
        return dateA.localeCompare(dateB);
      });
    return agencyDocs[0]?.doc_date || null;
  }, [dispatch?.linked_documents]);

  // 設定表單初始值
  useEffect(() => {
    if (dispatch) {
      const workTypeArray = dispatch.work_type
        ? dispatch.work_type
            .split(',')
            .map((t: string) => t.trim())
            .filter(Boolean)
        : [];

      // 解析作業類別代碼，用於自動帶入派工日期
      const activeCodes = parseWorkTypeCodes(workTypeArray);

      // 日期欄位：優先使用 paymentData，否則自動帶入派工日期
      const toDateValue = (code: string): ReturnType<typeof dayjs> | undefined => {
        const dateKey = `work_${code}_date` as keyof typeof paymentData;
        const val = paymentData?.[dateKey] as string | undefined;
        if (val) return dayjs(val);
        // 作業類別對應時，自動帶入派工日期
        if (activeCodes.includes(code) && dispatchDate) return dayjs(dispatchDate);
        return undefined;
      };

      form.setFieldsValue({
        dispatch_no: dispatch.dispatch_no,
        project_name: dispatch.project_name,
        work_type: workTypeArray,
        sub_case_name: dispatch.sub_case_name,
        deadline: dispatch.deadline,
        case_handler: dispatch.case_handler,
        survey_unit: dispatch.survey_unit,
        contact_note: dispatch.contact_note,
        cloud_folder: dispatch.cloud_folder,
        project_folder: dispatch.project_folder,
        work_01_date: toDateValue('01'),
        work_01_amount: paymentData?.work_01_amount,
        work_02_date: toDateValue('02'),
        work_02_amount: paymentData?.work_02_amount,
        work_03_date: toDateValue('03'),
        work_03_amount: paymentData?.work_03_amount,
        work_04_date: toDateValue('04'),
        work_04_amount: paymentData?.work_04_amount,
        work_05_date: toDateValue('05'),
        work_05_amount: paymentData?.work_05_amount,
        work_06_date: toDateValue('06'),
        work_06_amount: paymentData?.work_06_amount,
        work_07_date: toDateValue('07'),
        work_07_amount: paymentData?.work_07_amount,
      });
    }
  }, [dispatch, paymentData, form, dispatchDate]);

  // =============================================================================
  // Handlers
  // =============================================================================

  // 儲存派工單
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      const workTypeString = Array.isArray(values.work_type)
        ? values.work_type.join(', ')
        : values.work_type || '';

      // 解析作業類別代碼
      const workTypeCodes = parseWorkTypeCodes(values.work_type);

      /* eslint-disable @typescript-eslint/no-unused-vars */
      const {
        work_01_amount,
        work_02_amount,
        work_03_amount,
        work_04_amount,
        work_05_amount,
        work_06_amount,
        work_07_amount,
        current_amount,
        cumulative_amount,
        remaining_amount,
        ...dispatchValues
      } = values;
      /* eslint-enable @typescript-eslint/no-unused-vars */

      // 原始金額物件
      const originalAmounts: Record<string, number | undefined> = {
        work_01_amount,
        work_02_amount,
        work_03_amount,
        work_04_amount,
        work_05_amount,
        work_06_amount,
        work_07_amount,
      };

      // 檢查契金與作業類別一致性
      const inconsistencies = validatePaymentConsistency(workTypeCodes, originalAmounts);

      // 同步調整：只保留對應作業類別的金額，不對應的設為 null（非 undefined）以確實清除
      const syncedAmounts: Record<string, number | null | undefined> = {};
      for (let i = 1; i <= 7; i++) {
        const code = i.toString().padStart(2, '0');
        const field = `work_${code}_amount`;
        if (workTypeCodes.includes(code)) {
          // 保留對應金額（0 轉為 null，避免儲存無意義的零值）
          const val = originalAmounts[field];
          syncedAmounts[field] = (val && val > 0) ? val : null;
        } else {
          syncedAmounts[field] = null; // 明確清除不對應的金額
        }
      }

      // 如果有不一致的金額被清除，顯示提示
      if (inconsistencies.length > 0) {
        const clearedInfo = inconsistencies
          .map(item => `${item.label}: $${item.amount.toLocaleString()}`)
          .join('、');
        message.warning(`以下金額因作業類別變更已自動清除：${clearedInfo}`);
      }

      // 使用同步後的金額計算總金額
      const calculatedCurrentAmount =
        (syncedAmounts.work_01_amount || 0) +
        (syncedAmounts.work_02_amount || 0) +
        (syncedAmounts.work_03_amount || 0) +
        (syncedAmounts.work_04_amount || 0) +
        (syncedAmounts.work_05_amount || 0) +
        (syncedAmounts.work_06_amount || 0) +
        (syncedAmounts.work_07_amount || 0);

      // 日期欄位從 dayjs 轉換為字串格式
      const formatDateField = (dateValue: unknown): string | null => {
        if (!dateValue) return null;
        if (typeof dateValue === 'object' && dateValue !== null && 'format' in dateValue) {
          return (dateValue as { format: (fmt: string) => string }).format('YYYY-MM-DD');
        }
        if (typeof dateValue === 'string') return dateValue;
        return null;
      };

      // 串列執行：先更新派工單，成功後再更新契金（避免併發不一致）
      try {
        await updateMutation.mutateAsync({
          ...dispatchValues,
          work_type: workTypeString,
        });
      } catch {
        // updateMutation.onError 已處理提示，直接返回
        return;
      }

      // 派工單更新成功，接著更新契金
      if (calculatedCurrentAmount > 0 || paymentData?.id) {
        const paymentValues: ContractPaymentCreate = {
          dispatch_order_id: parseInt(id || '0', 10),
          work_01_date: workTypeCodes.includes('01') ? formatDateField(values.work_01_date) : null,
          work_02_date: workTypeCodes.includes('02') ? formatDateField(values.work_02_date) : null,
          work_03_date: workTypeCodes.includes('03') ? formatDateField(values.work_03_date) : null,
          work_04_date: workTypeCodes.includes('04') ? formatDateField(values.work_04_date) : null,
          work_05_date: workTypeCodes.includes('05') ? formatDateField(values.work_05_date) : null,
          work_06_date: workTypeCodes.includes('06') ? formatDateField(values.work_06_date) : null,
          work_07_date: workTypeCodes.includes('07') ? formatDateField(values.work_07_date) : null,
          work_01_amount: syncedAmounts.work_01_amount ?? null,
          work_02_amount: syncedAmounts.work_02_amount ?? null,
          work_03_amount: syncedAmounts.work_03_amount ?? null,
          work_04_amount: syncedAmounts.work_04_amount ?? null,
          work_05_amount: syncedAmounts.work_05_amount ?? null,
          work_06_amount: syncedAmounts.work_06_amount ?? null,
          work_07_amount: syncedAmounts.work_07_amount ?? null,
          current_amount: calculatedCurrentAmount > 0 ? calculatedCurrentAmount : null,
        };
        paymentMutation.mutate(paymentValues);
      }

      // 若有待上傳附件，一併上傳
      if (fileList.length > 0) {
        uploadAttachmentsMutation.mutate();
      }
    } catch (error) {
      message.error('請檢查表單欄位');
    }
  };

  // 取消編輯
  const handleCancelEdit = () => {
    setIsEditing(false);
    if (dispatch) {
      const workTypeArray = dispatch.work_type
        ? dispatch.work_type
            .split(',')
            .map((t: string) => t.trim())
            .filter(Boolean)
        : [];

      const activeCodes = parseWorkTypeCodes(workTypeArray);

      const toDateValue = (code: string): ReturnType<typeof dayjs> | undefined => {
        const dateKey = `work_${code}_date` as keyof typeof paymentData;
        const val = paymentData?.[dateKey] as string | undefined;
        if (val) return dayjs(val);
        if (activeCodes.includes(code) && dispatchDate) return dayjs(dispatchDate);
        return undefined;
      };

      form.setFieldsValue({
        dispatch_no: dispatch.dispatch_no,
        project_name: dispatch.project_name,
        work_type: workTypeArray,
        sub_case_name: dispatch.sub_case_name,
        deadline: dispatch.deadline,
        case_handler: dispatch.case_handler,
        survey_unit: dispatch.survey_unit,
        contact_note: dispatch.contact_note,
        cloud_folder: dispatch.cloud_folder,
        project_folder: dispatch.project_folder,
        work_01_date: toDateValue('01'),
        work_01_amount: paymentData?.work_01_amount,
        work_02_date: toDateValue('02'),
        work_02_amount: paymentData?.work_02_amount,
        work_03_date: toDateValue('03'),
        work_03_amount: paymentData?.work_03_amount,
        work_04_date: toDateValue('04'),
        work_04_amount: paymentData?.work_04_amount,
        work_05_date: toDateValue('05'),
        work_05_amount: paymentData?.work_05_amount,
        work_06_date: toDateValue('06'),
        work_06_amount: paymentData?.work_06_amount,
        work_07_date: toDateValue('07'),
        work_07_amount: paymentData?.work_07_amount,
      });
    }
  };

  // 處理工程關聯
  const handleLinkProject = useCallback(() => {
    if (!selectedProjectId) {
      message.warning('請先選擇要關聯的工程');
      return;
    }
    linkProjectMutation.mutate(selectedProjectId);
  }, [selectedProjectId, linkProjectMutation, message]);

  // 處理從派工資訊 Tab 選擇工程（混合模式）
  const handleProjectSelectFromInfo = useCallback((projectId: number, projectName: string) => {
    // 檢查是否已關聯
    const isAlreadyLinked = linkedProjectIds.includes(projectId);
    if (isAlreadyLinked) {
      message.info(`工程「${projectName}」已經關聯`);
      return;
    }

    // 詢問是否同時建立工程關聯
    Modal.confirm({
      title: '建立工程關聯',
      content: `您選擇了工程「${projectName}」，是否同時建立工程關聯？`,
      okText: '是，建立關聯',
      cancelText: '否，僅填入名稱',
      onOk: () => {
        linkProjectMutation.mutate(projectId);
      },
    });
  }, [linkedProjectIds, message, linkProjectMutation]);

  // =============================================================================
  // Tab 配置
  // =============================================================================

  const tabs = [
    createTabItem(
      'info',
      { icon: <SendOutlined />, text: '派工資訊' },
      <DispatchInfoTab
        dispatch={dispatch}
        form={form}
        isEditing={isEditing}
        agencyContacts={agencyContacts}
        projectVendors={projectVendors}
        paymentData={paymentData}
        watchedWorkTypes={watchedWorkTypes}
        watchedWorkAmounts={watchedWorkAmounts}
        availableProjects={availableProjects}
        onProjectSelect={handleProjectSelectFromInfo}
      />
    ),
    createTabItem(
      'attachments',
      {
        icon: <PaperClipOutlined />,
        text: '派工附件',
        count: attachments?.length || 0,
      },
      <DispatchAttachmentsTab
        dispatchId={parseInt(id || '0', 10)}
        isEditing={isEditing}
        isLoading={isLoading}
        attachments={attachments || []}
        fileList={fileList}
        setFileList={setFileList}
        uploading={uploading}
        uploadProgress={uploadProgress}
        uploadErrors={uploadErrors}
        setUploadErrors={setUploadErrors}
        uploadAttachmentsMutation={uploadAttachmentsMutation}
        deleteAttachmentMutation={deleteAttachmentMutation}
      />
    ),
    createTabItem(
      'projects',
      {
        icon: <ProjectOutlined />,
        text: '工程關聯',
        count: dispatch?.linked_projects?.length || 0,
      },
      <DispatchProjectsTab
        isLoading={isLoading}
        canEdit={canEdit}
        linkedProjects={(dispatch?.linked_projects || []) as LinkedProject[]}
        filteredProjects={filteredProjects}
        selectedProjectId={selectedProjectId}
        setSelectedProjectId={setSelectedProjectId}
        onLinkProject={handleLinkProject}
        linkProjectLoading={linkProjectMutation.isPending}
        onUnlinkProject={(linkId, _projectId, _proj) => unlinkProjectMutation.mutate(linkId)}
        unlinkProjectLoading={unlinkProjectMutation.isPending}
        navigate={navigate}
        messageError={message.error}
        refetch={refetch}
      />
    ),
    createTabItem(
      'payment',
      { icon: <DollarOutlined />, text: '契金維護' },
      <DispatchPaymentTab
        dispatch={dispatch}
        paymentData={paymentData}
        isEditing={isEditing}
        form={form}
      />
    ),
    createTabItem(
      'correspondence',
      {
        icon: <FileTextOutlined />,
        text: '公文對照',
        count: dispatch?.linked_documents?.length || 0,
      },
      <DispatchWorkflowTab
        dispatchOrderId={parseInt(id || '0', 10)}
        canEdit={canEdit}
        linkedProjects={(dispatch?.linked_projects || []).map((p: LinkedProject) => ({
          project_id: p.project_id,
          project_name: p.project_name,
        }))}
        linkedDocuments={dispatch?.linked_documents || []}
        onRefetchDispatch={refetch}
      />
    ),
  ];

  // =============================================================================
  // Header 配置
  // =============================================================================

  const headerConfig = {
    title: dispatch?.dispatch_no || '派工詳情',
    icon: <SendOutlined />,
    backText: '返回派工列表',
    backPath: '/taoyuan/dispatch',
    tags: dispatch
      ? [
          ...(dispatch.work_type
            ? [{ text: dispatch.work_type, color: 'blue' as const }]
            : []),
        ]
      : [],
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
              loading={updateMutation.isPending}
              disabled={updateMutation.isPending}
              onClick={handleSave}
            >
              儲存
            </Button>
          </>
        ) : (
          <>
            {canEdit && (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setIsEditing(true)}
              >
                編輯
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="確定要刪除此派工單嗎？"
                description="刪除後將無法復原，請確認是否繼續。"
                onConfirm={() => deleteMutation.mutate()}
                okText="確定刪除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>
                  刪除
                </Button>
              </Popconfirm>
            )}
          </>
        )}
      </Space>
    ),
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      loading={isLoading}
      hasData={!!dispatch}
    />
  );
};

export default TaoyuanDispatchDetailPage;
