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
} from 'antd';
import {
  SendOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ProjectOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import { dispatchOrdersApi, taoyuanProjectsApi, projectLinksApi } from '../api/taoyuanDispatchApi';
import { documentsApi } from '../api/documentsApi';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import type { DispatchOrder, DispatchOrderUpdate, OfficialDocument, LinkType, TaoyuanProject } from '../types/api';
import { TAOYUAN_WORK_TYPES, isReceiveDocument } from '../types/api';
import { useAuthGuard } from '../hooks';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';

const { Option } = Select;
const { Text } = Typography;

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
  const linkedDocIds = (dispatch?.linked_documents || []).map((d: any) => d.document_id);
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
  const linkedProjectIds = (dispatch?.linked_projects || []).map((p: any) => p.project_id);
  // 過濾掉已關聯的工程
  const filteredProjects = availableProjects.filter(
    (proj: TaoyuanProject) => !linkedProjectIds.includes(proj.id)
  );

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
  // linked_projects 實際結構包含 link_id, project_id 及專案欄位
  type LinkedProject = TaoyuanProject & { link_id: number; project_id: number };
  const unlinkProjectMutation = useMutation({
    mutationFn: (linkId: number) => {
      const linkedProjects = (dispatch?.linked_projects || []) as LinkedProject[];
      const targetProject = linkedProjects.find((p) => p.link_id === linkId);
      return projectLinksApi.unlinkDispatch(targetProject?.project_id || 0, linkId);
    },
    onSuccess: () => {
      message.success('已移除工程關聯');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] });
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects'] });
    },
    onError: () => message.error('移除關聯失敗'),
  });

  // 設定表單初始值
  useEffect(() => {
    if (dispatch) {
      form.setFieldsValue({
        dispatch_no: dispatch.dispatch_no,
        project_name: dispatch.project_name,
        work_type: dispatch.work_type,
        sub_case_name: dispatch.sub_case_name,
        deadline: dispatch.deadline,
        case_handler: dispatch.case_handler,
        survey_unit: dispatch.survey_unit,
        contact_note: dispatch.contact_note,
        cloud_folder: dispatch.cloud_folder,
        project_folder: dispatch.project_folder,
      });
    }
  }, [dispatch, form]);

  // 儲存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      updateMutation.mutate(values);
    } catch (error) {
      message.error('請檢查表單欄位');
    }
  };

  // 取消編輯
  const handleCancelEdit = () => {
    setIsEditing(false);
    if (dispatch) {
      form.setFieldsValue({
        dispatch_no: dispatch.dispatch_no,
        project_name: dispatch.project_name,
        work_type: dispatch.work_type,
        sub_case_name: dispatch.sub_case_name,
        deadline: dispatch.deadline,
        case_handler: dispatch.case_handler,
        survey_unit: dispatch.survey_unit,
        contact_note: dispatch.contact_note,
        cloud_folder: dispatch.cloud_folder,
        project_folder: dispatch.project_folder,
      });
    }
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
            <Select allowClear placeholder="選擇作業類別">
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
                  <div>
                    <div>{contact.contact_name}</div>
                    {(contact.position || contact.department) && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
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
                  <div>
                    <div>{vendor.vendor_name}</div>
                    {(vendor.role || vendor.vendor_business_type) && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
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

      {/* 唯讀模式下顯示系統資訊 */}
      {!isEditing && dispatch && (
        <>
          <Divider />
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="機關函文號">
              {dispatch.agency_doc_number || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="乾坤函文號">
              {dispatch.company_doc_number || '-'}
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
    const documents = dispatch?.linked_documents || [];

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
                  onChange={setSelectedDocId}
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
            renderItem={(doc: any) => (
              <Card size="small" style={{ marginBottom: 12 }}>
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="公文字號">
                    <Tag color={doc.link_type === 'agency_incoming' ? 'blue' : 'green'}>
                      {doc.doc_number || `#${doc.document_id}`}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="關聯類型">
                    {doc.link_type === 'agency_incoming' ? '機關來函' : '乾坤發文'}
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
                  {canEdit && (
                    <Popconfirm
                      title="確定要移除此關聯嗎？"
                      onConfirm={() => unlinkDocMutation.mutate(doc.link_id)}
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
            )}
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
            renderItem={(proj: any) => (
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
                    onClick={() => navigate(`/taoyuan/project/${proj.project_id}`)}
                  >
                    查看工程詳情
                  </Button>
                  {canEdit && (
                    <Popconfirm
                      title="確定要移除此關聯嗎？"
                      onConfirm={() => unlinkProjectMutation.mutate(proj.link_id)}
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
