import React, { useState, useMemo } from 'react';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card,
  Button,
  Space,
  Input,
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

const { Title, Text } = Typography;

// ---[類型定義]---
import type { Project, ViewMode } from '../types/api';

// ---[主元件]---
export const ContractCasePage: React.FC = () => {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  const { hasPermission } = useAuthGuard();
  // 2026-08-27：原本檢查 `projects:write` —— 那個名字**不存在於任何地方**
  //   （後端 _BUSINESS_PERMISSIONS 沒有、前端 PERMISSION_CATEGORIES 沒有、
  //     沒有任何角色擁有）⇒ 權限編輯畫面不會列出它，任何人都無法授予
  //   ⇒ 這個按鈕只有 superuser 看得到（hasPermission 只對 superuser 短路）。
  //
  //   而**後端要的是 `projects:create`**（`projects/crud.py:134`
  //   `require_permission("projects:create")`，admin 角色擁有它）
  //   ⇒ admin 直接打 API 建得了案件，卻看不到按鈕。
  //
  //   這不是產品決策，是前後端對不上：前端檢查的權限與端點要求的不是同一個。
  //   對齊到端點實際要求的那一個。
  //
  //   ⚠️ `projects:write` 的另一個使用點在 `ERPExpenseDetailPage`（費用核銷審核），
  //      那一塊 owner 指示「最後在處理」，本次不動 —— 它的正解可能是
  //      新開 `expenses:approve` 而不是沿用 projects 家族（語意上那不是專案寫入）。
  const canCreate = hasPermission('projects:create');

  // ---[UI 狀態管理]---
  const [statFilter, setStatFilter] = useState<string | null>(null);
  // 表頭搜尋框最後用在哪一欄（只影響漏斗勾選顯示與高亮；查詢一律走 search 參數）
  const [searchColumn, setSearchColumn] = useState<string | undefined>(undefined);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  // 2026-09-02：§2.6 ③ 預設當年度（西元），可切「全部」；此前預設空＝歷年混算
  const currentYear = new Date().getFullYear();
  const [yearFilter, setYearFilter] = useState<number | undefined>(currentYear);
  // 2026-09-02 owner：「以 01 委辦招標類別為主排列」＋「表格無排序」。
  // 後端 sort_by 接受逗號分隔多欄；類別永遠是第一鍵，使用者點的欄位接在後面。
  const [userSort, setUserSort] = useState<{ field: string; order: 'asc' | 'desc' } | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // 廠商管理模態框狀態
  const [vendorManagementVisible, setVendorManagementVisible] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // ---[React Query Hook]---
  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    sort_by: userSort && userSort.field !== 'category'
      ? `category:asc,${userSort.field}:${userSort.order}`
      : `category:${userSort?.order ?? 'asc'},year:desc`,
    sort_order: 'desc' as const,
    ...(searchText && { search: searchText }),
    ...(yearFilter && { year: yearFilter }),
    ...(categoryFilter && { category: categoryFilter }),
    ...(statusFilter && { status: statusFilter }),
  }), [currentPage, pageSize, searchText, yearFilter, categoryFilter, statusFilter, userSort]);

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
  const { columns } = useContractCaseColumns(availableYears, availableStatuses, {
    year: yearFilter, category: categoryFilter, status: statusFilter, search: searchText, searchColumn,
  });

  // ---[事件處理]---
  const handleView = (project: Project) => {
    navigate(ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(project.id)));
  };

  const handleAddNew = () => {
    navigate(ROUTES.CONTRACT_CASE_CREATE);
  };

  const handleResetFilters = () => {
    setSearchText('');
    setYearFilter(currentYear);
    setUserSort(null);
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
              onClick={() => { setStatFilter(statFilter === 'all' ? null : 'all'); setStatusFilter(''); setCurrentPage(1); }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="執行中"
              value={globalStats.inProgress}
              icon={<SyncOutlined />}
              color="#1890ff"
              active={statFilter === 'inProgress'}
              onClick={() => { const on = statFilter !== 'inProgress'; setStatFilter(on ? 'inProgress' : null); setStatusFilter(on ? '執行中' : ''); setCurrentPage(1); }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="已結案"
              value={globalStats.completed}
              icon={<CheckCircleOutlined />}
              color="#52c41a"
              active={statFilter === 'completed'}
              onClick={() => { const on = statFilter !== 'completed'; setStatFilter(on ? 'completed' : null); setStatusFilter(on ? '已結案' : ''); setCurrentPage(1); }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <ClickableStatCard
              title="合約總額"
              // 2026-09-02：§2.6 ① 卡片是分頁前的全量——此前 reduce 只加當頁 10 筆
              value={`NT$${(statistics?.total_contract_amount ?? 0).toLocaleString()}`}
              icon={<DollarOutlined />}
              active={statFilter === 'amount'}
              onClick={() => { const on = statFilter !== 'amount'; setStatFilter(on ? 'amount' : null); setUserSort(on ? { field: 'contract_amount', order: 'desc' } : null); setCurrentPage(1); }}
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
            <Col xs={24} sm={12} md={16} lg={18}>
              {/* 2026-09-04 owner：篩選走表頭漏斗（年度／類別／狀態）與欄位搜尋框，排序點欄名——
                  不再另建三個下拉（同一件事兩套機制，08-31 那套壞在前端只篩本頁）。這一行只顯示現值。 */}
              <Space wrap size={[4, 4]}>
                <Text type="secondary">目前：</Text>
                <Tag color={yearFilter ? 'blue' : 'default'}>{yearFilter ? `${yearFilter} 年度` : '全部年度'}</Tag>
                <Tag color={categoryFilter ? 'blue' : 'default'}>{categoryFilter ? `${categoryFilter} 類` : '全部類別'}</Tag>
                <Tag color={statusFilter ? 'blue' : 'default'}>{statusFilter ? getStatusLabel(statusFilter) : '全部狀態'}</Tag>
                <Text type="secondary">— 用表頭漏斗改，點欄名排序</Text>
              </Space>
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
              // 分頁器在表格外面（下方獨立的 <Pagination>），元件自己看不出來，
              // 所以這裡要明講：前端排序／篩選只會作用於當前這一頁（2026-08-31）。
              serverPaged
              pagination={false}
              onChange={(_p, filters, sorter) => {
                const s = Array.isArray(sorter) ? sorter[0] : sorter;
                const field = typeof s?.field === 'string' ? s.field : undefined;
                setUserSort(field && s?.order ? { field, order: s.order === 'ascend' ? 'asc' : 'desc' } : null);
                // 2026-09-04：表頭漏斗／搜尋框的勾選值 ⇒ 查詢參數（後端篩全庫）。
                // 這裡是唯一的篩選入口；工具列的三個下拉已撤（owner：表格能篩就不要重複做一套）。
                const first = (k: string) => {
                  const v = filters?.[k];
                  return Array.isArray(v) && v.length ? v[0] : undefined;
                };
                setYearFilter(first('year') as number | undefined);
                setCategoryFilter((first('category') as string | undefined) ?? '');
                setStatusFilter((first('status') as string | undefined) ?? '');
                const searchCol = ['project_code', 'project_name', 'client_agency'].find((k) => first(k) !== undefined);
                if (searchCol) {
                  setSearchText(String(first(searchCol)));
                  setSearchColumn(searchCol);
                } else if (searchColumn) {
                  // 使用者從搜尋框按「重置」：只清掉由表頭輸入的那份
                  setSearchText('');
                  setSearchColumn(undefined);
                }
                setCurrentPage(1);
              }}
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
