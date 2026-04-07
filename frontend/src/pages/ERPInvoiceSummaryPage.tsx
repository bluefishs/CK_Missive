/**
 * ERP 發票跨案件總覽頁面
 *
 * 功能：跨案件發票彙總 + 銷項/進項篩選 + 年度篩選
 */
import React, { useState, useMemo } from 'react';
import {
  Card, Table, Tag, Select, Typography, Row, Col, Space, Alert,
} from 'antd';
import {
  ArrowUpOutlined, ArrowDownOutlined, SwapOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { ClickableStatCard } from '../components/common';
import { useNavigate } from 'react-router-dom';
import { useInvoiceSummary } from '../hooks';
import type { InvoiceSummaryItem, InvoiceSummaryRequest } from '../types/erp';
import { ERP_INVOICE_TYPE_LABELS } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';

const { Title } = Typography;

/** 產生民國年選項 (近 5 年) */
const generateYearOptions = () => {
  const currentRocYear = new Date().getFullYear() - 1911;
  return Array.from({ length: 5 }, (_, i) => {
    const y = currentRocYear - i;
    return { value: y, label: `${y} 年` };
  });
};

const YEAR_OPTIONS = generateYearOptions();

const INVOICE_TYPE_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'sales', label: '銷項' },
  { value: 'purchase', label: '進項' },
];

const INVOICE_STATUS_COLORS: Record<string, string> = {
  issued: 'green',
  voided: 'red',
  cancelled: 'default',
};

const INVOICE_STATUS_LABELS: Record<string, string> = {
  issued: '已開立',
  voided: '已作廢',
  cancelled: '已取消',
};

const ERPInvoiceSummaryPage: React.FC = () => {
  const navigate = useNavigate();
  const [params, setParams] = useState<InvoiceSummaryRequest>({ skip: 0, limit: 20 });
  const [statFilter, setStatFilter] = useState<string | null>(null);
  const { data, isLoading, isError } = useInvoiceSummary(params);

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;

  // 統計
  const salesTotal = useMemo(
    () => items.filter(i => i.invoice_type === 'sales').reduce((s, i) => s + (i.amount || 0), 0),
    [items],
  );
  const purchaseTotal = useMemo(
    () => items.filter(i => i.invoice_type === 'purchase').reduce((s, i) => s + (i.amount || 0), 0),
    [items],
  );
  const netAmount = salesTotal - purchaseTotal;

  const columns: ColumnsType<InvoiceSummaryItem> = [
    { title: '發票號碼', dataIndex: 'invoice_number', key: 'invoice_number', width: 140 },
    { title: '開立日期', dataIndex: 'invoice_date', key: 'invoice_date', width: 120 },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
      render: (v: number) => v?.toLocaleString() ?? '-',
    },
    {
      title: '稅額', dataIndex: 'tax_amount', key: 'tax_amount', width: 110, align: 'right',
      render: (v: number) => v?.toLocaleString() ?? '-',
    },
    {
      title: '類型', dataIndex: 'invoice_type', key: 'invoice_type', width: 80,
      render: (v: string) => {
        const label = ERP_INVOICE_TYPE_LABELS[v as keyof typeof ERP_INVOICE_TYPE_LABELS] ?? v;
        return <Tag color={v === 'sales' ? 'blue' : 'orange'}>{label}</Tag>;
      },
    },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => (
        <Tag color={INVOICE_STATUS_COLORS[v] ?? 'default'}>
          {INVOICE_STATUS_LABELS[v] ?? v}
        </Tag>
      ),
    },
    {
      title: '案件代碼', key: 'project_code', width: 160,
      render: (_: unknown, record: InvoiceSummaryItem) => {
        const code = record.project_code || record.case_code;
        return record.erp_quotation_id ? (
          <a
            onClick={(e) => {
              e.stopPropagation();
              navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.erp_quotation_id)));
            }}
          >
            {code}
          </a>
        ) : code;
      },
    },
    { title: '案名', dataIndex: 'case_name', key: 'case_name', ellipsis: true },
    { title: '摘要', dataIndex: 'description', key: 'description', width: 180, ellipsis: true },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>發票總覽</Title></Col>
        </Row>
        <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={8}>
            <ClickableStatCard
              title="銷項總額" value={`NT$ ${salesTotal.toLocaleString()}`}
              icon={<ArrowUpOutlined />} color="#1677ff"
              active={statFilter === 'sales'}
              onClick={() => { const v = statFilter === 'sales' ? null : 'sales'; setStatFilter(v); setParams(p => ({ ...p, invoice_type: v || undefined, skip: 0 })); }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <ClickableStatCard
              title="進項總額" value={`NT$ ${purchaseTotal.toLocaleString()}`}
              icon={<ArrowDownOutlined />} color="#fa8c16"
              active={statFilter === 'purchase'}
              onClick={() => { const v = statFilter === 'purchase' ? null : 'purchase'; setStatFilter(v); setParams(p => ({ ...p, invoice_type: v || undefined, skip: 0 })); }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <ClickableStatCard
              title="淨額" value={`NT$ ${netAmount.toLocaleString()}`}
              icon={<SwapOutlined />} color={netAmount >= 0 ? '#52c41a' : '#ff4d4f'}
            />
          </Col>
        </Row>
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            value={params.invoice_type ?? ''}
            onChange={(v) => setParams(p => ({ ...p, invoice_type: v || undefined, skip: 0 }))}
            options={INVOICE_TYPE_OPTIONS}
            style={{ width: 120 }}
          />
          <Select
            placeholder="年度" allowClear
            value={params.year}
            onChange={(v) => setParams(p => ({ ...p, year: v ?? undefined, skip: 0 }))}
            options={YEAR_OPTIONS}
            style={{ width: 120 }}
          />
        </Space>

        <Table<InvoiceSummaryItem>
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor((params.skip ?? 0) / (params.limit ?? 20)) + 1,
            pageSize: params.limit ?? 20,
            total,
            onChange: (page, pageSize) => setParams(p => ({ ...p, skip: (page - 1) * pageSize, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
          }}
          size="middle"
          scroll={{ x: 1100 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPInvoiceSummaryPage;
