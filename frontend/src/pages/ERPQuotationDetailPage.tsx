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
  Button, Descriptions, Statistic, Row, Col, Card, Alert, Popconfirm, App,
} from 'antd';
import {
  EditOutlined, DeleteOutlined, DollarOutlined,
  InfoCircleOutlined, BankOutlined,
} from '@ant-design/icons';
import { FileTextOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useERPQuotation, useAuthGuard } from '../hooks';
import { AccountRecordTab } from './erpQuotation/AccountRecordTab';
import ExpensesTab from './erpQuotation/ExpensesTab';
import { ROUTES } from '../router/types';

import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';
import { ExpenseQRButton } from '../components/common/ExpenseQRCode';

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
        {quotation?.case_code && (
          <ExpenseQRButton caseCode={quotation.case_code} caseName={quotation.case_name} />
        )}
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
        {/* 合約概況 */}
        <Card size="small" title="合約概況">
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}><Statistic title="合約總價" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
            <Col xs={12} sm={6}><Statistic title="估計成本" value={Number(quotation.total_cost)} precision={0} /></Col>
            <Col xs={12} sm={6}><Statistic title="預估毛利" value={grossProfit} precision={0} styles={{ content: { color: grossProfit >= 0 ? '#3f8600' : '#cf1322' } }} /></Col>
            <Col xs={12} sm={6}><Statistic title="毛利率" value={quotation.gross_margin ? Number(quotation.gross_margin) : 0} suffix="%" precision={1} /></Col>
          </Row>
        </Card>

        {/* 應收/應付概況 */}
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Card size="small" title="應收概況 (委託單位)">
              <Row gutter={[16, 8]}>
                <Col span={6}><Statistic title="應收總額" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
                <Col span={6}><Statistic title="已請款" value={Number(quotation.total_billed)} precision={0} /></Col>
                <Col span={6}><Statistic title="已收款" value={Number(quotation.total_received)} precision={0} styles={{ content: { color: '#52c41a' } }} /></Col>
                <Col span={6}><Statistic title="未收款" value={Number(quotation.total_price ?? 0) - Number(quotation.total_received)} precision={0} styles={{ content: { color: Number(quotation.total_price ?? 0) > Number(quotation.total_received) ? '#ff4d4f' : '#52c41a' } }} /></Col>
              </Row>
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card size="small" title="應付概況 (協力廠商)">
              <Row gutter={[16, 8]}>
                <Col span={8}><Statistic title="應付總額" value={Number(quotation.total_payable)} precision={0} /></Col>
                <Col span={8}><Statistic title="已付款" value={Number(quotation.total_paid)} precision={0} styles={{ content: { color: '#52c41a' } }} /></Col>
                <Col span={8}><Statistic title="未付款" value={Number(quotation.total_payable) - Number(quotation.total_paid)} precision={0} styles={{ content: { color: Number(quotation.total_payable) > Number(quotation.total_paid) ? '#ff4d4f' : '#52c41a' } }} /></Col>
              </Row>
            </Card>
          </Col>
        </Row>

        {quotation.budget_limit && (
          <Alert
            type={quotation.is_over_budget ? 'error' : 'info'}
            message={`預算上限: ${Number(quotation.budget_limit).toLocaleString()} | 使用率: ${quotation.budget_usage_pct ?? '0'}%`}
            showIcon
          />
        )}

        {/* 損益分析 */}
        <Card size="small" title="損益分析">
          <Row gutter={[16, 8]}>
            <Col span={6}><Statistic title="營收 (含稅)" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
            <Col span={6}><Statistic title="稅額" value={Number(quotation.tax_amount)} precision={0} /></Col>
            <Col span={6}><Statistic title="營收 (未稅)" value={Number(quotation.total_price ?? 0) - Number(quotation.tax_amount)} precision={0} /></Col>
            <Col span={6}><Statistic title="淨利" value={Number(quotation.net_profit)} precision={0} styles={{ content: { color: Number(quotation.net_profit) >= 0 ? '#3f8600' : '#cf1322' } }} /></Col>
          </Row>
          <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small" style={{ marginTop: 16 }}>
            <Descriptions.Item label="外包費">{Number(quotation.outsourcing_fee).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="人事費">{Number(quotation.personnel_fee).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="管銷費">{Number(quotation.overhead_fee).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="其他成本">{Number(quotation.other_cost).toLocaleString()}</Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 合約明細 */}
        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small" title="合約資訊">
          <Descriptions.Item label="案號">{quotation.case_code}</Descriptions.Item>
          <Descriptions.Item label="案名">{quotation.case_name ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="年度">{quotation.year ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="狀態">{quotation.status}</Descriptions.Item>
          <Descriptions.Item label="備註" span={2}>{quotation.notes ?? '-'}</Descriptions.Item>
        </Descriptions>
      </div>
    )),
    createTabItem('receivable', { icon: <BankOutlined />, text: '應收帳款' }, (
      id ? <AccountRecordTab erpQuotationId={Number(id)} direction="receivable" /> : null
    )),
    createTabItem('payable', { icon: <DollarOutlined />, text: '應付帳款' }, (
      id ? <AccountRecordTab erpQuotationId={Number(id)} direction="payable" /> : null
    )),
    createTabItem('expenses', { icon: <FileTextOutlined />, text: '費用核銷' }, (
      quotation?.case_code ? <ExpensesTab caseCode={quotation.case_code} /> : null
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
