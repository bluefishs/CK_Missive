import React, { useState, useRef, useMemo } from 'react';
import type { InputRef, TableColumnType } from 'antd';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import { ResponsiveContent } from '../components/common';
import {
  Card,
  Button,
  Space,
  Input,
  Select,
  Row,
  Col,
  Tag,
  Statistic,
  Switch,
  Pagination,
  Typography,
  Empty,
  Spin,
  App,
} from 'antd';
import {
  PlusOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import { ResponsiveTable } from '../components/common';
import ProjectVendorManagement from '../components/project/ProjectVendorManagement';
import { useProjectsPage } from '../hooks';
import { useAuthGuard, useResponsive } from '../hooks';
import { STATUS_OPTIONS } from './contractCase/tabs/constants';

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
import type { Project, ProjectStatus } from '../types/api';

type ViewMode = 'list' | 'board';
type DataIndex = keyof Project;

// ---[主元件]---
export const ContractCasePage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();

  // 📱 響應式設計
  const { isMobile } = useResponsive();

  // 🔒 權限控制 Hook
  const { hasPermission } = useAuthGuard();
  const canCreate = hasPermission('projects:write');
  const canEdit = hasPermission('projects:write');
  const canDelete = hasPermission('projects:delete');

  // ---[UI 狀態管理]---
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // 廠商管理模態框狀態
  const [vendorManagementVisible, setVendorManagementVisible] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // 欄位搜尋狀態
  const [columnSearchText, setColumnSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  // ---[React Query Hook]---
  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    ...(searchText && { search: searchText }),
    ...(yearFilter && { year: yearFilter }),
    ...(categoryFilter && { category: categoryFilter }),
    ...(statusFilter && { status: statusFilter }),
  }), [currentPage, pageSize, searchText, yearFilter, categoryFilter, statusFilter]);

  const {
    projects,
    pagination,
    isLoading,
    statistics,
    availableYears,
    availableStatuses,
    refetch,
    deleteProject,
    isDeleting,
  } = useProjectsPage(queryParams);

  const total = pagination?.total ?? 0;

  // 全域統計數據
  const globalStats = useMemo(() => {
    if (!statistics) return { total: 0, inProgress: 0, completed: 0 };
    const inProgressCount = statistics.status_breakdown?.find(s => s.status === '執行中')?.count || 0;
    const completedCount = statistics.status_breakdown?.find(s => s.status === '已結案')?.count || 0;
    return {
      total: statistics.total_projects || 0,
      inProgress: inProgressCount,
      completed: completedCount,
    };
  }, [statistics]);

  // 欄位搜尋功能
  const handleColumnSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: DataIndex,
  ) => {
    confirm();
    setColumnSearchText(selectedKeys[0] ?? '');
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

  // ---[事件處理]---

  // 刪除專案
  const handleDelete = async (id: number) => {
    try {
      await deleteProject(id);
      message.success('專案刪除成功');
    } catch (error: unknown) {
      message.error(error instanceof Error ? error.message : '刪除失敗');
    }
  };

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
    // 導航至新增案件頁面
    navigate(ROUTES.CONTRACT_CASE_CREATE);
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
      case '執行中': return 'processing';
      case '已結案': return 'success';
      case '未得標': return 'error';
      case '暫停': return 'error';  // 舊資料相容
      default: return 'default';
    }
  };

  // 取得狀態顯示標籤（暫停 → 未得標）
  const getStatusLabel = (status?: string) => {
    if (!status) return '未設定';
    const option = STATUS_OPTIONS.find(opt => opt.value === status);
    return option?.label || status;
  };

  // ---[渲染邏輯]---

  // 列表視圖的欄位定義 - 欄位順序: 專案編號、年度、專案名稱、委託單位、案件類別、案件狀態、契約期程
  // 欄位寬度已優化 (2026-01-12)
  const columns: TableColumnType<Project>[] = [
    {
      title: '專案編號',
      dataIndex: 'project_code',
      key: 'project_code',
      width: 100,
      sorter: (a, b) => (a.project_code || '').localeCompare(b.project_code || ''),
      ...getColumnSearchProps('project_code'),
      render: (text) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {searchedColumn === 'project_code' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[columnSearchText]}
              autoEscape
              textToHighlight={text || '-'}
            />
          ) : (text || '-')}
        </span>
      ),
    },
    {
      title: '案件年度',
      dataIndex: 'year',
      key: 'year',
      width: 80,
      align: 'center',
      sorter: (a, b) => (a.year || 0) - (b.year || 0),
      defaultSortOrder: 'descend',
      filters: availableYears.map(y => ({ text: `${y}年`, value: y })),
      onFilter: (value, record) => record.year === value,
    },
    {
      title: '專案名稱',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 260,
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
      title: '委託單位',
      dataIndex: 'client_agency',
      key: 'client_agency',
      width: 160,
      ellipsis: true,
      sorter: (a, b) => (a.client_agency || '').localeCompare(b.client_agency || '', 'zh-TW'),
      ...getColumnSearchProps('client_agency'),
    },
    {
      title: '案件類別',
      dataIndex: 'category',
      key: 'category',
      width: 90,
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
      title: '案件狀態',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      align: 'center',
      filters: availableStatuses.map(s => ({ text: getStatusLabel(s), value: s })),
      onFilter: (value, record) => record.status === value,
      render: (status) => <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>,
    },
    {
      title: '契約期程',
      key: 'contract_period',
      width: 120,
      render: (_, record) => {
        const startDate = record.start_date ? dayjs(record.start_date).format('YYYY/MM/DD') : '';
        const endDate = record.end_date ? dayjs(record.end_date).format('YYYY/MM/DD') : '';
        if (!startDate && !endDate) return '-';
        return `${startDate || '未定'}~${endDate || '未定'}`;
      },
    },
    // 操作欄位已簡化 - 編輯與廠商管理已移至詳情頁 TAB 分頁 (2026-01-12)
    // 點擊行可直接進入詳情頁進行完整操作
    // {
    //   title: '操作',
    //   key: 'actions',
    //   width: 150,
    //   fixed: 'right',
    //   render: (_, record) => (
    //     <Space>
    //       {/* 編輯按鈕 - 需要 projects:write 權限 */}
    //       {canEdit && (
    //         <Button
    //           type="link"
    //           size="small"
    //           icon={<EditOutlined />}
    //           onClick={(e) => {
    //             e.stopPropagation();
    //             handleEdit(record);
    //           }}
    //         >編輯</Button>
    //       )}
    //       {/* 廠商管理按鈕 - 所有人可見 */}
    //       <Button
    //         type="link"
    //         size="small"
    //         icon={<TeamOutlined />}
    //         onClick={(e) => {
    //           e.stopPropagation();
    //           setSelectedProject(record);
    //           setVendorManagementVisible(true);
    //         }}
    //       >廠商</Button>
    //       {/* 刪除按鈕 - 需要 projects:delete 權限 */}
    //       {canDelete && (
    //         <Popconfirm
    //           title="確定刪除此專案嗎？"
    //           description="此操作不可撤銷"
    //           onConfirm={(e) => {
    //             e?.stopPropagation();
    //             handleDelete(record.id);
    //           }}
    //           onCancel={(e) => e?.stopPropagation()}
    //           okText="確定"
    //           cancelText="取消"
    //         >
    //           <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()}>刪除</Button>
    //         </Popconfirm>
    //       )}
    //     </Space>
    //   ),
    // },
  ];

  // 看板視圖渲染
  const renderBoardView = () => {
    if (projects.length === 0) return <Empty description="暫無數據" />;

    // 操作按鈕已簡化 - 點擊卡片直接進入詳情頁 (2026-01-12)
    const getCardActions = (item: Project) => {
      // 只保留檢視按鈕，編輯與廠商管理已移至詳情頁 TAB 分頁
      const actions = [
        <EyeOutlined key="view" onClick={() => handleView(item)} />,
      ];
      return actions;
    };

    return (
      <Row gutter={[16, 16]}>
        {projects.map((item) => (
          <Col key={item.id} xs={24} sm={12} lg={8} xl={6}>
            <Card
              title={item.project_name}
              size="small"
              actions={getCardActions(item)}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Tag color={getStatusColor(item.status)}>{getStatusLabel(item.status)}</Tag>
                  {item.year && <Tag>{item.year}年</Tag>}
                </div>
                <p><strong>委託單位:</strong> {item.client_agency || '-'}</p>
                <p><strong>契約期程:</strong> {
                  item.start_date || item.end_date
                    ? `${item.start_date ? dayjs(item.start_date).format('YYYY/MM/DD') : '未定'}~${item.end_date ? dayjs(item.end_date).format('YYYY/MM/DD') : '未定'}`
                    : '-'
                }</p>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* 頁面標題和統計 - 使用全域統計數據（從後端 API 取得） */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>承攬案件管理</Title></Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6} md={4}><Statistic title="總計案件" value={globalStats.total} /></Col>
          <Col xs={12} sm={6} md={4}><Statistic title="執行中" value={globalStats.inProgress} /></Col>
          <Col xs={12} sm={6} md={4}><Statistic title="已結案" value={globalStats.completed} /></Col>
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
                {availableStatuses.map(stat => <Option key={stat} value={stat}>{getStatusLabel(stat)}</Option>)}
              </Select>
            </Col>
          </Row>
          <Row justify="space-between">
            <Col>
              <Space>
                <Button onClick={handleResetFilters}>重置篩選</Button>
                <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新載入</Button>
              </Space>
            </Col>
            <Col>
              <Space>
                {/* 🔒 新增按鈕 - 需要 projects:write 權限 */}
                {canCreate && (
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleAddNew}>新增案件</Button>
                )}
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
        <Spin spinning={isLoading || isDeleting}>
          {viewMode === 'list' ? (
            <ResponsiveTable
              columns={columns}
              dataSource={projects}
              rowKey="id"
              pagination={false}
              scroll={{ x: isMobile ? 600 : 890 }}
              mobileHiddenColumns={['category', 'contract_period']}
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

      {/* 廠商關聯管理模態框 */}
      {selectedProject && (
        <ProjectVendorManagement
          projectId={selectedProject.id}
          projectName={selectedProject.project_name}
          visible={vendorManagementVisible}
          onClose={() => { setVendorManagementVisible(false); setSelectedProject(null); }}
        />
      )}
    </ResponsiveContent>
  );
};

export default ContractCasePage;