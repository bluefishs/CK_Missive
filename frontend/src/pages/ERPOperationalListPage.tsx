/**
 * ERP 營運帳目列表頁面
 *
 * 功能：統計卡片 + 篩選 + 帳目表格 + 導航至詳情/新增
 */
import React, { useState, useMemo } from 'react';
import {
  Alert, Card, Table, Button, Space, Tag, Input, Select, Typography,
  Statistic, Row, Col, Progress,
} from 'antd';
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import {
  useOperationalAccounts,
  useOperationalAccountStats,
  useAuthGuard,
} from '../hooks';
import {
  OPERATIONAL_CATEGORIES,
  OPERATIONAL_STATUS,
} from '../types/erp';
import type { OperationalAccount } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const CATEGORY_OPTIONS = Object.entries(OPERATIONAL_CATEGORIES).map(
  ([value, label]) => ({ value, label })
);

const STATUS_OPTIONS = Object.entries(OPERATIONAL_STATUS).map(
  ([value, label]) => ({ value, label })
);

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  closed: 'default',
  frozen: 'blue',
};

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => {
  const y = currentYear - i;
  return { value: y, label: String(y) };
});

interface ListParams {
  skip: number;
  limit: number;
  category?: string;
  fiscal_year?: number;
  status?: string;
  keyword?: string;
}

const ERPOperationalListPage: React.FC = () => {
  const navigate = useNavigate();
  const [params, setParams] = useState<ListParams>({ skip: 0, limit: 20 });

  const { hasPermission } = useAuthGuard();
  const canWrite = hasPermission('operational:write');

  const { data, isLoading, isError, refetch } = useOperationalAccounts(params);
  const { data: stats } = useOperationalAccountStats();

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;

  const usageRate =
    stats && stats.total_budget > 0
      ? Math.round((stats.total_spent / stats.total_budget) * 100)
      : 0;

  const columns: ColumnsType<OperationalAccount> = [
    {
      title: '帳目編號',
      dataIndex: 'account_code',
      key: 'account_code',
      width: 140,
    },
    {
      title: '名稱',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      width: 110,
      render: (val: string) => (
        <Tag>{OPERATIONAL_CATEGORIES[val] ?? val}</Tag>
      ),
    },
    {
      title: '年度',
      dataIndex: 'fiscal_year',
      key: 'fiscal_year',
      width: 80,
      align: 'center',
    },
    {
      title: '預算',
      dataIndex: 'budget_limit',
      key: 'budget_limit',
      width: 130,
      align: 'right',
      render: (val?: number) => val != null ? `NT$ ${val.toLocaleString()}` : '-',
    },
    {
      title: '已支出',
      dataIndex: 'total_spent',
      key: 'total_spent',
      width: 130,
      align: 'right',
      render: (val?: number) => val != null ? `NT$ ${val.toLocaleString()}` : '-',
    },
    {
      title: '使用率',
      key: 'usage',
      width: 140,
      render: (_: unknown, record: OperationalAccount) => {
        const spent = record.total_spent ?? 0;
        const budget = record.budget_limit;
        const pct = budget > 0 ? Math.round((spent / budget) * 100) : 0;
        return (
          <Progress
            percent={pct}
            size="small"
            status={pct > 90 ? 'exception' : pct > 70 ? 'active' : 'normal'}
          />
        );
      },
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] ?? 'default'}>
          {OPERATIONAL_STATUS[status] ?? status}
        </Tag>
      ),
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* Header + Stats */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={3} style={{ margin: 0 }}>營運帳目</Title>
          </Col>
          <Col>
            {canWrite && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate(ROUTES.ERP_OPERATIONAL_CREATE)}
              >
                新增帳目
              </Button>
            )}
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}>
            <Statistic title="帳目數" value={stats?.total_accounts ?? 0} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="總預算"
              value={stats?.total_budget ?? 0}
              precision={0}
              prefix="NT$"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="總支出"
              value={stats?.total_spent ?? 0}
              precision={0}
              prefix="NT$"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="使用率"
              value={usageRate}
              suffix="%"
              styles={{ content: { color: usageRate > 90 ? '#ff4d4f' : usageRate > 70 ? '#fa8c16' : '#52c41a' } }}
            />
          </Col>
        </Row>
      </Card>

      {/* Filters + Table */}
      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜尋帳目編號或名稱..."
            allowClear
            style={{ width: 220 }}
            onChange={(e) => {
              const val = e.target.value.trim() || undefined;
              setParams((p) => ({ ...p, keyword: val, skip: 0 }));
            }}
          />
          <Select
            placeholder="類別"
            allowClear
            style={{ width: 130 }}
            options={CATEGORY_OPTIONS}
            onChange={(v) => setParams((p) => ({ ...p, category: v, skip: 0 }))}
          />
          <Select
            placeholder="年度"
            allowClear
            style={{ width: 100 }}
            options={YEAR_OPTIONS}
            onChange={(v) => setParams((p) => ({ ...p, fiscal_year: v, skip: 0 }))}
          />
          <Select
            placeholder="狀態"
            allowClear
            style={{ width: 100 }}
            options={STATUS_OPTIONS}
            onChange={(v) => setParams((p) => ({ ...p, status: v, skip: 0 }))}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            重新整理
          </Button>
        </Space>

        {isError && (
          <Alert
            type="error"
            message="營運帳目載入失敗，請稍後重試"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Table<OperationalAccount>
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor((params.skip ?? 0) / (params.limit ?? 20)) + 1,
            pageSize: params.limit ?? 20,
            total,
            onChange: (page, pageSize) =>
              setParams((p) => ({ ...p, skip: (page - 1) * pageSize, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`${ROUTES.ERP_OPERATIONAL}/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1000 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPOperationalListPage;
