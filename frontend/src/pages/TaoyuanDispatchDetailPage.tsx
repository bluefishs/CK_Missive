/**
 * 桃園查估派工詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構：
 * - 派工資訊：派工單號、工程名稱、作業類別、承辦人等
 * - 公文關聯：機關函文、乾坤函文關聯管理
 * - 工程關聯：關聯的工程資訊
 *
 * @version 1.0.0
 * @date 2026-01-20
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Form,
  Input,
  Select,
  Button,
  App,
  Space,
  Row,
  Col,
  Tag,
  Spin,
  Empty,
  Descriptions,
  Divider,
  Popconfirm,
  List,
  Card,
  Radio,
  Typography,
  Upload,
  Progress,
  Alert,
  InputNumber,
  DatePicker,
} from 'antd';
import type { UploadFile, UploadChangeParam, UploadProps } from 'antd/es/upload';
import {
  SendOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ProjectOutlined,
  PlusOutlined,
  PaperClipOutlined,
  InboxOutlined,
  DownloadOutlined,
  FileOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  LoadingOutlined,
  DollarOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import { dispatchOrdersApi, taoyuanProjectsApi, projectLinksApi, dispatchAttachmentsApi, contractPaymentsApi } from '../api/taoyuanDispatchApi';
import { documentsApi } from '../api/documentsApi';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import type { DispatchOrder, DispatchOrderUpdate, OfficialDocument, LinkType, TaoyuanProject, DispatchDocumentLink, DispatchAttachment, ContractPayment, ContractPaymentCreate, ContractPaymentUpdate } from '../types/api';

/** 關聯工程型別（包含 link_id 用於刪除操作） */
type LinkedProject = TaoyuanProject & { link_id: number; project_id: number };
import { TAOYUAN_WORK_TYPES, isReceiveDocument } from '../types/api';
import { useAuthGuard } from '../hooks';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';

const { Option } = Select;
const { Text } = Typography;
const { Dragger } = Upload;

/**
 * 根據公文字號自動判斷關聯類型
 * - 以「乾坤」開頭的公文 → 乾坤發文 (company_outgoing)
 * - 其他 → 機關來函 (agency_incoming)
 */
const detectLinkType = (docNumber?: string): LinkType => {
  if (!docNumber) return 'agency_incoming';
  // 「乾坤」開頭表示公司發文
  if (docNumber.startsWith('乾坤')) {
    return 'company_outgoing';
  }
  // 其他都是機關來函
  return 'agency_incoming';
};

export const TaoyuanDispatchDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 權限控制
  const { hasPermission } = useAuthGuard();
  const canEdit = hasPermission('documents:edit');  // 使用 documents 權限作為派工管理權限
  const canDelete = hasPermission('documents:delete');

  // 狀態
  const [activeTab, setActiveTab] = useState('info');
  const [isEditing, setIsEditing] = useState(false);

  // 公文關聯狀態
  const [docSearchKeyword, setDocSearchKeyword] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<number>();
  const [selectedLinkType, setSelectedLinkType] = useState<LinkType>('agency_incoming');

  // 工程關聯狀態
  const [selectedProjectId, setSelectedProjectId] = useState<number>();

  // 附件上傳狀態
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

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

  // 查詢關聯公文
  const { data: linkedDocuments, refetch: refetchDocs } = useQuery({
    queryKey: ['dispatch-linked-documents', id],
    queryFn: async () => {
      // 透過派工單的 linked_documents 欄位取得
      return dispatch?.linked_documents || [];
    },
    enabled: !!dispatch,
  });

  // 查詢關聯工程
  const { data: linkedProjects, refetch: refetchProjects } = useQuery({
    queryKey: ['dispatch-linked-projects', id],
    queryFn: async () => {
      return dispatch?.linked_projects || [];
    },
    enabled: !!dispatch,
  });

  // 搜尋可關聯的公文
  const { data: searchedDocs, isLoading: searchingDocs } = useQuery({
    queryKey: ['documents-for-dispatch-link', docSearchKeyword],
    queryFn: async () => {
      if (!docSearchKeyword.trim()) return [];
      return documentsApi.searchDocuments(docSearchKeyword, 20);
    },
    enabled: !!docSearchKeyword.trim(),
  });

  // 已關聯的公文 ID 列表
  const linkedDocIds = (dispatch?.linked_documents || []).map((d: DispatchDocumentLink) => d.document_id);
  // 過濾掉已關聯的公文
  const availableDocs = (searchedDocs || []).filter(
    (doc: OfficialDocument) => !linkedDocIds.includes(doc.id)
  );

  // 查詢機關承辦清單（來自承攬案件）
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const agencyContacts = agencyContactsData?.items ?? [];

  // 查詢協力廠商清單（用於查估單位，來自承攬案件）
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const projectVendors = vendorsData?.associations ?? [];

  // 查詢可關聯的工程
  const { data: availableProjectsData } = useQuery({
    queryKey: ['taoyuan-projects-for-dispatch-link', dispatch?.contract_project_id],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id: dispatch?.contract_project_id || TAOYUAN_CONTRACT.PROJECT_ID,
        limit: 500,
      }),
    enabled: !!dispatch,
  });
  const availableProjects = availableProjectsData?.items ?? [];

  // 已關聯的工程 ID 列表
  const linkedProjectIds = (dispatch?.linked_projects || []).map((p: LinkedProject) => p.project_id);
  // 過濾掉已關聯的工程
  const filteredProjects = availableProjects.filter(
    (proj: TaoyuanProject) => !linkedProjectIds.includes(proj.id)
  );

  // 查詢派工單附件
  const { data: attachments, refetch: refetchAttachments } = useQuery({
    queryKey: ['dispatch-attachments', id],
    queryFn: () => dispatchAttachmentsApi.getAttachments(parseInt(id || '0', 10)),
    enabled: !!id,
  });

  // 契金維護狀態
  const [paymentForm] = Form.useForm();
  const [isPaymentEditing, setIsPaymentEditing] = useState(false);

  // 監聽作業類別變化（必須在組件頂層呼叫 Hook）
  const watchedWorkTypes: string[] = Form.useWatch('work_type', form) || [];
  // 監聽各作業類別金額變化（用於即時計算本次派工金額）
  const watchedWork01Amount = Form.useWatch('work_01_amount', form) || 0;
  const watchedWork02Amount = Form.useWatch('work_02_amount', form) || 0;
  const watchedWork03Amount = Form.useWatch('work_03_amount', form) || 0;
  const watchedWork04Amount = Form.useWatch('work_04_amount', form) || 0;
  const watchedWork05Amount = Form.useWatch('work_05_amount', form) || 0;
  const watchedWork06Amount = Form.useWatch('work_06_amount', form) || 0;
  const watchedWork07Amount = Form.useWatch('work_07_amount', form) || 0;

  // 查詢契金紀錄
  const { data: paymentData, refetch: refetchPayment } = useQuery({
    queryKey: ['dispatch-payment', id],
    queryFn: async () => {
      const result = await contractPaymentsApi.getList(parseInt(id || '0', 10));
      return result.items?.[0] || null;
    },
    enabled: !!id,
  });

  // 契金儲存 mutation
  const paymentMutation = useMutation({
    mutationFn: async (values: ContractPaymentCreate) => {
      if (paymentData?.id) {
        // 更新現有記錄
        const { dispatch_order_id, ...updateData } = values;
        return contractPaymentsApi.update(paymentData.id, updateData);
      } else {
        // 建立新記錄
        return contractPaymentsApi.create(values);
      }
    },
    onSuccess: () => {
      message.success('契金紀錄儲存成功');
      refetchPayment();
      setIsPaymentEditing(false);
    },
    onError: () => message.error('契金儲存失敗'),
  });

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: DispatchOrderUpdate) =>
      dispatchOrdersApi.update(parseInt(id || '0', 10), data),
    onSuccess: () => {
      message.success('派工單更新成功');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
      setIsEditing(false);
    },
    onError: () => message.error('更新失敗'),
  });

  // 刪除 mutation
  const deleteMutation = useMutation({
    mutationFn: () => dispatchOrdersApi.delete(parseInt(id || '0', 10)),
    onSuccess: () => {
      message.success('派工單刪除成功');
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
      navigate('/taoyuan/dispatch');
    },
    onError: () => message.error('刪除失敗'),
  });

  // 關聯公文 mutation
  const linkDocMutation = useMutation({
    mutationFn: (data: { documentId: number; linkType: LinkType }) =>
      dispatchOrdersApi.linkDocument(parseInt(id || '0', 10), {
        document_id: data.documentId,
        link_type: data.linkType,
      }),
    onSuccess: () => {
      message.success('公文關聯成功');
      setSelectedDocId(undefined);
      setDocSearchKeyword('');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
    },
    onError: () => message.error('關聯失敗'),
  });

  // 移除公文關聯 mutation
  const unlinkDocMutation = useMutation({
    mutationFn: (linkId: number) =>
      dispatchOrdersApi.unlinkDocument(parseInt(id || '0', 10), linkId),
    onSuccess: () => {
      message.success('已移除公文關聯');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
    },
    onError: () => message.error('移除關聯失敗'),
  });

  // 關聯工程 mutation
  const linkProjectMutation = useMutation({
    mutationFn: (projectId: number) =>
      projectLinksApi.linkDispatch(projectId, parseInt(id || '0', 10)),
    onSuccess: () => {
      message.success('工程關聯成功');
      setSelectedProjectId(undefined);
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects'] });
    },
    onError: () => message.error('關聯失敗'),
  });

  // 移除工程關聯 mutation
  const unlinkProjectMutation = useMutation({
    mutationFn: (linkId: number) => {
      // 防禦性檢查：確保 linkId 有效
      if (linkId === undefined || linkId === null) {
        console.error('[unlinkProjectMutation] linkId 無效:', linkId);
        return Promise.reject(new Error('關聯 ID 無效'));
      }

      const linkedProjects = dispatch?.linked_projects || [];
      console.debug('[unlinkProjectMutation] linked_projects:', JSON.stringify(
        linkedProjects.map(p => ({ id: p.id, link_id: p.link_id, project_id: p.project_id }))
      ));

      // 嚴格匹配：只用 link_id 查找，不使用回退值
      const targetProject = linkedProjects.find((p) => p.link_id === linkId);
      if (!targetProject) {
        // 如果找不到，記錄詳細信息以便調試
        console.error('[unlinkProjectMutation] 找不到 link_id:', linkId);
        console.error('[unlinkProjectMutation] 可用的 link_ids:', linkedProjects.map(p => p.link_id));
        return Promise.reject(new Error('找不到關聯工程，請重新整理頁面'));
      }

      // 使用 project_id，回退到 id（工程 ID）
      const projectId = targetProject.project_id ?? targetProject.id;
      if (!projectId) {
        console.error('[unlinkProjectMutation] project_id 無效:', targetProject);
        return Promise.reject(new Error('工程 ID 無效，請重新整理頁面'));
      }

      console.debug('[unlinkProjectMutation] 準備移除:', { projectId, linkId, targetProject });
      return projectLinksApi.unlinkDispatch(projectId, linkId);
    },
    onSuccess: () => {
      message.success('已移除工程關聯');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects'] });
    },
    onError: (error: Error) => {
      message.error(`移除關聯失敗: ${error.message}`);
      // 自動重新載入以確保數據同步
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

  // 設定表單初始值
  useEffect(() => {
    if (dispatch) {
      // work_type 轉換：字串轉陣列（支援逗號分隔）
      const workTypeArray = dispatch.work_type
        ? dispatch.work_type.split(',').map((t: string) => t.trim()).filter(Boolean)
        : [];

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
        // 各作業類別金額
        work_01_amount: paymentData?.work_01_amount,
        work_02_amount: paymentData?.work_02_amount,
        work_03_amount: paymentData?.work_03_amount,
        work_04_amount: paymentData?.work_04_amount,
        work_05_amount: paymentData?.work_05_amount,
        work_06_amount: paymentData?.work_06_amount,
        work_07_amount: paymentData?.work_07_amount,
      });
    }
  }, [dispatch, paymentData, form]);

  // 儲存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      // work_type 轉換：陣列轉逗號分隔字串
      const workTypeString = Array.isArray(values.work_type)
        ? values.work_type.join(', ')
        : values.work_type || '';

      // 分離派工單資料和契金資料（各作業類別金額欄位）
      const {
        work_01_amount, work_02_amount, work_03_amount, work_04_amount,
        work_05_amount, work_06_amount, work_07_amount,
        current_amount, cumulative_amount, remaining_amount,
        ...dispatchValues
      } = values;

      // 更新派工單
      updateMutation.mutate({
        ...dispatchValues,
        work_type: workTypeString,
      });

      // 計算本次派工金額（各作業類別金額總和）
      const calculatedCurrentAmount =
        (work_01_amount || 0) + (work_02_amount || 0) + (work_03_amount || 0) +
        (work_04_amount || 0) + (work_05_amount || 0) + (work_06_amount || 0) +
        (work_07_amount || 0);

      // 如果有任何金額資料，同時更新契金
      if (calculatedCurrentAmount > 0 || paymentData?.id) {
        const paymentValues: ContractPaymentCreate = {
          dispatch_order_id: parseInt(id || '0', 10),
          work_01_amount: work_01_amount || undefined,
          work_02_amount: work_02_amount || undefined,
          work_03_amount: work_03_amount || undefined,
          work_04_amount: work_04_amount || undefined,
          work_05_amount: work_05_amount || undefined,
          work_06_amount: work_06_amount || undefined,
          work_07_amount: work_07_amount || undefined,
          current_amount: calculatedCurrentAmount,
          // 累進派工金額和剩餘金額由後端自動計算，不傳送
        };
        paymentMutation.mutate(paymentValues);
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
        ? dispatch.work_type.split(',').map((t: string) => t.trim()).filter(Boolean)
        : [];

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
        // 各作業類別金額
        work_01_amount: paymentData?.work_01_amount,
        work_02_amount: paymentData?.work_02_amount,
        work_03_amount: paymentData?.work_03_amount,
        work_04_amount: paymentData?.work_04_amount,
        work_05_amount: paymentData?.work_05_amount,
        work_06_amount: paymentData?.work_06_amount,
        work_07_amount: paymentData?.work_07_amount,
      });
    }
  };

  // 作業類別與金額欄位對應
  const WORK_TYPE_AMOUNT_MAPPING: Record<string, { dateField: string; amountField: string; label: string }> = {
    '01.地上物查估作業': { dateField: 'work_01_date', amountField: 'work_01_amount', label: '01.地上物查估' },
    '02.土地協議市價查估作業': { dateField: 'work_02_date', amountField: 'work_02_amount', label: '02.土地協議市價查估' },
    '03.土地徵收市價查估作業': { dateField: 'work_03_date', amountField: 'work_03_amount', label: '03.土地徵收市價查估' },
    '04.相關計畫書製作': { dateField: 'work_04_date', amountField: 'work_04_amount', label: '04.相關計畫書製作' },
    '05.測量作業': { dateField: 'work_05_date', amountField: 'work_05_amount', label: '05.測量作業' },
    '06.樁位測釘作業': { dateField: 'work_06_date', amountField: 'work_06_amount', label: '06.樁位測釘作業' },
    '07.辦理教育訓練': { dateField: 'work_07_date', amountField: 'work_07_amount', label: '07.辦理教育訓練' },
  };

  // 計算本次派工金額總和
  const calculateCurrentAmount = (): number => {
    if (!paymentData) return 0;
    return (
      (paymentData.work_01_amount || 0) +
      (paymentData.work_02_amount || 0) +
      (paymentData.work_03_amount || 0) +
      (paymentData.work_04_amount || 0) +
      (paymentData.work_05_amount || 0) +
      (paymentData.work_06_amount || 0) +
      (paymentData.work_07_amount || 0)
    );
  };

  // 契金資訊區塊（唯讀和編輯模式共用）
  const renderPaymentSection = () => {
    // 使用頂層監聽的作業類別（避免在函數內使用 useWatch）
    const validWorkTypes = watchedWorkTypes.filter((wt) => WORK_TYPE_AMOUNT_MAPPING[wt]);

    // 格式化金額（整數，無小數）
    const formatCurrency = (val?: number | null) => {
      if (val === undefined || val === null || val === 0) return '-';
      return `$${Math.round(val).toLocaleString()}`;
    };

    // 計算編輯時的本次派工總金額（使用頂層監聽的各作業類別金額）
    const editCurrentAmount =
      (watchedWork01Amount || 0) +
      (watchedWork02Amount || 0) +
      (watchedWork03Amount || 0) +
      (watchedWork04Amount || 0) +
      (watchedWork05Amount || 0) +
      (watchedWork06Amount || 0) +
      (watchedWork07Amount || 0);

    // 計算本次派工金額（從 paymentData 取得各作業類別金額總和）
    const currentAmount = paymentData?.current_amount ?? calculateCurrentAmount();

    // 累進派工金額和剩餘金額從 API 取得（自動計算）
    const cumulativeAmount = paymentData?.cumulative_amount ?? 0;
    const remainingAmount = paymentData?.remaining_amount ?? 0;

    if (!isEditing) {
      // 唯讀模式：顯示契金摘要
      // 根據截圖調整順序：先顯示各作業類別金額，再顯示統計數據
      const workTypeItems = validWorkTypes.map((wt) => {
        const mapping = WORK_TYPE_AMOUNT_MAPPING[wt];
        if (!mapping) return null;
        const amount = paymentData?.[mapping.amountField as keyof typeof paymentData] as number | undefined;
        return {
          key: wt,
          label: `${mapping.label} 金額`,
          value: formatCurrency(amount),
        };
      }).filter(Boolean);

      return (
        <Descriptions size="small" column={3} bordered>
          {/* 先顯示各作業類別金額 */}
          {workTypeItems.map((item) => item && (
            <Descriptions.Item key={item.key} label={item.label}>
              {item.value}
            </Descriptions.Item>
          ))}
          {/* 再顯示統計數據 */}
          <Descriptions.Item label="本次派工總金額">
            <Text strong style={{ color: '#1890ff' }}>
              {formatCurrency(currentAmount)}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="累進派工金額（統計）">
            <Text>{formatCurrency(cumulativeAmount)}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="剩餘金額（統計）">
            <Text type={remainingAmount > 0 && remainingAmount < 1000000 ? 'warning' : undefined}>
              {formatCurrency(remainingAmount)}
            </Text>
          </Descriptions.Item>
        </Descriptions>
      );
    }

    // 編輯模式：顯示根據作業類別的金額輸入欄位
    return (
      <>
        {/* 各作業類別金額欄位 */}
        {validWorkTypes.length > 0 ? (
          <Row gutter={16}>
            {validWorkTypes.map((wt) => {
              const mapping = WORK_TYPE_AMOUNT_MAPPING[wt];
              if (!mapping) return null;
              return (
                <Col span={8} key={wt}>
                  <Form.Item name={mapping.amountField} label={`${mapping.label} 金額`}>
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      precision={0}
                      formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                      parser={(value) => Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0}
                      placeholder="輸入金額"
                    />
                  </Form.Item>
                </Col>
              );
            })}
          </Row>
        ) : (
          <Alert
            message="請先選擇作業類別"
            description="選擇作業類別後，將顯示對應的金額輸入欄位"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 金額彙總（本次派工總金額為各作業類別加總，累進派工金額、剩餘金額為自動計算） */}
        <Divider dashed style={{ margin: '12px 0' }} />
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="本次派工總金額（自動加總）">
              <InputNumber
                style={{ width: '100%' }}
                value={editCurrentAmount}
                disabled
                precision={0}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="累進派工金額（統計）">
              <InputNumber
                style={{ width: '100%' }}
                value={cumulativeAmount}
                disabled
                precision={0}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="剩餘金額（統計）">
              <InputNumber
                style={{ width: '100%' }}
                value={remainingAmount}
                disabled
                precision={0}
                formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
          </Col>
        </Row>
      </>
    );
  };

  // Tab 1: 派工資訊
  const renderInfoTab = () => (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      {/* 第一行：派工單號 + 工程名稱 */}
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

      {/* 第二行：作業類別 + 分案名稱 + 履約期限 */}
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="work_type" label="作業類別">
            <Select
              mode="multiple"
              allowClear
              placeholder="選擇作業類別（可多選）"
              maxTagCount={2}
            >
              {TAOYUAN_WORK_TYPES.map((type) => (
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
            tooltip="從機關承辦清單選擇（來源：承攬案件機關承辦）"
          >
            <Select
              placeholder="選擇案件承辦"
              allowClear
              showSearch
              optionFilterProp="label"
            >
              {agencyContacts.map((contact) => (
                <Option
                  key={contact.id}
                  value={contact.contact_name}
                  label={contact.contact_name}
                >
                  {contact.contact_name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="survey_unit"
            label="查估單位"
            tooltip="從協力廠商清單選擇（來源：承攬案件協力廠商）"
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
                  {vendor.vendor_name}
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

      {/* 契金資訊（唯讀和編輯模式都顯示） */}
      <Divider orientation="left">契金資訊</Divider>
      {renderPaymentSection()}

      {/* 唯讀模式下顯示系統資訊 */}
      {!isEditing && dispatch && (
        <>
          <Divider />
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="機關函文號">
              {(() => {
                // 從 linked_documents 取得機關來函（而非使用可能不一致的 agency_doc_id）
                const agencyDocs = (dispatch.linked_documents || [])
                  .filter((d: DispatchDocumentLink) => detectLinkType(d.doc_number) === 'agency_incoming')
                  .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
                    const dateA = a.doc_date || '9999-12-31';
                    const dateB = b.doc_date || '9999-12-31';
                    return dateA.localeCompare(dateB);
                  });
                return agencyDocs.length > 0 ? (agencyDocs[0]?.doc_number || '-') : '-';
              })()}
            </Descriptions.Item>
            <Descriptions.Item label="乾坤函文號">
              {(() => {
                // 從 linked_documents 取得乾坤發文（而非使用可能不一致的 company_doc_id）
                const companyDocs = (dispatch.linked_documents || [])
                  .filter((d: DispatchDocumentLink) => detectLinkType(d.doc_number) === 'company_outgoing')
                  .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
                    const dateA = a.doc_date || '9999-12-31';
                    const dateB = b.doc_date || '9999-12-31';
                    return dateA.localeCompare(dateB);
                  });
                return companyDocs.length > 0 ? (companyDocs[0]?.doc_number || '-') : '-';
              })()}
            </Descriptions.Item>
            <Descriptions.Item label="建立時間">
              {dispatch.created_at ? dayjs(dispatch.created_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Form>
  );

  // 處理公文關聯
  const handleLinkDocument = useCallback(() => {
    if (!selectedDocId) {
      message.warning('請先選擇要關聯的公文');
      return;
    }
    linkDocMutation.mutate({
      documentId: selectedDocId,
      linkType: selectedLinkType,
    });
  }, [selectedDocId, selectedLinkType, linkDocMutation, message]);

  // Tab 2: 公文關聯
  const renderDocumentsTab = () => {
    // 按公文日期排序（最新的排前面）
    const documents = [...(dispatch?.linked_documents || [])].sort((a, b) => {
      if (!a.doc_date && !b.doc_date) return 0;
      if (!a.doc_date) return 1;
      if (!b.doc_date) return -1;
      return new Date(b.doc_date).getTime() - new Date(a.doc_date).getTime();
    });

    return (
      <Spin spinning={isLoading}>
        {/* 新增關聯區塊 */}
        {canEdit && (
          <Card size="small" style={{ marginBottom: 16 }} title="新增公文關聯">
            <Row gutter={[12, 12]} align="middle">
              <Col span={10}>
                <Select
                  showSearch
                  allowClear
                  placeholder="搜尋公文字號或主旨..."
                  style={{ width: '100%' }}
                  value={selectedDocId}
                  onChange={(docId) => {
                    setSelectedDocId(docId);
                    // 自動判斷關聯類型
                    if (docId) {
                      const selectedDoc = availableDocs.find((d: OfficialDocument) => d.id === docId);
                      if (selectedDoc?.doc_number) {
                        setSelectedLinkType(detectLinkType(selectedDoc.doc_number));
                      }
                    }
                  }}
                  onSearch={setDocSearchKeyword}
                  filterOption={false}
                  notFoundContent={
                    docSearchKeyword ? (
                      <Empty description="無符合的公文" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : (
                      <Typography.Text type="secondary">請輸入關鍵字搜尋</Typography.Text>
                    )
                  }
                  loading={searchingDocs}
                >
                  {availableDocs.map((doc: OfficialDocument) => (
                    <Option key={doc.id} value={doc.id}>
                      <Space>
                        <Tag color={isReceiveDocument(doc.category) ? 'blue' : 'green'}>
                          {doc.doc_number || `#${doc.id}`}
                        </Tag>
                        <Text ellipsis style={{ maxWidth: 200 }}>
                          {doc.subject || '(無主旨)'}
                        </Text>
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Col>
              <Col span={8}>
                <Radio.Group
                  value={selectedLinkType}
                  onChange={(e) => setSelectedLinkType(e.target.value)}
                >
                  <Radio.Button value="agency_incoming">機關來函</Radio.Button>
                  <Radio.Button value="company_outgoing">乾坤發文</Radio.Button>
                </Radio.Group>
              </Col>
              <Col span={6}>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleLinkDocument}
                  loading={linkDocMutation.isPending}
                  disabled={!selectedDocId}
                >
                  建立關聯
                </Button>
              </Col>
            </Row>
          </Card>
        )}

        {/* 已關聯公文列表 */}
        {documents.length > 0 ? (
          <List
            dataSource={documents}
            renderItem={(doc: DispatchDocumentLink) => {
              // 使用 detectLinkType 根據公文字號校正關聯類型顯示
              // 解決資料庫中可能存在的錯誤 link_type 值
              const correctedLinkType = detectLinkType(doc.doc_number);
              const isAgencyIncoming = correctedLinkType === 'agency_incoming';

              return (
              <Card size="small" style={{ marginBottom: 12 }}>
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="公文字號">
                    <Space>
                      {doc.doc_date && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(doc.doc_date).format('YYYY-MM-DD')}
                        </Text>
                      )}
                      <Tag color={isAgencyIncoming ? 'blue' : 'green'}>
                        {doc.doc_number || `#${doc.document_id}`}
                      </Tag>
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="關聯類型">
                    <Tag color={isAgencyIncoming ? 'blue' : 'green'}>
                      {isAgencyIncoming ? '機關來函' : '乾坤發文'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="主旨" span={2}>
                    {doc.subject || '-'}
                  </Descriptions.Item>
                </Descriptions>
                <Space>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/documents/${doc.document_id}`)}
                  >
                    查看公文
                  </Button>
                  {canEdit && doc.link_id !== undefined && (
                    <Popconfirm
                      title="確定要移除此關聯嗎？"
                      onConfirm={() => {
                        if (doc.link_id === undefined || doc.link_id === null) {
                          message.error('關聯資料缺少 link_id，請重新整理頁面');
                          console.error('[unlinkDoc] link_id 缺失:', doc);
                          refetch();
                          return;
                        }
                        unlinkDocMutation.mutate(doc.link_id);
                      }}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button
                        type="link"
                        size="small"
                        danger
                        loading={unlinkDocMutation.isPending}
                      >
                        移除關聯
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              </Card>
              );
            }}
          />
        ) : (
          <Empty description="此派工單尚無關聯公文" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            {!canEdit && (
              <Button type="link" onClick={() => navigate('/taoyuan/dispatch')}>
                返回派工列表
              </Button>
            )}
          </Empty>
        )}
      </Spin>
    );
  };

  // 處理工程關聯
  const handleLinkProject = useCallback(() => {
    if (!selectedProjectId) {
      message.warning('請先選擇要關聯的工程');
      return;
    }
    linkProjectMutation.mutate(selectedProjectId);
  }, [selectedProjectId, linkProjectMutation, message]);

  // Tab 3: 工程關聯
  const renderProjectsTab = () => {
    const projects = dispatch?.linked_projects || [];

    return (
      <Spin spinning={isLoading}>
        {/* 新增關聯區塊 */}
        {canEdit && (
          <Card size="small" style={{ marginBottom: 16 }} title="新增工程關聯">
            <Row gutter={[12, 12]} align="middle">
              <Col span={16}>
                <Select
                  showSearch
                  allowClear
                  placeholder="搜尋工程名稱..."
                  style={{ width: '100%' }}
                  value={selectedProjectId}
                  onChange={setSelectedProjectId}
                  filterOption={(input, option) =>
                    String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  notFoundContent={
                    filteredProjects.length === 0 ? (
                      <Empty description="無可關聯的工程" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : undefined
                  }
                  options={filteredProjects.map((proj: TaoyuanProject) => ({
                    value: proj.id,
                    label: `${proj.project_name}${proj.district ? ` (${proj.district})` : ''}`,
                  }))}
                />
              </Col>
              <Col span={8}>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleLinkProject}
                  loading={linkProjectMutation.isPending}
                  disabled={!selectedProjectId}
                >
                  建立關聯
                </Button>
              </Col>
            </Row>
          </Card>
        )}

        {/* 已關聯工程列表 */}
        {projects.length > 0 ? (
          <List
            dataSource={projects}
            renderItem={(proj: LinkedProject) => (
              <Card size="small" style={{ marginBottom: 12 }}>
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="工程名稱" span={2}>
                    {proj.project_name || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="分案名稱">
                    {proj.sub_case_name || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="行政區">
                    {proj.district || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="案件承辦">
                    {proj.case_handler || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="案件類型">
                    {proj.case_type ? <Tag color="blue">{proj.case_type}</Tag> : '-'}
                  </Descriptions.Item>
                </Descriptions>
                <Space style={{ marginTop: 8 }}>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/taoyuan/project/${proj.project_id || proj.id}`)}
                  >
                    查看工程詳情
                  </Button>
                  {canEdit && (
                    <Popconfirm
                      title="確定要移除此關聯嗎？"
                      onConfirm={() => {
                        // 必須使用 link_id（關聯記錄 ID），不可使用 id（工程 ID）
                        const linkId = proj.link_id;
                        const projectId = proj.project_id ?? proj.id;

                        // 嚴格驗證：link_id 必須存在且不等於 project_id
                        if (linkId === undefined || linkId === null) {
                          message.error('關聯資料缺少 link_id，請重新整理頁面後再試');
                          console.error('[unlinkProject] link_id 缺失:', {
                            proj,
                            link_id: proj.link_id,
                            project_id: proj.project_id,
                            id: proj.id,
                          });
                          refetch(); // 自動重新載入數據
                          return;
                        }

                        if (!projectId) {
                          message.error('工程資料不完整，請重新整理頁面');
                          console.error('[unlinkProject] project_id 缺失:', proj);
                          return;
                        }

                        console.debug('[unlinkProject] 執行移除:', { linkId, projectId, proj });
                        unlinkProjectMutation.mutate(linkId);
                      }}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button
                        type="link"
                        size="small"
                        danger
                        loading={unlinkProjectMutation.isPending}
                      >
                        移除關聯
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              </Card>
            )}
          />
        ) : (
          <Empty description="此派工單尚無關聯工程" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            {!canEdit && (
              <Button type="link" onClick={() => navigate('/taoyuan/dispatch')}>
                返回派工列表
              </Button>
            )}
          </Empty>
        )}
      </Spin>
    );
  };

  // 取得檔案圖示
  const getFileIcon = (mimeType: string | undefined, filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (mimeType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '')) {
      return <FileImageOutlined style={{ fontSize: 24, color: '#52c41a' }} />;
    }
    if (mimeType === 'application/pdf' || ext === 'pdf') {
      return <FilePdfOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />;
    }
    return <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />;
  };

  // 判斷檔案是否可預覽
  const isPreviewable = (mimeType?: string, filename?: string): boolean => {
    // 根據 MIME type 判斷
    if (mimeType) {
      if (mimeType.startsWith('image/') ||
          mimeType === 'application/pdf' ||
          mimeType.startsWith('text/')) {
        return true;
      }
    }
    // 根據副檔名判斷
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  // 預覽附件
  const handlePreview = async (attachmentId: number, filename: string) => {
    try {
      const blob = await dispatchAttachmentsApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      // 10 秒後釋放記憶體
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      console.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  // 驗證檔案
  const validateFile = (file: File): { valid: boolean; message?: string } => {
    const maxSize = 50 * 1024 * 1024; // 50MB
    const allowedExts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar', '7z', 'txt', 'csv'];
    const ext = file.name.split('.').pop()?.toLowerCase();

    if (file.size > maxSize) {
      message.error(`檔案 ${file.name} 超過 50MB 限制`);
      return { valid: false, message: '檔案超過大小限制' };
    }
    if (!ext || !allowedExts.includes(ext)) {
      message.error(`檔案 ${file.name} 格式不支援`);
      return { valid: false, message: '不支援的檔案格式' };
    }
    return { valid: true };
  };

  // Tab 4: 附件管理
  const renderAttachmentsTab = () => {
    const uploadProps: UploadProps = {
      multiple: true,
      fileList,
      showUploadList: false,
      beforeUpload: (file: File) => {
        const validation = validateFile(file);
        if (!validation.valid) {
          return Upload.LIST_IGNORE;
        }
        return false;
      },
      onChange: ({ fileList: newFileList }: UploadChangeParam<UploadFile>) => {
        setFileList(newFileList);
      },
      onRemove: (file: UploadFile) => {
        setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
      },
    };

    return (
      <Spin spinning={isLoading}>
        {/* 上傳區塊（僅編輯模式顯示）*/}
        {isEditing && (
          <Card size="small" style={{ marginBottom: 16 }} title="上傳附件">
            <Dragger {...uploadProps} disabled={uploading}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">點擊或拖拽檔案到此區域上傳</p>
              <p className="ant-upload-hint">
                支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 50MB
              </p>
            </Dragger>

            {/* 待上傳檔案預覽 */}
            {fileList.length > 0 && !uploading && (
              <Card
                size="small"
                style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}
                title={
                  <span style={{ color: '#52c41a' }}>
                    <PaperClipOutlined style={{ marginRight: 8 }} />
                    待上傳檔案（{fileList.length} 個）
                  </span>
                }
              >
                <List
                  size="small"
                  dataSource={fileList}
                  renderItem={(file: UploadFile) => (
                    <List.Item
                      actions={[
                        <Button
                          key="remove"
                          type="link"
                          size="small"
                          danger
                          onClick={() => setFileList((prev) => prev.filter((f) => f.uid !== file.uid))}
                        >
                          移除
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                        title={file.name}
                        description={file.size ? `${(file.size / 1024).toFixed(1)} KB` : ''}
                      />
                    </List.Item>
                  )}
                />
                <Button
                  type="primary"
                  style={{ marginTop: 12 }}
                  onClick={() => uploadAttachmentsMutation.mutate()}
                  loading={uploading}
                >
                  開始上傳
                </Button>
              </Card>
            )}

            {/* 上傳進度 */}
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
          </Card>
        )}

        {/* 已上傳附件列表 */}
        {(attachments?.length ?? 0) > 0 ? (
          <Card
            size="small"
            title={
              <Space>
                <PaperClipOutlined />
                <span>已上傳附件（{attachments?.length ?? 0} 個）</span>
              </Space>
            }
          >
            <List
              size="small"
              dataSource={attachments}
              renderItem={(item: DispatchAttachment) => (
                <List.Item
                  actions={[
                    // 預覽按鈕（僅支援 PDF/圖片/文字檔）
                    isPreviewable(item.mime_type, item.original_name || item.file_name) && (
                      <Button
                        key="preview"
                        type="link"
                        size="small"
                        icon={<EyeOutlined />}
                        style={{ color: '#52c41a' }}
                        onClick={() =>
                          handlePreview(item.id, item.original_name || item.file_name)
                        }
                      >
                        預覽
                      </Button>
                    ),
                    <Button
                      key="download"
                      type="link"
                      size="small"
                      icon={<DownloadOutlined />}
                      onClick={() =>
                        dispatchAttachmentsApi.downloadAttachment(
                          item.id,
                          item.original_name || item.file_name
                        )
                      }
                    >
                      下載
                    </Button>,
                    isEditing && (
                      <Popconfirm
                        key="delete"
                        title="確定要刪除此附件嗎？"
                        description="刪除後無法復原，請確認是否繼續？"
                        onConfirm={() => deleteAttachmentMutation.mutate(item.id)}
                        okText="確定刪除"
                        okButtonProps={{ danger: true }}
                        cancelText="取消"
                      >
                        <Button
                          type="link"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          loading={deleteAttachmentMutation.isPending}
                        >
                          刪除
                        </Button>
                      </Popconfirm>
                    ),
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={getFileIcon(item.mime_type, item.original_name || item.file_name)}
                    title={item.original_name || item.file_name}
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
        ) : (
          !isEditing && (
            <Empty description="此派工單尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )
        )}
      </Spin>
    );
  };

  // 貨幣格式化 helper
  const currencyFormatter = (value: number | string | undefined) =>
    `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const currencyParser = (value: string | undefined) =>
    Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0;

  // 契金維護 Tab 內容
  const renderPaymentTab = () => {
    // 計算派工日期（機關第一筆來函日期）
    const getDispatchDate = () => {
      const agencyDocs = (dispatch?.linked_documents || [])
        .filter((link: DispatchDocumentLink) => link.link_type === 'agency_incoming' && link.doc_date)
        .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
          const dateA = a.doc_date || '9999-12-31';
          const dateB = b.doc_date || '9999-12-31';
          return dateA.localeCompare(dateB);
        });
      return agencyDocs[0]?.doc_date || null;
    };
    const dispatchDate = getDispatchDate();

    const handlePaymentSave = async () => {
      try {
        const values = await paymentForm.validateFields();

        // 計算本次派工金額（7種作業類別金額總和）
        const currentAmount =
          (values.work_01_amount || 0) +
          (values.work_02_amount || 0) +
          (values.work_03_amount || 0) +
          (values.work_04_amount || 0) +
          (values.work_05_amount || 0) +
          (values.work_06_amount || 0) +
          (values.work_07_amount || 0);

        const data: ContractPaymentCreate = {
          dispatch_order_id: parseInt(id || '0', 10),
          work_01_date: values.work_01_date?.format('YYYY-MM-DD'),
          work_01_amount: values.work_01_amount,
          work_02_date: values.work_02_date?.format('YYYY-MM-DD'),
          work_02_amount: values.work_02_amount,
          work_03_date: values.work_03_date?.format('YYYY-MM-DD'),
          work_03_amount: values.work_03_amount,
          work_04_date: values.work_04_date?.format('YYYY-MM-DD'),
          work_04_amount: values.work_04_amount,
          work_05_date: values.work_05_date?.format('YYYY-MM-DD'),
          work_05_amount: values.work_05_amount,
          work_06_date: values.work_06_date?.format('YYYY-MM-DD'),
          work_06_amount: values.work_06_amount,
          work_07_date: values.work_07_date?.format('YYYY-MM-DD'),
          work_07_amount: values.work_07_amount,
          current_amount: currentAmount,
          cumulative_amount: values.cumulative_amount,
          remaining_amount: values.remaining_amount,
          acceptance_date: values.acceptance_date?.format('YYYY-MM-DD'),
        };

        paymentMutation.mutate(data);
      } catch {
        // form validation error
      }
    };

    const handlePaymentEdit = () => {
      if (paymentData) {
        paymentForm.setFieldsValue({
          work_01_date: paymentData.work_01_date ? dayjs(paymentData.work_01_date) : null,
          work_01_amount: paymentData.work_01_amount,
          work_02_date: paymentData.work_02_date ? dayjs(paymentData.work_02_date) : null,
          work_02_amount: paymentData.work_02_amount,
          work_03_date: paymentData.work_03_date ? dayjs(paymentData.work_03_date) : null,
          work_03_amount: paymentData.work_03_amount,
          work_04_date: paymentData.work_04_date ? dayjs(paymentData.work_04_date) : null,
          work_04_amount: paymentData.work_04_amount,
          work_05_date: paymentData.work_05_date ? dayjs(paymentData.work_05_date) : null,
          work_05_amount: paymentData.work_05_amount,
          work_06_date: paymentData.work_06_date ? dayjs(paymentData.work_06_date) : null,
          work_06_amount: paymentData.work_06_amount,
          work_07_date: paymentData.work_07_date ? dayjs(paymentData.work_07_date) : null,
          work_07_amount: paymentData.work_07_amount,
          cumulative_amount: paymentData.cumulative_amount,
          remaining_amount: paymentData.remaining_amount,
          acceptance_date: paymentData.acceptance_date ? dayjs(paymentData.acceptance_date) : null,
        });
      }
      setIsPaymentEditing(true);
    };

    // 唯讀模式：顯示契金資訊
    if (!isPaymentEditing) {
      return (
        <div>
          {/* 派工基本資訊 */}
          <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
            <Row gutter={16}>
              <Col span={8}>
                <Text type="secondary">派工單號：</Text>
                <Text strong>{dispatch?.dispatch_no || '-'}</Text>
              </Col>
              <Col span={8}>
                <Text type="secondary">作業類別：</Text>
                {dispatch?.work_type ? <Tag color="blue">{dispatch.work_type}</Tag> : '-'}
              </Col>
              <Col span={8}>
                <Text type="secondary">派工日期：</Text>
                <Text strong style={{ color: '#1890ff' }}>
                  {dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '(尚無機關來函)'}
                </Text>
              </Col>
            </Row>
          </Card>

          <Space style={{ marginBottom: 16 }}>
            {canEdit && (
              <Button type="primary" icon={<EditOutlined />} onClick={handlePaymentEdit}>
                {paymentData ? '編輯契金' : '新增契金'}
              </Button>
            )}
          </Space>

          {paymentData ? (
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="01.地上物查估 - 派工日期">
                {paymentData.work_01_date ? dayjs(paymentData.work_01_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="01.地上物查估 - 金額">
                {paymentData.work_01_amount ? `$${Math.round(paymentData.work_01_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="02.土地協議市價查估 - 派工日期">
                {paymentData.work_02_date ? dayjs(paymentData.work_02_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="02.土地協議市價查估 - 金額">
                {paymentData.work_02_amount ? `$${Math.round(paymentData.work_02_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="03.土地徵收市價查估 - 派工日期">
                {paymentData.work_03_date ? dayjs(paymentData.work_03_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="03.土地徵收市價查估 - 金額">
                {paymentData.work_03_amount ? `$${Math.round(paymentData.work_03_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="04.相關計畫書製作 - 派工日期">
                {paymentData.work_04_date ? dayjs(paymentData.work_04_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="04.相關計畫書製作 - 金額">
                {paymentData.work_04_amount ? `$${Math.round(paymentData.work_04_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="05.測量作業 - 派工日期">
                {paymentData.work_05_date ? dayjs(paymentData.work_05_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="05.測量作業 - 金額">
                {paymentData.work_05_amount ? `$${Math.round(paymentData.work_05_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="06.樁位測釘作業 - 派工日期">
                {paymentData.work_06_date ? dayjs(paymentData.work_06_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="06.樁位測釘作業 - 金額">
                {paymentData.work_06_amount ? `$${Math.round(paymentData.work_06_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="07.辦理教育訓練 - 派工日期">
                {paymentData.work_07_date ? dayjs(paymentData.work_07_date).format('YYYY-MM-DD') : (dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '-')}
              </Descriptions.Item>
              <Descriptions.Item label="07.辦理教育訓練 - 金額">
                {paymentData.work_07_amount ? `$${Math.round(paymentData.work_07_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="本次派工總金額">
                <Text strong style={{ color: '#1890ff' }}>
                  {paymentData.current_amount ? `$${Math.round(paymentData.current_amount).toLocaleString()}` : '-'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="累進派工金額">
                {paymentData.cumulative_amount ? `$${Math.round(paymentData.cumulative_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="剩餘金額" span={2}>
                {paymentData.remaining_amount ? `$${Math.round(paymentData.remaining_amount).toLocaleString()}` : '-'}
              </Descriptions.Item>
            </Descriptions>
          ) : (
            <Empty description="尚無契金紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      );
    }

    // 編輯模式：表單輸入
    return (
      <Form form={paymentForm} layout="vertical">
        {/* 派工基本資訊（唯讀） */}
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <Row gutter={16}>
            <Col span={8}>
              <Text type="secondary">派工單號：</Text>
              <Text strong>{dispatch?.dispatch_no || '-'}</Text>
            </Col>
            <Col span={8}>
              <Text type="secondary">作業類別：</Text>
              {dispatch?.work_type ? <Tag color="blue">{dispatch.work_type}</Tag> : '-'}
            </Col>
            <Col span={8}>
              <Text type="secondary">派工日期：</Text>
              <Text strong style={{ color: '#1890ff' }}>
                {dispatchDate ? dayjs(dispatchDate).format('YYYY-MM-DD') : '(尚無機關來函)'}
              </Text>
            </Col>
          </Row>
        </Card>

        <Space style={{ marginBottom: 16 }}>
          <Button icon={<CloseOutlined />} onClick={() => setIsPaymentEditing(false)}>
            取消
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={paymentMutation.isPending}
            onClick={handlePaymentSave}
          >
            儲存
          </Button>
        </Space>

        <Divider orientation="left">作業類別派工金額</Divider>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_01_date" label="01.地上物查估 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_01_amount" label="01.地上物查估 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_02_date" label="02.土地協議市價查估 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_02_amount" label="02.土地協議市價查估 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_03_date" label="03.土地徵收市價查估 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_03_amount" label="03.土地徵收市價查估 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_04_date" label="04.相關計畫書製作 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_04_amount" label="04.相關計畫書製作 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_05_date" label="05.測量作業 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_05_amount" label="05.測量作業 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_06_date" label="06.樁位測釘作業 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_06_amount" label="06.樁位測釘作業 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="work_07_date" label="07.辦理教育訓練 - 派工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="work_07_amount" label="07.辦理教育訓練 - 金額">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">金額彙總</Divider>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="cumulative_amount" label="累進派工金額（統計）">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} disabled />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="remaining_amount" label="剩餘金額（統計）">
              <InputNumber style={{ width: '100%' }} min={0} precision={0} formatter={currencyFormatter} parser={currencyParser} disabled />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    );
  };

  // Tab 配置
  const tabs = [
    createTabItem(
      'info',
      { icon: <SendOutlined />, text: '派工資訊' },
      renderInfoTab()
    ),
    createTabItem(
      'documents',
      { icon: <FileTextOutlined />, text: '公文關聯', count: dispatch?.linked_documents?.length || 0 },
      renderDocumentsTab()
    ),
    createTabItem(
      'attachments',
      { icon: <PaperClipOutlined />, text: '派工附件', count: attachments?.length || 0 },
      renderAttachmentsTab()
    ),
    createTabItem(
      'projects',
      { icon: <ProjectOutlined />, text: '工程關聯', count: dispatch?.linked_projects?.length || 0 },
      renderProjectsTab()
    ),
  ];

  // Header 配置
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

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      loading={isLoading}
      hasData={!!dispatch}
    />
  );
};

export default TaoyuanDispatchDetailPage;
