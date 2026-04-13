import React, { useState, useMemo } from 'react';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card,
  Button,
  Space,
  Input,
  Select,
  Row,
  Col,
  Tag,
  Switch,
  Pagination,
  Typography,
  Empty,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  TeamOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import { ResponsiveTable, ClickableStatCard } from '../components/common';
import ProjectVendorManagement from '../components/project/ProjectVendorManagement';
import { useProjectsPage } from '../hooks';
import { useAuthGuard, useResponsive } from '../hooks';
import { useContractCaseColumns } from './contractCase/useContractCaseColumns';
import { getStatusColor, getStatusLabel } from './contractCase/contractCaseConstants';

const { Title } = Typography;
const { Option } = Select;

// ---[類型定義]---
import type { Project, ViewMode } from '../types/api';

// ---[主元件]---
export const ContractCasePage: React.FC = () => {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  const { hasPermission } = useAuthGuard();
  const canCreate = hasPermission('projects:write');

  // ---[UI 狀態管理]---
  const [statFilter, setStatFilter] = useState<string | null>(null);
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

  // ---[React Query Hook]---
  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    sort_by: 'year',
    sort_order: 'desc' as const,
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

  // 表格欄位 (extracted hook)
  const { columns } = useContractCaseColumns(availableYears, availableStatuses);

  // ---[事件處理]---
  const handleView = (project: Project) => {
    navigate(ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(project.id)));
  };

  const handleAddNew = () => {
    navigate(ROUTES.CONTRACT_CASE_CREATE);
  };

  const handleResetFilters = () => {
    setSearchText('');
    setYearFilter(undefined);
    setCategoryFilter('');
    setStatusFilter('');
    setCurrentPage(1);
  };

  // 看板視圖渲染
  const renderBoardView = () => {
    if (projects.length === 0) return <Empty description="暫無數據" />;

    const getCardActions = (item: Project) => {
      return [
        <EyeOutlined key="view" onClick={() => handleView(item)} />,
      ];
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
              <Space vertical style={{ width: '100%' }}>
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
      {/* 頁面標題和統計 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>承攬案件管理</Title></Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="總計案件"
              value={globalStats.total}
              icon={<TeamOutlined />}
              active={statFilter === 'all'}
              onClick={() => setStatFilter(statFilter === 'all' ? null : 'all')}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="執行中"
              value={globalStats.inProgress}
              icon={<SyncOutlined />}
              color="#1890ff"
              active={statFilter === 'inProgress'}
              onClick={() => setStatFilter(statFilter === 'inProgress' ? null : 'inProgress')}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="已結案"
              value={globalStats.completed}
              icon={<CheckCircleOutlined />}
              color="#52c41a"
              active={statFilter === 'completed'}
              onClick={() => setStatFilter(statFilter === 'completed' ? null : 'completed')}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="合約總額"
              value={`NT$${projects.reduce((sum, p) => sum + (p.contract_amount ?? 0), 0).toLocaleString()}`}
              icon={<DollarOutlined />}
              active={statFilter === 'amount'}
              onClick={() => setStatFilter(statFilter === 'amount' ? null : 'amount')}
            />
          </Col>
        </Row>
      </Card>

      {/* 篩選和操作區 */}
      <Card style={{ marginBottom: 16 }}>
        <Space vertical style={{ width: '100%' }}>
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
              <Select placeholder="計畫類別" value={categoryFilter} onChange={setCategoryFilter} allowClear style={{ width: '100%' }}>
                {[
                  { value: '01', label: '01委辦招標' },
                  { value: '02', label: '02承攬報價' },
                ].map(opt => <Option key={opt.value} value={opt.value}>{opt.label}</Option>)}
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
          open={vendorManagementVisible}
          onClose={() => { setVendorManagementVisible(false); setSelectedProject(null); }}
        />
      )}
    </ResponsiveContent>
  );
};

export default ContractCasePage;
