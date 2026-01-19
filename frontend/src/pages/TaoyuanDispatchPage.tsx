/**
 * 桃園查估派工管理系統
 *
 * 四頁籤架構:
 * - Tab 1: 工程資訊 (轄管工程清單 + 派工工程)
 * - Tab 2: 函文紀錄 (公文管理)
 * - Tab 3: 派工紀錄
 * - Tab 4: 契金管控
 *
 * @version 2.0.0
 * @date 2026-01-19
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
  Card,
  Tag,
  Tabs,
  Table,
  Input,
  Select,
  Form,
  DatePicker,
  InputNumber,
  Statistic,
  Row,
  Col,
  Upload,
  Tooltip,
  Popconfirm,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
  FileExcelOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  DollarOutlined,
  ProjectOutlined,
  FileTextOutlined,
  SendOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useQueryClient, useQuery, useMutation } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload';
import dayjs from 'dayjs';

import { DocumentTabs } from '../components/document/DocumentTabs';
import { DocumentOperations, DocumentSendModal } from '../components/document/DocumentOperations';
import { DocumentImport } from '../components/document/DocumentImport';
import { exportDocumentsToExcel } from '../utils/exportUtils';
import {
  useDocuments,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useAuthGuard,
} from '../hooks';
import { Document, DocumentFilter as IDocumentFilter } from '../types';
import {
  TaoyuanProject,
  TaoyuanProjectCreate,
  TaoyuanProjectUpdate,
  DispatchOrder,
  DispatchOrderCreate,
  DispatchOrderUpdate,
  ContractPayment,
  ContractPaymentCreate,
  ContractPaymentUpdate,
  MasterControlItem,
  TAOYUAN_WORK_TYPES,
} from '../types/api';
import {
  taoyuanProjectsApi,
  dispatchOrdersApi,
  contractPaymentsApi,
  masterControlApi,
} from '../api/taoyuanDispatchApi';
import { calendarIntegrationService } from '../services/calendarIntegrationService';
import { queryKeys } from '../config/queryConfig';
import { logger } from '../utils/logger';

const { Title, Text } = Typography;
const { Search } = Input;

// 固定的承攬案件
const FIXED_CONTRACT_PROJECT_ID = 1; // 實際的承攬案件 ID
const FIXED_CONTRACT_CODE = 'CK2025_01_03_001';
const FIXED_CONTRACT_NAME =
  '115年度桃園市興辦公共設施用地取得所需土地市價及地上物查估、測量作業暨開瓶資料製作委託專業服務(開口契約)';

// ============================================================================
// Tab 1: 工程資訊組件
// ============================================================================

interface ProjectsTabProps {
  contractProjectId: number;
}

const ProjectsTab: React.FC<ProjectsTabProps> = ({ contractProjectId }) => {
  const { message } = App.useApp();
  const [searchText, setSearchText] = useState('');
  const [editingProject, setEditingProject] = useState<TaoyuanProject | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 查詢工程列表
  const {
    data: projectsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['taoyuan-projects', contractProjectId, searchText],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id: contractProjectId,
        search: searchText || undefined,
        limit: 1000,
      }),
  });

  const projects = projectsData?.items ?? [];

  // 建立/更新 mutation
  const createMutation = useMutation({
    mutationFn: (data: TaoyuanProjectCreate) => taoyuanProjectsApi.create(data),
    onSuccess: () => {
      message.success('工程新增成功');
      refetch();
      setModalVisible(false);
      form.resetFields();
    },
    onError: () => message.error('新增失敗'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: TaoyuanProjectUpdate }) =>
      taoyuanProjectsApi.update(id, data),
    onSuccess: () => {
      message.success('工程更新成功');
      refetch();
      setModalVisible(false);
      setEditingProject(null);
      form.resetFields();
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => taoyuanProjectsApi.delete(id),
    onSuccess: () => {
      message.success('工程刪除成功');
      refetch();
    },
    onError: () => message.error('刪除失敗'),
  });

  const handleEdit = (project: TaoyuanProject) => {
    setEditingProject(project);
    form.setFieldsValue(project);
    setModalVisible(true);
  };

  const handleCreate = () => {
    setEditingProject(null);
    form.resetFields();
    form.setFieldsValue({ contract_project_id: contractProjectId });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editingProject) {
      updateMutation.mutate({ id: editingProject.id, data: values });
    } else {
      createMutation.mutate({ ...values, contract_project_id: contractProjectId });
    }
  };

  const handleImport = async (file: File) => {
    try {
      const result = await taoyuanProjectsApi.importExcel(file, contractProjectId);
      if (result.success) {
        message.success(`匯入成功: ${result.imported_count} 筆`);
        refetch();
      } else {
        message.error(`匯入失敗: ${result.errors.map((e) => e.message).join(', ')}`);
      }
    } catch {
      message.error('匯入失敗');
    }
    setImportModalVisible(false);
  };

  const columns: ColumnsType<TaoyuanProject> = [
    {
      title: '項次',
      dataIndex: 'sequence_no',
      width: 70,
      render: (val: number | undefined, _record: TaoyuanProject, index: number) => val ?? index + 1,
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      width: 250,
      ellipsis: true,
    },
    {
      title: '子案名稱',
      dataIndex: 'sub_case_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '行政區',
      dataIndex: 'district',
      width: 80,
    },
    {
      title: '審議年度',
      dataIndex: 'review_year',
      width: 90,
    },
    {
      title: '案件類型',
      dataIndex: 'case_type',
      width: 100,
    },
    {
      title: '承辦人',
      dataIndex: 'case_handler',
      width: 100,
    },
    {
      title: '土地協議進度',
      dataIndex: 'land_agreement_status',
      width: 120,
      render: (val?: string) => val ? <Tag color="blue">{val}</Tag> : '-',
    },
    {
      title: '地上物查估進度',
      dataIndex: 'building_survey_status',
      width: 120,
      render: (val?: string) => val ? <Tag color="green">{val}</Tag> : '-',
    },
    {
      title: '驗收狀態',
      dataIndex: 'acceptance_status',
      width: 100,
      render: (val?: string) =>
        val === '已驗收' ? <Badge status="success" text={val} /> : (val || '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm title="確定刪除?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 統計資料 (基於進度狀態判斷)
  const dispatchedCount = projects.filter((p) => p.land_agreement_status || p.building_survey_status).length;
  const completedCount = projects.filter((p) => p.acceptance_status === '已驗收').length;

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="總工程數" value={projects.length} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已派工"
              value={dispatchedCount}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SendOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={completedCount}
              valueStyle={{ color: '#52c41a' }}
              prefix={<Badge status="success" />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="完成率"
              value={projects.length ? Math.round((completedCount / projects.length) * 100) : 0}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 */}
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜尋工程名稱"
          allowClear
          onSearch={setSearchText}
          style={{ width: 250 }}
        />
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          重新整理
        </Button>
        <Button icon={<UploadOutlined />} onClick={() => setImportModalVisible(true)}>
          Excel 匯入
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新增工程
        </Button>
      </Space>

      {/* 工程列表表格 */}
      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1300 }}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 筆`,
        }}
      />

      {/* 新增/編輯 Modal */}
      <Modal
        title={editingProject ? '編輯工程' : '新增工程'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingProject(null);
          form.resetFields();
        }}
        width={600}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="project_name" label="工程名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="sub_case_name" label="子案名稱">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="district" label="區域">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="review_year" label="年度">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="work_type" label="工程類別">
                <Select allowClear>
                  {TAOYUAN_WORK_TYPES.map((type) => (
                    <Select.Option key={type} value={type}>
                      {type}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="estimated_count" label="預估筆數">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="case_handler" label="承辦人">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cloud_path" label="雲端路徑">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Excel 匯入 Modal */}
      <Modal
        title="Excel 匯入工程資料"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
      >
        <Upload.Dragger
          accept=".xlsx,.xls"
          maxCount={1}
          beforeUpload={(file) => {
            handleImport(file);
            return false;
          }}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">點擊或拖曳 Excel 檔案至此</p>
          <p className="ant-upload-hint">支援 .xlsx, .xls 格式</p>
        </Upload.Dragger>
      </Modal>
    </div>
  );
};

// ============================================================================
// Tab 2: 函文紀錄組件 (整合現有公文管理)
// ============================================================================

interface DocumentsTabProps {
  contractCode: string;
}

const DocumentsTab: React.FC<DocumentsTabProps> = ({ contractCode }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const { hasPermission } = useAuthGuard();
  const canCreate = hasPermission('documents:create');
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  const [filters, setFilters] = useState<IDocumentFilter>({
    contract_case: contractCode,
  });

  const [pagination, setPagination] = useState({ page: 1, limit: 20 });
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  const [deleteModal, setDeleteModal] = useState<{ open: boolean; document: Document | null }>({
    open: false,
    document: null,
  });
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isAddingToCalendar, setIsAddingToCalendar] = useState(false);

  const [documentOperation, setDocumentOperation] = useState<{
    type: 'view' | 'edit' | 'create' | 'copy' | null;
    document: Document | null;
    visible: boolean;
  }>({ type: null, document: null, visible: false });

  const [sendModal, setSendModal] = useState<{ visible: boolean; document: Document | null }>({
    visible: false,
    document: null,
  });

  const {
    data: documentsData,
    isLoading,
    error: queryError,
    refetch,
  } = useDocuments({
    ...filters,
    page: pagination.page,
    limit: pagination.limit,
    ...(sortField && { sortBy: sortField }),
    ...(sortOrder && { sortOrder: sortOrder === 'ascend' ? 'asc' : 'desc' }),
  });

  const documents = documentsData?.items ?? [];
  const totalCount = documentsData?.pagination?.total ?? 0;

  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();
  const deleteMutation = useDeleteDocument();

  const forceRefresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    await refetch();
  }, [queryClient, refetch]);

  useEffect(() => {
    if (queryError) {
      message.error(queryError instanceof Error ? queryError.message : '載入公文資料失敗');
    }
  }, [queryError, message]);

  const handleFiltersChange = (newFilters: IDocumentFilter) => {
    setPagination({ ...pagination, page: 1 });
    setFilters({ ...newFilters, contract_case: contractCode });
  };

  const handleTableChange = (paginationInfo: any, _: any, sorter: any) => {
    if (
      paginationInfo &&
      (paginationInfo.current !== pagination.page || paginationInfo.pageSize !== pagination.limit)
    ) {
      setPagination({
        page: paginationInfo.current || 1,
        limit: paginationInfo.pageSize || 20,
      });
    }

    if (sorter && sorter.field) {
      setSortField(sorter.field);
      setSortOrder(sorter.order);
    } else {
      setSortField('');
      setSortOrder(null);
    }
  };

  const handleViewDocument = (document: Document) => {
    setDocumentOperation({ type: 'view', document, visible: true });
  };

  const handleEditDocument = (document: Document) => {
    setDocumentOperation({ type: 'edit', document, visible: true });
  };

  const handleCreateDocument = () => {
    navigate('/documents/create');
  };

  const handleDeleteDocument = (document: Document) => {
    setDeleteModal({ open: true, document });
  };

  const handleAddToCalendar = async (document: Document) => {
    setIsAddingToCalendar(true);
    try {
      await calendarIntegrationService.addDocumentToCalendar(document);
    } catch (error) {
      logger.error('Calendar integration failed:', error);
    } finally {
      setIsAddingToCalendar(false);
    }
  };

  const handleSaveDocument = async (documentData: Partial<Document>): Promise<Document | void> => {
    try {
      let result: Document;

      if (documentOperation.type === 'create' || documentOperation.type === 'copy') {
        result = await createMutation.mutateAsync(documentData as any);
        message.success('公文新增成功！');
      } else if (documentOperation.type === 'edit' && documentOperation.document?.id) {
        result = await updateMutation.mutateAsync({
          documentId: documentOperation.document.id,
          data: documentData as any,
        });
        message.success('公文更新成功！');
      } else {
        return;
      }

      setDocumentOperation({ type: null, document: null, visible: false });
      return result;
    } catch (error) {
      logger.error('Save document error:', error);
      throw error;
    }
  };

  const handleConfirmDelete = async () => {
    if (deleteModal.document) {
      try {
        await deleteMutation.mutateAsync(deleteModal.document.id);
        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        setDeleteModal({ open: false, document: null });
      } catch {
        message.error('刪除公文失敗');
      }
    }
  };

  const handleSend = async () => {
    try {
      message.success('公文發送成功！');
      setSendModal({ visible: false, document: null });
      await forceRefresh();
    } catch (error) {
      throw error;
    }
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      const now = new Date();
      const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `桃園查估派工函文紀錄_${dateStr}`;
      await exportDocumentsToExcel(documents, filename, filters);
      message.success('文件已成功匯出');
    } catch {
      message.error('匯出 Excel 失敗');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={() => forceRefresh()} loading={isLoading}>
          重新整理
        </Button>
        <Button icon={<FileExcelOutlined />} onClick={handleExportExcel} loading={isExporting}>
          匯出 Excel
        </Button>
        {canCreate && (
          <Button icon={<UploadOutlined />} onClick={() => setImportModalVisible(true)}>
            公文匯入
          </Button>
        )}
        {canCreate && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateDocument}>
            新增公文
          </Button>
        )}
      </Space>

      <DocumentTabs
        documents={documents}
        loading={isLoading}
        filters={{ ...filters, page: pagination.page, limit: pagination.limit }}
        total={totalCount}
        onEdit={canEdit ? handleEditDocument : () => {}}
        onDelete={canDelete ? handleDeleteDocument : () => {}}
        onView={handleViewDocument}
        onExport={handleExportExcel}
        onTableChange={handleTableChange}
        onFiltersChange={handleFiltersChange}
        isExporting={isExporting}
        onAddToCalendar={handleAddToCalendar}
        isAddingToCalendar={isAddingToCalendar}
      />

      <Modal
        title="確認刪除"
        open={deleteModal.open}
        onOk={handleConfirmDelete}
        onCancel={() => setDeleteModal({ open: false, document: null })}
        okText="刪除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
        confirmLoading={deleteMutation.isPending}
      >
        <p>確定要刪除公文「{deleteModal.document?.doc_number}」嗎？此操作無法復原。</p>
      </Modal>

      <DocumentImport
        visible={importModalVisible}
        onClose={() => setImportModalVisible(false)}
        onSuccess={forceRefresh}
      />

      <DocumentOperations
        document={documentOperation.document}
        operation={documentOperation.type}
        visible={documentOperation.visible}
        onClose={() => setDocumentOperation({ type: null, document: null, visible: false })}
        onSave={handleSaveDocument}
      />

      <DocumentSendModal
        document={sendModal.document}
        visible={sendModal.visible}
        onClose={() => setSendModal({ visible: false, document: null })}
        onSend={handleSend}
      />
    </div>
  );
};

// ============================================================================
// Tab 3: 派工紀錄組件
// ============================================================================

interface DispatchOrdersTabProps {
  contractProjectId: number;
}

const DispatchOrdersTab: React.FC<DispatchOrdersTabProps> = ({ contractProjectId }) => {
  const { message } = App.useApp();
  const [searchText, setSearchText] = useState('');
  const [editingOrder, setEditingOrder] = useState<DispatchOrder | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const {
    data: ordersData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['dispatch-orders', contractProjectId, searchText],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: contractProjectId,
        search: searchText || undefined,
        limit: 1000,
      }),
  });

  const orders = ordersData?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (data: DispatchOrderCreate) => dispatchOrdersApi.create(data),
    onSuccess: () => {
      message.success('派工單新增成功');
      refetch();
      setModalVisible(false);
      form.resetFields();
    },
    onError: () => message.error('新增失敗'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: DispatchOrderUpdate }) =>
      dispatchOrdersApi.update(id, data),
    onSuccess: () => {
      message.success('派工單更新成功');
      refetch();
      setModalVisible(false);
      setEditingOrder(null);
      form.resetFields();
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => dispatchOrdersApi.delete(id),
    onSuccess: () => {
      message.success('派工單刪除成功');
      refetch();
    },
    onError: () => message.error('刪除失敗'),
  });

  const handleEdit = (order: DispatchOrder) => {
    setEditingOrder(order);
    form.setFieldsValue({
      dispatch_no: order.dispatch_no,
      project_name: order.project_name,
      work_type: order.work_type,
      sub_case_name: order.sub_case_name,
      deadline: order.deadline,
      case_handler: order.case_handler,
      survey_unit: order.survey_unit,
      cloud_folder: order.cloud_folder,
      project_folder: order.project_folder,
    });
    setModalVisible(true);
  };

  const handleCreate = () => {
    setEditingOrder(null);
    form.resetFields();
    form.setFieldsValue({ contract_project_id: contractProjectId });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const data: DispatchOrderCreate | DispatchOrderUpdate = {
      dispatch_no: values.dispatch_no,
      project_name: values.project_name,
      work_type: values.work_type,
      sub_case_name: values.sub_case_name,
      deadline: values.deadline,
      case_handler: values.case_handler,
      survey_unit: values.survey_unit,
      cloud_folder: values.cloud_folder,
      project_folder: values.project_folder,
    };

    if (editingOrder) {
      updateMutation.mutate({ id: editingOrder.id, data: data as DispatchOrderUpdate });
    } else {
      createMutation.mutate({ ...data, contract_project_id: contractProjectId } as DispatchOrderCreate);
    }
  };

  const statusColors: Record<string, string> = {
    draft: 'default',
    dispatched: 'processing',
    in_progress: 'warning',
    completed: 'success',
    cancelled: 'error',
  };

  const statusLabels: Record<string, string> = {
    draft: '草稿',
    dispatched: '已派工',
    in_progress: '進行中',
    completed: '已完成',
    cancelled: '已取消',
  };

  const columns: ColumnsType<DispatchOrder> = [
    {
      title: '派工編號',
      dataIndex: 'dispatch_number',
      width: 120,
    },
    {
      title: '標題',
      dataIndex: 'title',
      width: 200,
      ellipsis: true,
    },
    {
      title: '派工機關',
      dataIndex: 'dispatch_agency',
      width: 150,
    },
    {
      title: '派工日期',
      dataIndex: 'dispatch_date',
      width: 110,
      render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
    },
    {
      title: '應完成日',
      dataIndex: 'deadline_date',
      width: 110,
      render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 90,
      render: (val: string) => (
        <Tag color={statusColors[val] || 'default'}>{statusLabels[val] || val}</Tag>
      ),
    },
    {
      title: '實收金額',
      dataIndex: 'actual_payment',
      width: 110,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm title="確定刪除?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜尋派工單"
          allowClear
          onSearch={setSearchText}
          style={{ width: 250 }}
        />
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          重新整理
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新增派工單
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={orders}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1100 }}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 筆`,
        }}
      />

      <Modal
        title={editingOrder ? '編輯派工單' : '新增派工單'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingOrder(null);
          form.resetFields();
        }}
        width={700}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="dispatch_number" label="派工編號">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="狀態" rules={[{ required: true }]}>
                <Select>
                  <Select.Option value="draft">草稿</Select.Option>
                  <Select.Option value="dispatched">已派工</Select.Option>
                  <Select.Option value="in_progress">進行中</Select.Option>
                  <Select.Option value="completed">已完成</Select.Option>
                  <Select.Option value="cancelled">已取消</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="title" label="標題" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="dispatch_agency" label="派工機關">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="actual_payment" label="實收金額">
                <InputNumber
                  style={{ width: '100%' }}
                  formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => value?.replace(/\$\s?|(,*)/g, '') as unknown as number}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="dispatch_date" label="派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="received_date" label="收件日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="deadline_date" label="應完成日">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="說明">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

// ============================================================================
// Tab 4: 契金管控組件
// ============================================================================

interface PaymentsTabProps {
  contractProjectId: number;
}

const PaymentsTab: React.FC<PaymentsTabProps> = ({ contractProjectId }) => {
  const { message } = App.useApp();

  // 先查詢派工單列表以取得 dispatch_order_id
  const { data: ordersData } = useQuery({
    queryKey: ['dispatch-orders', contractProjectId],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: contractProjectId,
        limit: 1000,
      }),
  });

  const orders = ordersData?.items ?? [];
  const [selectedOrderId, setSelectedOrderId] = useState<number | undefined>();

  const {
    data: paymentsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['contract-payments', selectedOrderId],
    queryFn: () => (selectedOrderId ? contractPaymentsApi.getList(selectedOrderId) : null),
    enabled: !!selectedOrderId,
  });

  const payments = paymentsData?.items ?? [];
  // 計算彙總金額
  const totalCurrentAmount = payments.reduce((sum, p) => sum + (p.current_amount ?? 0), 0);
  const totalCumulativeAmount = payments.reduce((sum, p) => sum + (p.cumulative_amount ?? 0), 0);
  const totalRemainingAmount = payments.reduce((sum, p) => sum + (p.remaining_amount ?? 0), 0);

  const [editingPayment, setEditingPayment] = useState<ContractPayment | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const createMutation = useMutation({
    mutationFn: (data: ContractPaymentCreate) => contractPaymentsApi.create(data),
    onSuccess: () => {
      message.success('契金紀錄新增成功');
      refetch();
      setModalVisible(false);
      form.resetFields();
    },
    onError: () => message.error('新增失敗'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ContractPaymentUpdate }) =>
      contractPaymentsApi.update(id, data),
    onSuccess: () => {
      message.success('契金紀錄更新成功');
      refetch();
      setModalVisible(false);
      setEditingPayment(null);
      form.resetFields();
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => contractPaymentsApi.delete(id),
    onSuccess: () => {
      message.success('契金紀錄刪除成功');
      refetch();
    },
    onError: () => message.error('刪除失敗'),
  });

  const handleEdit = (payment: ContractPayment) => {
    setEditingPayment(payment);
    form.setFieldsValue({
      work_01_date: payment.work_01_date ? dayjs(payment.work_01_date) : null,
      work_01_amount: payment.work_01_amount,
      work_02_date: payment.work_02_date ? dayjs(payment.work_02_date) : null,
      work_02_amount: payment.work_02_amount,
      work_03_date: payment.work_03_date ? dayjs(payment.work_03_date) : null,
      work_03_amount: payment.work_03_amount,
      work_04_date: payment.work_04_date ? dayjs(payment.work_04_date) : null,
      work_04_amount: payment.work_04_amount,
      work_05_date: payment.work_05_date ? dayjs(payment.work_05_date) : null,
      work_05_amount: payment.work_05_amount,
      work_06_date: payment.work_06_date ? dayjs(payment.work_06_date) : null,
      work_06_amount: payment.work_06_amount,
      work_07_date: payment.work_07_date ? dayjs(payment.work_07_date) : null,
      work_07_amount: payment.work_07_amount,
      current_amount: payment.current_amount,
      cumulative_amount: payment.cumulative_amount,
      remaining_amount: payment.remaining_amount,
      acceptance_date: payment.acceptance_date ? dayjs(payment.acceptance_date) : null,
    });
    setModalVisible(true);
  };

  const handleCreate = () => {
    if (!selectedOrderId) {
      message.warning('請先選擇派工單');
      return;
    }
    setEditingPayment(null);
    form.resetFields();
    form.setFieldsValue({ dispatch_order_id: selectedOrderId });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const data: ContractPaymentCreate = {
      dispatch_order_id: selectedOrderId!,
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
      current_amount: values.current_amount,
      cumulative_amount: values.cumulative_amount,
      remaining_amount: values.remaining_amount,
      acceptance_date: values.acceptance_date?.format('YYYY-MM-DD'),
    };

    if (editingPayment) {
      const { dispatch_order_id, ...updateData } = data;
      updateMutation.mutate({ id: editingPayment.id, data: updateData });
    } else {
      createMutation.mutate(data);
    }
  };

  const columns: ColumnsType<ContractPayment> = [
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 120,
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '本次派工金額',
      dataIndex: 'current_amount',
      width: 130,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '累進派工金額',
      dataIndex: 'cumulative_amount',
      width: 130,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '剩餘金額',
      dataIndex: 'remaining_amount',
      width: 130,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '驗收日期',
      dataIndex: 'acceptance_date',
      width: 110,
      render: (val?: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm title="確定刪除?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="本次派工金額"
              value={totalCurrentAmount}
              prefix={<DollarOutlined />}
              precision={0}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="累進派工金額" value={totalCumulativeAmount} precision={0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="剩餘金額"
              value={totalRemainingAmount}
              valueStyle={{ color: '#1890ff' }}
              precision={0}
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 */}
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="選擇派工單"
          style={{ width: 300 }}
          value={selectedOrderId}
          onChange={setSelectedOrderId}
          allowClear
        >
          {orders.map((order) => (
            <Select.Option key={order.id} value={order.id}>
              {order.dispatch_no || `派工單 #${order.id}`} - {order.project_name || ''}
            </Select.Option>
          ))}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()} disabled={!selectedOrderId}>
          重新整理
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate} disabled={!selectedOrderId}>
          新增契金紀錄
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={payments}
        rowKey="id"
        loading={isLoading}
        pagination={{
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 筆`,
        }}
      />

      <Modal
        title={editingPayment ? '編輯契金紀錄' : '新增契金紀錄'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingPayment(null);
          form.resetFields();
        }}
        width={800}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="dispatch_order_id" hidden>
            <Input />
          </Form.Item>

          <Title level={5}>作業類別派工</Title>
          {/* 01.地上物查估作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_01_date" label="01.地上物查估 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_01_amount" label="01.地上物查估 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 02.土地協議市價查估作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_02_date" label="02.土地協議市價查估 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_02_amount" label="02.土地協議市價查估 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 03.土地徵收市價查估作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_03_date" label="03.土地徵收市價查估 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_03_amount" label="03.土地徵收市價查估 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 04.相關計畫書製作 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_04_date" label="04.相關計畫書製作 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_04_amount" label="04.相關計畫書製作 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 05.測量作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_05_date" label="05.測量作業 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_05_amount" label="05.測量作業 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 06.樁位測釘作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_06_date" label="06.樁位測釘作業 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_06_amount" label="06.樁位測釘作業 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 07.辦理教育訓練 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_07_date" label="07.辦理教育訓練 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_07_amount" label="07.辦理教育訓練 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>

          <Title level={5} style={{ marginTop: 16 }}>金額彙總</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="current_amount" label="本次派工金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="cumulative_amount" label="累進派工金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="remaining_amount" label="剩餘金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="acceptance_date" label="完成驗收日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

// ============================================================================
// 主頁面組件
// ============================================================================

export const TaoyuanDispatchPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('1');

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>
          桃園查估派工管理系統
        </Title>
        <Text type="secondary">派工管理 / 函文紀錄 / 契金管控</Text>
      </div>

      {/* 專案資訊卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <Tag color="blue">承攬案件</Tag>
          <Tag color="cyan">{FIXED_CONTRACT_CODE}</Tag>
          <Text strong style={{ fontSize: '14px' }}>
            {FIXED_CONTRACT_NAME}
          </Text>
        </div>
      </Card>

      {/* TAB 頁籤 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        size="large"
        items={[
          {
            key: '1',
            label: (
              <span>
                <ProjectOutlined />
                工程資訊
              </span>
            ),
            children: <ProjectsTab contractProjectId={FIXED_CONTRACT_PROJECT_ID} />,
          },
          {
            key: '2',
            label: (
              <span>
                <FileTextOutlined />
                函文紀錄
              </span>
            ),
            children: <DocumentsTab contractCode={FIXED_CONTRACT_CODE} />,
          },
          {
            key: '3',
            label: (
              <span>
                <SendOutlined />
                派工紀錄
              </span>
            ),
            children: <DispatchOrdersTab contractProjectId={FIXED_CONTRACT_PROJECT_ID} />,
          },
          {
            key: '4',
            label: (
              <span>
                <DollarOutlined />
                契金管控
              </span>
            ),
            children: <PaymentsTab contractProjectId={FIXED_CONTRACT_PROJECT_ID} />,
          },
        ]}
      />
    </div>
  );
};

export default TaoyuanDispatchPage;
