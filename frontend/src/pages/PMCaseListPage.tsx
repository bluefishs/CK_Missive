/**
 * PM 案件管理列表頁面
 *
 * 提供 PM 專案管理列表，包含統計卡片、搜尋篩選與分頁功能。
 *
 * @version 2.0.0
 */
import React, { useState, useMemo } from 'react';
import { Typography, Input, Button, Space, Card, Statistic, Row, Col, Tag, Select, Progress, Table } from 'antd';
import { PlusOutlined, ReloadOutlined, ProjectOutlined, CheckCircleOutlined, ClockCircleOutlined, DollarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { usePMCases, usePMCaseSummary, useAuthGuard, useResponsive, useAllProjectsSummary } from '../hooks';
import { PM_CASE_STATUS_LABELS, PM_CASE_STATUS_COLORS, PM_CATEGORY_LABELS } from '../types/api';
import type { PMCase } from '../types/api';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';

const { Title } = Typography;
const { Search } = Input;

export const PMCaseListPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { isMobile } = useResponsive();

  const [searchText, setSearchText] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>(114);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    ...(searchText && { search: searchText }),
    ...(yearFilter !== undefined && { year: yearFilter }),
    ...(statusFilter && { status: statusFilter }),
    ...(categoryFilter && { category: categoryFilter }),
  }), [currentPage, searchText, yearFilter, statusFilter, categoryFilter]);

  const { data: casesData, isLoading, refetch } = usePMCases(queryParams);
  const { data: summary } = usePMCaseSummary({ year: yearFilter });
  const { data: financialData } = useAllProjectsSummary({ year: yearFilter, limit: 200 });

  // Build budget alert lookup by case_code
  const budgetMap = useMemo(() => {
    const map: Record<string, { pct?: number; alert?: string }> = {};
    for (const p of financialData?.items ?? []) {
      map[p.case_code] = { pct: p.budget_used_percentage, alert: p.budget_alert };
    }
    return map;
  }, [financialData]);

  // PaginatedResponse<PMCase> has .items and .pagination directly
  const cases = casesData?.items ?? [];
  const total = casesData?.pagination?.total ?? 0;

  const desktopColumns: ColumnsType<PMCase> = [
    {
      title: '案號',
      dataIndex: 'case_code',
      key: 'case_code',
      width: 130,
      render: (code: string) => <Typography.Text strong>{code}</Typography.Text>,
    },
    {
      title: '案名',
      dataIndex: 'case_name',
      key: 'case_name',
      ellipsis: true,
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (cat: string) => PM_CATEGORY_LABELS[cat] || cat || '-',
    },
    {
      title: '委託單位',
      dataIndex: 'client_name',
      key: 'client_name',
      width: 150,
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '合約金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      width: 130,
      align: 'right' as const,
      render: (v: number) => v ? `NT$${v.toLocaleString()}` : '-',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Tag color={PM_CASE_STATUS_COLORS[s as keyof typeof PM_CASE_STATUS_COLORS] || 'default'}>
          {PM_CASE_STATUS_LABELS[s as keyof typeof PM_CASE_STATUS_LABELS] || s}
        </Tag>
      ),
    },
    {
      title: '進度',
      dataIndex: 'progress',
      key: 'progress',
      width: 110,
      render: (p: number) => <Progress percent={p} size="small" />,
    },
    {
      title: '預算',
      key: 'budget_alert',
      width: 100,
      render: (_: unknown, record: PMCase) => {
        const info = budgetMap[record.case_code];
        if (!info || info.pct == null) return <Tag>-</Tag>;
        const color = info.alert === 'critical' ? 'red' : info.alert === 'warning' ? 'orange' : 'green';
        return <Tag color={color}>{info.pct.toFixed(0)}%</Tag>;
      },
    },
    {
      title: '開始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 110,
      render: (d: string) => d || '-',
    },
  ];

  // Mobile: strip category, client, amount, start_date columns
  const mobileColumns: ColumnsType<PMCase> = [
    desktopColumns[0]!, // 案號
    desktopColumns[1]!, // 案名
    desktopColumns[5]!, // 狀態
    desktopColumns[6]!, // 進度
  ];

  const columns = isMobile ? mobileColumns : desktopColumns;

  return (
    <ResponsiveContent>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>PM 專案管理</Title>
          </Col>
          <Col>
            {hasPermission('projects:write') && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate(ROUTES.PM_CASE_CREATE)}
              >
                新增案件
              </Button>
            )}
          </Col>
        </Row>

        {summary && (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="總案件數"
                  value={summary.total_cases}
                  prefix={<ProjectOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="執行中"
                  value={summary.by_status?.['in_progress'] ?? 0}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="已完成"
                  value={summary.by_status?.['completed'] ?? 0}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <Statistic
                  title="合約總額"
                  value={summary.total_contract_amount ?? 0}
                  prefix={<DollarOutlined />}
                  formatter={(v) => `NT$${Number(v).toLocaleString()}`}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Row gutter={[8, 8]}>
          <Col xs={24} sm={8}>
            <Search
              placeholder="搜尋案號/案名..."
              allowClear
              onSearch={(v) => {
                setSearchText(v);
                setCurrentPage(1);
              }}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="年度"
              allowClear
              value={yearFilter}
              onChange={(v) => {
                setYearFilter(v);
                setCurrentPage(1);
              }}
              options={[
                { value: 114, label: '114' },
                { value: 113, label: '113' },
                { value: 112, label: '112' },
              ]}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="狀態"
              allowClear
              value={statusFilter}
              onChange={(v) => {
                setStatusFilter(v);
                setCurrentPage(1);
              }}
              options={Object.entries(PM_CASE_STATUS_LABELS).map(([k, v]) => ({
                value: k,
                label: v,
              }))}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="類別"
              allowClear
              value={categoryFilter}
              onChange={(v) => {
                setCategoryFilter(v);
                setCurrentPage(1);
              }}
              options={Object.entries(PM_CATEGORY_LABELS).map(([k, v]) => ({
                value: k,
                label: v,
              }))}
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
          </Col>
        </Row>

        <Table<PMCase>
          dataSource={cases}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: setCurrentPage,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 筆`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/pm/cases/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: 800 }}
        />
      </Space>
    </ResponsiveContent>
  );
};

export default PMCaseListPage;
