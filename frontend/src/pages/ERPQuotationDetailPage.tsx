/**
 * ERP 報價詳情頁面 — 統一 DetailPageLayout 模板
 *
 * 與 documents、pm-cases、contract-cases 共用佈局/標頭/Tab。
 * 採導航模式編輯（navigate to edit page），非 inline。
 *
 * @version 2.0.0 — 遷移至 DetailPageLayout
 */
import React from 'react';
import {
  Button, Descriptions, Statistic, Row, Col, Card, Alert, Popconfirm, App, Tabs,
} from 'antd';
import {
  EditOutlined, DeleteOutlined, DollarOutlined,
  InfoCircleOutlined, FileTextOutlined, BankOutlined, LineChartOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useERPQuotation, useAuthGuard } from '../hooks';
import { InvoicesTab, BillingsTab, VendorPayablesTab, ProfitTrendTab } from './erpQuotation';
import { ROUTES } from '../router/types';

import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';

const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿', color: 'default' },
  { value: 'confirmed', label: '已確認', color: 'success' },
  { value: 'revised', label: '修訂中', color: 'warning' },
  { value: 'closed', label: '已結案', color: 'default' },
];

export const ERPQuotationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { message } = App.useApp();
  const canWrite = hasPermission('projects:write');
  const { data: quotation, isLoading } = useERPQuotation(id ? Number(id) : null);

  if (!quotation && !isLoading) {
    return <DetailPageLayout header={{ title: '報價不存在', backPath: ROUTES.ERP_QUOTATIONS }} tabs={[]} hasData={false} />;
  }

  const grossProfit = Number(quotation?.gross_profit ?? 0);
  const statusOpt = STATUS_OPTIONS.find(o => o.value === quotation?.status);

  const headerConfig = {
    title: quotation?.case_name ?? quotation?.case_code ?? '載入中...',
    subtitle: quotation?.case_code,
    icon: <DollarOutlined />,
    backPath: ROUTES.ERP_QUOTATIONS,
    backText: '返回列表',
    tags: statusOpt ? [{ text: statusOpt.label, color: statusOpt.color }] : [],
    extra: canWrite ? (
      <>
        <Button type="primary" icon={<EditOutlined />}
          onClick={() => navigate(ROUTES.ERP_QUOTATION_EDIT.replace(':id', String(quotation?.id)))}
        >編輯</Button>
        <Popconfirm title="確定刪除此報價？" okText="確定" cancelText="取消"
          okButtonProps={{ danger: true }}
          onConfirm={async () => {
            try {
              const { erpQuotationsApi } = await import('../api/erp/quotationsApi');
              await erpQuotationsApi.delete(quotation!.id);
              message.success('報價已刪除');
              navigate(ROUTES.ERP_QUOTATIONS);
            } catch { message.error('刪除失敗'); }
          }}
        >
          <Button danger icon={<DeleteOutlined />}>刪除</Button>
        </Popconfirm>
      </>
    ) : undefined,
  };

  const tabs = quotation ? [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '成本結構' }, (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 統計卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={4}><Card size="small"><Statistic title="總價" value={Number(quotation.total_price ?? 0)} precision={0} /></Card></Col>
          <Col xs={12} sm={4}><Card size="small"><Statistic title="成本" value={Number(quotation.total_cost)} precision={0} /></Card></Col>
          <Col xs={12} sm={4}><Card size="small"><Statistic title="毛利" value={grossProfit} precision={0} styles={{ content: { color: grossProfit >= 0 ? '#3f8600' : '#cf1322' } }} /></Card></Col>
          <Col xs={12} sm={4}><Card size="small"><Statistic title="毛利率" value={quotation.gross_margin ? Number(quotation.gross_margin) : 0} suffix="%" precision={1} /></Card></Col>
          <Col xs={12} sm={4}><Card size="small"><Statistic title="已請款" value={Number(quotation.total_billed)} precision={0} /></Card></Col>
          <Col xs={12} sm={4}><Card size="small"><Statistic title="已收款" value={Number(quotation.total_received)} precision={0} /></Card></Col>
        </Row>

        {quotation.budget_limit && (
          <Alert
            type={quotation.is_over_budget ? 'error' : 'info'}
            message={`預算上限: ${Number(quotation.budget_limit).toLocaleString()} | 使用率: ${quotation.budget_usage_pct ?? '0'}%`}
            showIcon
          />
        )}

        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
          <Descriptions.Item label="案號">{quotation.case_code}</Descriptions.Item>
          <Descriptions.Item label="案名">{quotation.case_name ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="年度">{quotation.year ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="總價">{Number(quotation.total_price ?? 0).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="稅額">{Number(quotation.tax_amount).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="外包費">{Number(quotation.outsourcing_fee).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="人事費">{Number(quotation.personnel_fee).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="管銷費">{Number(quotation.overhead_fee).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="其他成本">{Number(quotation.other_cost).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="淨利">{Number(quotation.net_profit).toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="備註" span={2}>{quotation.notes ?? '-'}</Descriptions.Item>
        </Descriptions>
      </div>
    )),
    createTabItem('financial', { icon: <BankOutlined />, text: '請款管理', count: (quotation.billing_count || 0) + (quotation.invoice_count || 0) }, (
      id ? (
        <Tabs defaultActiveKey="billings" size="small" items={[
          { key: 'billings', label: <><BankOutlined /> 請款紀錄</>, children: <BillingsTab erpQuotationId={Number(id)} /> },
          { key: 'invoices', label: <><FileTextOutlined /> 發票管理</>, children: <InvoicesTab erpQuotationId={Number(id)} /> },
          { key: 'payables', label: <><DollarOutlined /> 廠商應付</>, children: <VendorPayablesTab erpQuotationId={Number(id)} /> },
        ]} />
      ) : null
    )),
    createTabItem('trend', { icon: <LineChartOutlined />, text: '損益趨勢' }, (
      <ProfitTrendTab />
    )),
  ] : [];

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      loading={isLoading}
      hasData={!!quotation}
    />
  );
};

export default ERPQuotationDetailPage;
