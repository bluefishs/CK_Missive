/**
 * ERP 委託單位帳款明細頁面
 *
 * 功能：單一委託單位的跨案件應收明細 (多 Tab 案件管理模式)
 * - Tab 1: 基本資訊 (統計卡片 + 單位資訊 + 簡易案件列表)
 * - Tab 2: 案件應收明細 (可展開請款記錄)
 * - Tab 3: 收款紀錄 (跨案件扁平時間軸)
 *
 * @version 2.0.0
 */
import React, { useMemo } from 'react';
import { Button, Card, Col, Descriptions, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { InfoCircleOutlined, UnorderedListOutlined, HistoryOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { useClientAccountDetail } from '../hooks';
import type { ClientCaseReceivableItem } from '../types/erp';
import { ERP_QUOTATION_STATUS_LABELS, ERP_QUOTATION_STATUS_COLORS } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';

const { Text } = Typography;

type BillingRecord = ClientCaseReceivableItem['items'][number];
type FlatBillingRecord = BillingRecord & { case_code: string; project_code?: string; case_name?: string };

const ERPClientAccountDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const vendorId = id ? Number(id) : null;
  const { data: detail, isLoading } = useClientAccountDetail(vendorId);

  // Must be before early return to satisfy Rules of Hooks
  const allBillings = useMemo<FlatBillingRecord[]>(() => {
    if (!detail?.cases) return [];
    return detail.cases.flatMap(c =>
      (c.items ?? []).map(item => ({ ...item, case_code: c.case_code, project_code: c.project_code, case_name: c.case_name }))
    ).sort((a, b) => (a.billing_date ?? '').localeCompare(b.billing_date ?? ''));
  }, [detail]);

  if (!detail && !isLoading) {
    return (
      <DetailPageLayout
        header={{ title: '找不到此委託單位帳款資料', backPath: ROUTES.ERP_CLIENT_ACCOUNTS }}
        tabs={[]}
        hasData={false}
      />
    );
  }

  const collectionRate = Number(detail?.total_billed ?? 0) > 0
    ? (Number(detail?.total_received ?? 0) / Number(detail?.total_billed ?? 0) * 100)
    : 0;

  // --- Tab 1: 基本資訊 ---
  const simpleCaseColumns: ColumnsType<ClientCaseReceivableItem> = [
    { title: '案號', key: 'project_code', width: 160, render: (_: unknown, r) => {
      const code = r.project_code || r.case_code;
      return <a onClick={() => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(r.erp_quotation_id)))}>{code}</a>;
    }},
    { title: '案名', dataIndex: 'case_name', ellipsis: true },
    { title: '年度', dataIndex: 'year', width: 80, render: (v?: number) => v ? (v < 1911 ? v + 1911 : v) : '-' },
    { title: '合約金額', dataIndex: 'contract_amount', width: 130, align: 'right', render: (v: number) => Number(v).toLocaleString() },
  ];

  const overviewTab = createTabItem('overview', { icon: <InfoCircleOutlined />, text: '基本資訊' }, (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} lg={4}><Card size="small"><Statistic title="合約總額" value={Number(detail?.total_contract ?? 0)} precision={0} /></Card></Col>
        <Col xs={12} sm={8} lg={4}><Card size="small"><Statistic title="已請款" value={Number(detail?.total_billed ?? 0)} precision={0} /></Card></Col>
        <Col xs={12} sm={8} lg={4}><Card size="small"><Statistic title="已收款" value={Number(detail?.total_received ?? 0)} precision={0} valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col xs={12} sm={8} lg={4}><Card size="small"><Statistic title="未收餘額" value={Number(detail?.outstanding ?? 0)} precision={0} valueStyle={{ color: Number(detail?.outstanding ?? 0) > 0 ? '#fa8c16' : '#52c41a' }} /></Card></Col>
        <Col xs={12} sm={8} lg={4}><Card size="small"><Statistic title="案件數" value={detail?.cases?.length ?? 0} /></Card></Col>
        <Col xs={12} sm={8} lg={4}><Card size="small"><Statistic title="收款率" value={collectionRate} suffix="%" precision={1} /></Card></Col>
      </Row>
      <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label="單位名稱">{detail?.vendor_name ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="代碼">{detail?.vendor_code ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="案件數">{detail?.cases?.length ?? 0}</Descriptions.Item>
      </Descriptions>
      <Table<ClientCaseReceivableItem>
        columns={simpleCaseColumns}
        dataSource={detail?.cases ?? []}
        rowKey="case_code"
        size="small"
        pagination={false}
      />
    </div>
  ));

  // --- Tab 2: 案件應收明細 (existing expandable) ---
  const caseColumns: ColumnsType<ClientCaseReceivableItem> = [
    { title: '案號', key: 'project_code', width: 160, render: (_: unknown, r) => {
      const code = r.project_code || r.case_code;
      return <a onClick={() => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(r.erp_quotation_id)))}>{code}</a>;
    }},
    { title: '案名', dataIndex: 'case_name', ellipsis: true },
    { title: '合約金額', dataIndex: 'contract_amount', width: 130, align: 'right', render: (v: number) => Number(v).toLocaleString() },
    { title: '已請款', dataIndex: 'total_billed', width: 130, align: 'right', render: (v: number) => Number(v).toLocaleString() },
    { title: '已收款', dataIndex: 'total_received', width: 130, align: 'right', render: (v: number) => <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span> },
    { title: '未收餘額', dataIndex: 'outstanding', width: 130, align: 'right', render: (v: number) => {
      const num = Number(v);
      return <Tag color={num > 0 ? 'orange' : 'green'} style={{ margin: 0 }}>{num.toLocaleString()}</Tag>;
    }},
  ];

  const billingColumns: ColumnsType<BillingRecord> = [
    { title: '期別', dataIndex: 'billing_period', width: 100, render: (v?: string) => v ?? '-' },
    { title: '請款日期', dataIndex: 'billing_date', width: 120, render: (v?: string) => v ?? '-' },
    { title: '請款金額', dataIndex: 'billing_amount', width: 120, align: 'right', render: (v: number) => Number(v).toLocaleString() },
    { title: '收款狀態', dataIndex: 'payment_status', width: 100, align: 'center', render: (v: string) => {
      const color = v === 'paid' ? 'green' : v === 'partial' ? 'orange' : 'default';
      const label = v === 'paid' ? '已收' : v === 'partial' ? '部分收' : '未收';
      return <Tag color={color}>{label}</Tag>;
    }},
    { title: '收款金額', dataIndex: 'payment_amount', width: 120, align: 'right', render: (v: number) => <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span> },
    { title: '收款日期', dataIndex: 'payment_date', width: 120, render: (v: string | null) => v ?? '-' },
  ];

  const casesTab = createTabItem('cases', { icon: <UnorderedListOutlined />, text: '案件應收明細', count: detail?.cases?.length }, (
    <Table<ClientCaseReceivableItem>
      columns={caseColumns}
      dataSource={detail?.cases ?? []}
      rowKey="case_code"
      size="middle"
      pagination={false}
      expandable={{
        expandedRowRender: (record) => (
          <div>
            <Descriptions size="small" column={{ xs: 1, sm: 2, md: 4 }} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="合約金額"><Text strong>{Number(record.contract_amount ?? 0).toLocaleString()}</Text></Descriptions.Item>
              <Descriptions.Item label="年度">{record.year ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="報價狀態">
                <Tag color={ERP_QUOTATION_STATUS_COLORS[record.quotation_status as keyof typeof ERP_QUOTATION_STATUS_COLORS] ?? 'default'}>
                  {ERP_QUOTATION_STATUS_LABELS[record.quotation_status as keyof typeof ERP_QUOTATION_STATUS_LABELS] ?? record.quotation_status ?? '-'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="">
                <Space>
                  <Button type="link" size="small" onClick={() => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.erp_quotation_id)))}>報價詳情</Button>
                </Space>
              </Descriptions.Item>
            </Descriptions>
            <Table<BillingRecord> columns={billingColumns} dataSource={record.items ?? []} rowKey="id" size="small" pagination={false} />
          </div>
        ),
        rowExpandable: () => true,
      }}
    />
  ));

  // --- Tab 3: 收款時間軸 ---
  const timelineColumns: ColumnsType<FlatBillingRecord> = [
    { title: '案號', key: 'project_code', width: 140, render: (_: unknown, r) => r.project_code || r.case_code },
    { title: '期別', dataIndex: 'billing_period', width: 80, render: (v?: string) => v ?? '-' },
    { title: '請款金額', dataIndex: 'billing_amount', width: 120, align: 'right', render: (v: number) => Number(v).toLocaleString() },
    { title: '收款金額', dataIndex: 'payment_amount', width: 120, align: 'right', render: (v: number) => <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span> },
    { title: '狀態', dataIndex: 'payment_status', width: 90, align: 'center', render: (v: string) => {
      const color = v === 'paid' ? 'green' : v === 'partial' ? 'orange' : 'default';
      const label = v === 'paid' ? '已收' : v === 'partial' ? '部分收' : '未收';
      return <Tag color={color}>{label}</Tag>;
    }},
    { title: '請款日期', dataIndex: 'billing_date', width: 110, render: (v?: string) => v ?? '-' },
    { title: '收款日期', dataIndex: 'payment_date', width: 110, render: (v: string | null) => v ?? '-' },
  ];

  const timelineTab = createTabItem('timeline', { icon: <HistoryOutlined />, text: '收款紀錄', count: allBillings.length }, (
    <Table<FlatBillingRecord>
      columns={timelineColumns}
      dataSource={allBillings}
      rowKey="id"
      size="small"
      pagination={{ pageSize: 20, showTotal: (total) => `共 ${total} 筆` }}
    />
  ));

  return (
    <DetailPageLayout
      header={{
        title: detail?.vendor_name ?? '載入中...',
        backPath: ROUTES.ERP_CLIENT_ACCOUNTS,
        subtitle: detail?.vendor_code,
      }}
      tabs={[overviewTab, casesTab, timelineTab]}
      loading={isLoading}
      hasData={!!detail}
    />
  );
};

export default ERPClientAccountDetailPage;
