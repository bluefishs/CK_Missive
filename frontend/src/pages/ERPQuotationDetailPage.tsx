/**
 * ERP 報價詳情頁面
 */
import React from 'react';
import { Alert, Card, Descriptions, Tag, Spin, Button, Typography, Tabs, Statistic, Row, Col, Space } from 'antd';
import { ArrowLeftOutlined, EditOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useParams, useNavigate } from 'react-router-dom';
import { useERPQuotation, useAuthGuard } from '../hooks';
import { ERP_QUOTATION_STATUS_LABELS } from '../types/erp';
import type { ERPQuotationStatus } from '../types/erp';
import { InvoicesTab, BillingsTab, VendorPayablesTab, ProfitTrendTab } from './erpQuotation';
import { ROUTES } from '../router/types';

const { Title } = Typography;

const STATUS_COLORS: Record<ERPQuotationStatus, string> = {
  draft: 'default',
  confirmed: 'success',
  revised: 'warning',
  closed: 'default',
};

export const ERPQuotationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const canWrite = hasPermission('projects:write');
  const { data: quotation, isLoading } = useERPQuotation(id ? Number(id) : null);

  if (isLoading) return <Spin description="載入中..." style={{ display: 'block', margin: '100px auto' }} />;
  if (!quotation) return <div style={{ padding: 24 }}>報價不存在</div>;

  const grossProfit = Number(quotation.gross_profit);

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space style={{ marginBottom: 16 }} align="center">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.ERP_QUOTATIONS)}>返回</Button>
        <Title level={4} style={{ margin: 0 }}>
          {quotation.case_code} {quotation.case_name ? `- ${quotation.case_name}` : ''}
        </Title>
        <Tag color={STATUS_COLORS[quotation.status]}>{ERP_QUOTATION_STATUS_LABELS[quotation.status]}</Tag>
        {canWrite && (
          <Button icon={<EditOutlined />} onClick={() => navigate(ROUTES.ERP_QUOTATION_EDIT.replace(':id', String(quotation.id)))}>
            編輯
          </Button>
        )}
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic title="總價" value={Number(quotation.total_price ?? 0)} precision={0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="成本" value={Number(quotation.total_cost)} precision={0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="毛利"
              value={grossProfit}
              precision={0}
              styles={{ content: { color: grossProfit >= 0 ? '#3f8600' : '#cf1322' } }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="毛利率" value={quotation.gross_margin ? Number(quotation.gross_margin) : 0} suffix="%" precision={1} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="已請款" value={Number(quotation.total_billed)} precision={0} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="已收款" value={Number(quotation.total_received)} precision={0} />
          </Card>
        </Col>
      </Row>

      {quotation.budget_limit && (
        <Alert
          type={quotation.is_over_budget ? 'error' : 'info'}
          message={`預算上限: ${Number(quotation.budget_limit).toLocaleString()} | 使用率: ${quotation.budget_usage_pct ?? '0'}%`}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        items={[
          {
            key: 'info',
            label: '成本結構',
            children: (
              <Card>
                <Descriptions column={2} bordered size="small">
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
              </Card>
            ),
          },
          {
            key: 'invoices',
            label: `發票 (${quotation.invoice_count})`,
            children: id ? <InvoicesTab erpQuotationId={Number(id)} /> : null,
          },
          {
            key: 'billings',
            label: `請款 (${quotation.billing_count})`,
            children: id ? <BillingsTab erpQuotationId={Number(id)} /> : null,
          },
          {
            key: 'payables',
            label: '廠商應付',
            children: id ? <VendorPayablesTab erpQuotationId={Number(id)} /> : null,
          },
          {
            key: 'trend',
            label: '損益趨勢',
            children: <ProfitTrendTab />,
          },
        ]}
      />
    </ResponsiveContent>
  );
};

export default ERPQuotationDetailPage;
