import React, { useState, useEffect, useRef } from 'react';
import type { InputRef, TableColumnType } from 'antd';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import {
  Card,
  Button,
  Space,
  Input,
  Select,
  Row,
  Col,
  Table,
  Tag,
  Statistic,
  Switch,
  Pagination,
  Typography,
  Empty,
  Spin,
  Modal,
  Form,
  Popconfirm,
  DatePicker,
  InputNumber,
  App,
} from 'antd';
import {
  PlusOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  TeamOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import ProjectVendorManagement from '../components/project/ProjectVendorManagement';
// 使用統一 API 服務
import { projectsApi } from '../api/projectsApi';

const { Title } = Typography;
const { Option } = Select;

// 案件類別選項 (與 ContractCaseDetailPage 保持一致)
const CATEGORY_OPTIONS = [
  { value: '01', label: '01委辦案件', color: 'blue' },
  { value: '02', label: '02協力計畫', color: 'green' },
  { value: '03', label: '03小額採購', color: 'orange' },
  { value: '04', label: '04其他類別', color: 'default' },
];

// 類別映射表 (處理舊資料格式)
const CATEGORY_MAP: Record<string, string> = {
  '01': '01', '委辦案件': '01', '01委辦案件': '01',
  '02': '02', '協力計畫': '02', '02協力計畫': '02',
  '03': '03', '小額採購': '03', '03小額採購': '03',
  '04': '04', '其他類別': '04', '04其他類別': '04',
};

// 取得標準化類別代碼
const normalizeCategory = (category?: string): string => {
  if (!category) return '';
  return CATEGORY_MAP[category] || category;
};

// 取得類別標籤顏色
const getCategoryTagColor = (category?: string) => {
  const normalized = normalizeCategory(category);
  const option = CATEGORY_OPTIONS.find(c => c.value === normalized);
  return option?.color || 'default';
};

// 取得類別標籤文字
const getCategoryTagText = (category?: string) => {
  const normalized = normalizeCategory(category);
  const option = CATEGORY_OPTIONS.find(c => c.value === normalized);
  return option?.label || category || '未分類';
};

// ---[類型定義]---
interface Project {
  id: number;
  project_name: string;
  project_code?: string;
  year?: number;
  category?: string;
  status?: string;
  client_agency?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface ProjectFormData {
  project_name: string;
  project_code?: string;
  year?: number;
  category?: string;
  status?: string;
  client_agency?: string;
  contract_amount?: number;
  start_date?: any; // 使用 any 以便處理 dayjs 物件
  end_date?: any;
  description?: string;
}

type ViewMode = 'list' | 'board';
type DataIndex = keyof Project;

// ---[主元件]---
export const ContractCasePage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  // ---[狀態管理]---
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // 篩選選項
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [availableStatuses, setAvailableStatuses] = useState<string[]>([]);

  // 模態框狀態
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [modalMode, setModalMode] = useState<'view' | 'edit' | 'create'>('create');

  // 廠商管理模態框狀態
  const [vendorManagementVisible, setVendorManagementVisible] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // 欄位搜尋狀態
  const [columnSearchText, setColumnSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  // 欄位搜尋功能
  const handleColumnSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: DataIndex,
  ) => {
    confirm();
    setColumnSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleColumnReset = (clearFilters: () => void) => {
    clearFilters();
    setColumnSearchText('');
  };

  // 取得欄位搜尋屬性
  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<Project> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`搜尋...`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            搜尋
          </Button>
          <Button
            onClick={() => clearFilters && handleColumnReset(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            重置
          </Button>
          <Button type="link" size="small" onClick={() => close()}>關閉</Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]?.toString().toLowerCase().includes((value as string).toLowerCase()) ?? false,
    filterDropdownProps: {
      onOpenChange(open) {
        if (open) setTimeout(() => searchInput.current?.select(), 100);
      },
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
          searchWords={[columnSearchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : text,
  });

  // ---[API 呼叫]---

  // 載入專案列表 (使用統一 API 服務)
  const loadProjects = async () => {
    setLoading(true);
    try {
      const response = await projectsApi.getProjects({
        page: currentPage,
        limit: pageSize,
        search: searchText || undefined,
        year: yearFilter,
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      });

      // 統一 API 回傳 { items, pagination } 格式
      setProjects(response.items || []);
      setTotal(response.pagination?.total || 0);
    } catch (error: any) {
      message.error(error.message || '載入專案列表失敗');
    } finally {
      setLoading(false);
    }
  };

  // 載入篩選選項 (使用統一 API 服務)
  const loadFilterOptions = async () => {
    try {
      const [years, categories, statuses] = await Promise.all([
        projectsApi.getYearOptions(),
        projectsApi.getCategoryOptions(),
        projectsApi.getStatusOptions(),
      ]);

      setAvailableYears(years || []);
      setAvailableCategories(categories || []);
      setAvailableStatuses(statuses || []);
    } catch (error) {
      console.error('載入篩選選項失敗:', error);
    }
  };

  // 新增或編輯專案 (使用統一 API 服務)
  const handleSubmit = async (values: ProjectFormData) => {
    try {
      const formData = {
        ...values,
        start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : undefined,
        end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : undefined,
      };

      if (editingProject) {
        await projectsApi.updateProject(editingProject.id, formData);
        message.success('專案更新成功');
      } else {
        await projectsApi.createProject(formData);
        message.success('專案建立成功');
      }

      setModalVisible(false);
      form.resetFields();
      setEditingProject(null);
      loadProjects();
      loadFilterOptions(); // 刷新篩選選項
    } catch (error: any) {
      message.error(error.message || '操作失敗');
    }
  };

  // 刪除專案 (使用統一 API 服務)
  const handleDelete = async (id: number) => {
    try {
      await projectsApi.deleteProject(id);
      message.success('專案刪除成功');
      loadProjects();
    } catch (error: any) {
      message.error(error.message || '刪除失敗');
    }
  };

  // ---[生命週期鉤子]---
  useEffect(() => {
    loadProjects();
  }, [currentPage, pageSize, searchText, yearFilter, categoryFilter, statusFilter]);

  useEffect(() => {
    loadFilterOptions();
  }, []);

  // ---[事件處理函式]---
  const handleView = (project: Project) => {
    // 導航到詳情頁面（採用 TAB 分頁模式：案件資訊、承辦同仁、協力廠商）
    navigate(ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(project.id)));
  };

  const handleEdit = (project: Project) => {
    // 直接導航到詳情頁面，使用內嵌編輯模式（不使用彈跳視窗）
    navigate(ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(project.id)));
  };

  const handleAddNew = () => {
    setEditingProject(null);
    setModalMode('create');
    form.resetFields();
    setModalVisible(true);
  };

  const handleResetFilters = () => {
    setSearchText('');
    setYearFilter(undefined);
    setCategoryFilter('');
    setStatusFilter('');
    setCurrentPage(1);
  };

  // ---[UI 輔助函式]---
  const getStatusColor = (status?: string) => {
    switch (status) {
      case '執行中':
      case '進行中': return 'processing';
      case '已結案': return 'success';
      case '暫停': return 'warning';
      case '取消': return 'error';
      default: return 'default';
    }
  };

  // ---[渲染邏輯]---

  // 列表視圖的欄位定義 - 含排序與篩選功能
  const columns: TableColumnType<Project>[] = [
    {
      title: '專案名稱',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 250,
      ellipsis: true,
      sorter: (a, b) => a.project_name.localeCompare(b.project_name, 'zh-TW'),
      ...getColumnSearchProps('project_name'),
      render: (text, record) => (
        <strong>
          {searchedColumn === 'project_name' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[columnSearchText]}
              autoEscape
              textToHighlight={text || ''}
            />
          ) : text}
        </strong>
      ),
    },
    {
      title: '年度',
      dataIndex: 'year',
      key: 'year',
      width: 80,
      align: 'center',
      sorter: (a, b) => (a.year || 0) - (b.year || 0),
      filters: availableYears.map(y => ({ text: `${y}年`, value: y })),
      onFilter: (value, record) => record.year === value,
    },
    {
      title: '案件類別',
      dataIndex: 'category',
      key: 'category',
      width: 130,
      align: 'center',
      filters: CATEGORY_OPTIONS.map(c => ({ text: c.label, value: c.value })),
      onFilter: (value, record) => normalizeCategory(record.category) === value,
      render: (category) => (
        <Tag color={getCategoryTagColor(category)}>
          {getCategoryTagText(category)}
        </Tag>
      ),
    },
    {
      title: '委託單位',
      dataIndex: 'client_agency',
      key: 'client_agency',
      width: 200,
      ellipsis: true,
      sorter: (a, b) => (a.client_agency || '').localeCompare(b.client_agency || '', 'zh-TW'),
      ...getColumnSearchProps('client_agency'),
    },
    {
      title: '案件狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      align: 'center',
      filters: availableStatuses.map(s => ({ text: s, value: s })),
      onFilter: (value, record) => record.status === value,
      render: (status) => <Tag color={getStatusColor(status)}>{status || '未設定'}</Tag>,
    },
    {
      title: '起始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      sorter: (a, b) => {
        if (!a.start_date && !b.start_date) return 0;
        if (!a.start_date) return 1;
        if (!b.start_date) return -1;
        return new Date(a.start_date).getTime() - new Date(b.start_date).getTime();
      },
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '結束日期',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      sorter: (a, b) => {
        if (!a.end_date && !b.end_date) return 0;
        if (!a.end_date) return 1;
        if (!b.end_date) return -1;
        return new Date(a.end_date).getTime() - new Date(b.end_date).getTime();
      },
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<TeamOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedProject(record);
              setVendorManagementVisible(true);
            }}
          >廠商</Button>
          <Popconfirm
            title="確定刪除此專案嗎？"
            description="此操作不可撤銷"
            onConfirm={(e) => {
              e?.stopPropagation();
              handleDelete(record.id);
            }}
            onCancel={(e) => e?.stopPropagation()}
            okText="確定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()}>刪除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 看板視圖渲染
  const renderBoardView = () => {
    if (projects.length === 0) return <Empty description="暫無數據" />;
    return (
      <Row gutter={[16, 16]}>
        {projects.map((item) => (
          <Col key={item.id} xs={24} sm={12} lg={8} xl={6}>
            <Card
              title={item.project_name}
              size="small"
              actions={[
                <EyeOutlined key="view" onClick={() => handleView(item)} />,
                <EditOutlined key="edit" onClick={() => handleEdit(item)} />,
                <TeamOutlined key="vendor" onClick={() => { setSelectedProject(item); setVendorManagementVisible(true); }} />,
                <Popconfirm
                  title="確定刪除此專案嗎？"
                  onConfirm={() => handleDelete(item.id)}
                  okText="確定"
                  cancelText="取消"
                >
                  <DeleteOutlined key="delete" />
                </Popconfirm>,
              ]}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <div><Tag color={getStatusColor(item.status)}>{item.status || '未設定'}</Tag></div>
                <p><strong>委託單位:</strong> {item.client_agency || '-'}</p>
                <p><strong>契約期程:</strong></p>
                <p>{item.start_date ? dayjs(item.start_date).format('YYYY-MM-DD') : 'N/A'} ~ {item.end_date ? dayjs(item.end_date).format('YYYY-MM-DD') : 'N/A'}</p>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  // 統計數據 (同時計算 '執行中' 和 '進行中')
  const statistics = {
    total: total,
    inProgress: projects.filter(p => p.status === '執行中' || p.status === '進行中').length,
    completed: projects.filter(p => p.status === '已結案').length,
  };

  return (
    <div style={{ padding: 24 }}>
      {/* 頁面標題和統計 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>承攬案件管理</Title></Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6} md={4}><Statistic title="總計案件" value={statistics.total} /></Col>
          <Col xs={12} sm={6} md={4}><Statistic title="進行中" value={statistics.inProgress} /></Col>
          <Col xs={12} sm={6} md={4}><Statistic title="已完成" value={statistics.completed} /></Col>
        </Row>
      </Card>

      {/* 篩選和操作區 */}
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Row gutter={[16, 8]}>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Input
                placeholder="搜尋專案名稱、編號、委託單位"
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                allowClear
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={3}>
              <Select placeholder="年度" value={yearFilter} onChange={setYearFilter} allowClear style={{ width: '100%' }}>
                {availableYears.map(year => <Option key={year} value={year}>{year}年</Option>)}
              </Select>
            </Col>
            <Col xs={12} sm={6} md={5} lg={4}>
              <Select placeholder="案件類別" value={categoryFilter} onChange={setCategoryFilter} allowClear style={{ width: '100%' }}>
                {CATEGORY_OPTIONS.map(opt => <Option key={opt.value} value={opt.value}>{opt.label}</Option>)}
              </Select>
            </Col>
            <Col xs={12} sm={6} md={4} lg={4}>
              <Select placeholder="案件狀態" value={statusFilter} onChange={setStatusFilter} allowClear style={{ width: '100%' }}>
                {availableStatuses.map(stat => <Option key={stat} value={stat}>{stat}</Option>)}
              </Select>
            </Col>
          </Row>
          <Row justify="space-between">
            <Col>
              <Space>
                <Button onClick={handleResetFilters}>重置篩選</Button>
                <Button icon={<ReloadOutlined />} onClick={loadProjects}>重新載入</Button>
              </Space>
            </Col>
            <Col>
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAddNew}>新增案件</Button>
                <Space>
                  <AppstoreOutlined />
                  <Switch checked={viewMode === 'board'} onChange={(c) => setViewMode(c ? 'board' : 'list')} />
                  <UnorderedListOutlined />
                </Space>
              </Space>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* 內容區域 */}
      <Card>
        <Spin spinning={loading}>
          {viewMode === 'list' ? (
            <Table
              columns={columns}
              dataSource={projects}
              rowKey="id"
              pagination={false}
              scroll={{ x: 1200 }}
              onRow={(record) => ({
                onClick: () => handleView(record),
                style: { cursor: 'pointer' },
              })}
            />
          ) : (
            renderBoardView()
          )}
        </Spin>
        {total > 0 && (
          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Pagination
              current={currentPage}
              pageSize={pageSize}
              total={total}
              showSizeChanger
              showQuickJumper
              showTotal={(t, r) => `第 ${r[0]}-${r[1]} 項，共 ${t} 項`}
              onChange={(page, size) => { setCurrentPage(page); setPageSize(size); }}
            />
          </div>
        )}
      </Card>

      {/* 新增/編輯/檢視模態框 */}
      <Modal
        title={
          modalMode === 'view' ? '檢視專案詳情' :
          modalMode === 'edit' ? '編輯專案' : '新增專案'
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingProject(null);
          setModalMode('create');
          form.resetFields();
        }}
        footer={null}
        width={800}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ status: '進行中' }}>
          <Form.Item name="project_name" label="專案名稱" rules={[{ required: true, message: '請輸入專案名稱' }]}>
            <Input placeholder="請輸入專案名稱" readOnly={modalMode === 'view'} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="project_code" label="專案編號"><Input placeholder="請輸入專案編號" readOnly={modalMode === 'view'} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="year" label="年度"><InputNumber placeholder="請輸入年度" min={2000} max={2050} style={{ width: '100%' }} readOnly={modalMode === 'view'} /></Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="案件類別">
                <Select placeholder="請選擇案件類別" disabled={modalMode === 'view'}>
                  {CATEGORY_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="案件狀態">
                <Select placeholder="請選擇狀態" disabled={modalMode === 'view'}>
                  {availableStatuses.map(stat => <Option key={stat} value={stat}>{stat}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="client_agency" label="委託單位"><Input placeholder="請輸入委託單位" readOnly={modalMode === 'view'} /></Form.Item>
          <Form.Item name="contract_amount" label="合約金額">
            <InputNumber placeholder="請輸入合約金額" min={0} style={{ width: '100%' }} formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={v => v!.replace(/\$\s?|(,*)/g, '')} readOnly={modalMode === 'view'} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="start_date" label="起始日期"><DatePicker style={{ width: '100%' }} disabled={modalMode === 'view'} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="結束日期"><DatePicker style={{ width: '100%' }} disabled={modalMode === 'view'} /></Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="專案描述"><Input.TextArea placeholder="請輸入專案描述" rows={3} readOnly={modalMode === 'view'} /></Form.Item>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => {
                setModalVisible(false);
                setEditingProject(null);
                setModalMode('create');
                form.resetFields();
              }}>
                {modalMode === 'view' ? '關閉' : '取消'}
              </Button>
              {modalMode !== 'view' && (
                <Button type="primary" htmlType="submit">
                  {modalMode === 'edit' ? '更新' : '建立'}
                </Button>
              )}
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 廠商關聯管理模態框 */}
      {selectedProject && (
        <ProjectVendorManagement
          projectId={selectedProject.id}
          projectName={selectedProject.project_name}
          visible={vendorManagementVisible}
          onClose={() => { setVendorManagementVisible(false); setSelectedProject(null); }}
        />
      )}
    </div>
  );
};

export default ContractCasePage;