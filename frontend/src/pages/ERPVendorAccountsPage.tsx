/**
 * ERP 協力廠商帳款總覽頁面
 *
 * 功能：列出所有協力廠商及其跨案件應付彙總
 * - 年度篩選 + 關鍵字搜尋
 * - 總應付 / 總已付 / 總未付 統計
 * - 點擊廠商列進入明細頁
 *
 * @version 1.0.0
 */
import React, { useState, useMemo } from 'react';
import {
  Alert, Card, Typography, Row, Col, Tag, Select, Space, Input,
} from 'antd';
import { DollarOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ClickableStatCard } from '../components/common';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { useVendorAccountSummary } from '../hooks';
import type { VendorAccountSummaryItem } from '../types/erp';
import { EnhancedTable } from '../components/common/EnhancedTable';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const currentYear = new Date().getFullYear() - 1911;
const yearOptions = Array.from({ length: 5 }, (_, i) => ({
  value: currentYear - i,
  label: `${currentYear - i} 年`,
}));

const ERPVendorAccountsPage: React.FC = () => {
  const navigate = useNavigate();
  const [year, setYear] = useState<number | undefined>();
  const [keyword, setKeyword] = useState('');
  const [statFilter, setStatFilter] = useState<string | null>(null);

  const { data, isLoading, isError } = useVendorAccountSummary({
    vendor_type: 'subcontractor',
    year,
    keyword: keyword || undefined,
  });

  const items: VendorAccountSummaryItem[] = useMemo(
    () => data?.items ?? [],
    [data?.items],
  );

  // Top-level stats
  const stats = useMemo(() => {
    let totalPayable = 0;
    let totalPaid = 0;
    let totalOutstanding = 0;
    for (const item of items) {
      totalPayable += Number(item.total_payable ?? 0);
      totalPaid += Number(item.total_paid ?? 0);
      totalOutstanding += Number(item.outstanding ?? 0);
    }
    return { totalPayable, totalPaid, totalOutstanding };
  }, [items]);

  const filteredItems = useMemo(() => {
    if (!statFilter) return items;
    if (statFilter === 'paid') return items.filter(i => Number(i.total_paid ?? 0) > 0);
    if (statFilter === 'outstanding') return items.filter(i => Number(i.outstanding ?? 0) > 0);
    return items;
  }, [items, statFilter]);

  const columns: ColumnsType<VendorAccountSummaryItem> = [
    {
      title: '廠商名稱',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      ellipsis: true,
    },
    {
      title: '廠商代碼',
      dataIndex: 'vendor_code',
      key: 'vendor_code',
      width: 140,
    },
    {
      title: '合作案件數',
      dataIndex: 'case_count',
      key: 'case_count',
      width: 110,
      align: 'center',
      sorter: (a, b) => (a.case_count ?? 0) - (b.case_count ?? 0),
    },
    {
      title: '應付總額',
      dataIndex: 'total_payable',
      key: 'total_payable',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_payable ?? 0) - Number(b.total_payable ?? 0),
      render: (v: number) => Number(v).toLocaleString(),
    },
    {
      title: '已付總額',
      dataIndex: 'total_paid',
      key: 'total_paid',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_paid ?? 0) - Number(b.total_paid ?? 0),
      render: (v: number) => (
        <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span>
      ),
    },
    {
      title: '未付餘額',
      dataIndex: 'outstanding',
      key: 'outstanding',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.outstanding ?? 0) - Number(b.outstanding ?? 0),
      render: (v: number) => {
        const num = Number(v);
        return (
          <Tag color={num > 0 ? 'red' : 'green'} style={{ margin: 0 }}>
            {num.toLocaleString()}
          </Tag>
        );
      },
    },
    {
      title: '付款率',
      key: 'payment_rate',
      width: 100,
      align: 'center',
      sorter: (a, b) => {
        const rateA = Number(a.total_payable) > 0 ? Number(a.total_paid) / Number(a.total_payable) * 100 : 0;
        const rateB = Number(b.total_payable) > 0 ? Number(b.total_paid) / Number(b.total_payable) * 100 : 0;
        return rateA - rateB;
      },
      render: (_: unknown, record: VendorAccountSummaryItem) => {
        const pct = Number(record.total_payable) > 0
          ? Number(record.total_paid) / Number(record.total_payable) * 100
          : 0;
        const color = pct >= 100 ? '#52c41a' : pct >= 50 ? '#faad14' : '#ff4d4f';
        return <span style={{ color, fontWeight: 600 }}>{pct.toFixed(1)}%</span>;
      },
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card
        title={<Title level={3} style={{ margin: 0 }}>協力廠商帳款總覽</Title>}
        extra={
          <Space>
            <Input.Search
              placeholder="搜尋廠商名稱 / 代碼"
              allowClear
              style={{ width: 220 }}
              onSearch={(v) => setKeyword(v.trim())}
            />
            <Select
              placeholder="年度"
              allowClear
              style={{ width: 120 }}
              options={yearOptions}
              onChange={(v) => setYear(v)}
            />
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <ClickableStatCard
              title="總應付"
              value={stats.totalPayable.toLocaleString()}
              icon={<DollarOutlined />}
              color="#1890ff"
              active={statFilter === 'all'}
              onClick={() => setStatFilter(statFilter === 'all' ? null : 'all')}
            />
          </Col>
          <Col xs={24} sm={8}>
            <ClickableStatCard
              title="總已付"
              value={stats.totalPaid.toLocaleString()}
              icon={<CheckCircleOutlined />}
              color="#3f8600"
              active={statFilter === 'paid'}
              onClick={() => setStatFilter(statFilter === 'paid' ? null : 'paid')}
            />
          </Col>
          <Col xs={24} sm={8}>
            <ClickableStatCard
              title="總未付"
              value={stats.totalOutstanding.toLocaleString()}
              icon={<ExclamationCircleOutlined />}
              color={stats.totalOutstanding > 0 ? '#cf1322' : '#3f8600'}
              active={statFilter === 'outstanding'}
              onClick={() => setStatFilter(statFilter === 'outstanding' ? null : 'outstanding')}
            />
          </Col>
        </Row>
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <EnhancedTable<VendorAccountSummaryItem>
          columns={columns}
          dataSource={filteredItems}
          rowKey="vendor_id"
          loading={isLoading}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 廠商` }}
          size="middle"
          scroll={{ x: 900 }}
          onRow={(record) => ({
            onClick: () => navigate(`${ROUTES.ERP_VENDOR_ACCOUNTS}/${record.vendor_id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPVendorAccountsPage;
