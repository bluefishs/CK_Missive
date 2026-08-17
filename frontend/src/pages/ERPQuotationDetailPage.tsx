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
import { FileTextOutlined, ProfileOutlined } from '@ant-design/icons';
import { QuotationItemsTab } from './erpQuotation';
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
        {quotation.amount_mismatch && (
          <Alert
            type="warning"
            showIcon
            message={`PM 合約金額 (NT$ ${Number(quotation.pm_contract_amount ?? 0).toLocaleString()}) 與 ERP 報價總額不一致，請確認是否需要同步更新。`}
          />
        )}
        {/* 合約概況 */}
        {/* 2026-08-15：金額欄改為 lg 才分四欄。
            原本 sm={6}（≥576px 就四欄）—— 768px 扣掉側欄約 568px 可用，
            四欄各約 126px，而「22,675,000」在 24px 字級約需 132px，**必然裁切**。
            390px 時是兩欄（約 175px）所以行動觀測量不到 ——
            `pageOverflow: 0` 只代表文件沒被撐寬，**元素在固定寬度欄位裡被裁切不會撐寬文件**。
            這一類要靠真人看，或看下方 money-stat 的字級收斂。 */}
        {/* 金額字級收斂：AntD Statistic 預設 24px 不會隨欄寬縮小，
            長數字（22,675,000＝10 字元）在窄欄會被裁切。
            clamp 讓它在窄欄自動降到 16px，寬螢幕維持 24px。 */}
        <style>{`.money-stat .ant-statistic-content-value {
          font-size: clamp(16px, 2.2vw, 24px) !important;
          white-space: nowrap;
        }`}</style>
        <Card size="small" title="合約概況" className="money-stat">
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={12} lg={6}><Statistic title="合約總價" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
            {/* 2026-08-15 owner：「報價單估列費用、實際成本、毛利皆由區分清楚不可混淆」。
                原本只有一個「估計成本」，看的人不知道那是報價時填的估列還是真的花掉的錢。
                三個數字各自標明基準：估列來自報價單、實際來自統一帳本、待入帳是填報缺口。 */}
            <Col xs={12} sm={12} lg={6}>
              <Statistic title="估列成本（報價單）" value={Number(quotation.total_cost)} precision={0} />
            </Col>
            <Col xs={12} sm={12} lg={6}>
              <Statistic title="實際成本（已入帳）" value={Number(quotation.actual_cost ?? 0)} precision={0} />
              {Number(quotation.pending_cost ?? 0) > 0 && (
                <div style={{ fontSize: 12, color: '#faad14', marginTop: 4, lineHeight: 1.4 }}>
                  另有 {Number(quotation.pending_cost).toLocaleString()} 元
                  <br />「應付未付＋核銷未入帳」
                </div>
              )}
            </Col>
            {/* 2026-08-15：成本未填時不得呈現毛利數字。
                後端 schema 把未填的成本存成 0，於是「沒填」與「真的是零」
                在資料裡分不出來，毛利率會顯示 100% —— 實測 77 筆報價有 37 筆
                落在這裡，其中最大一筆收入 943 萬。
                報一個 100% 比不報更糟：它看起來像結論。 */}
            {quotation.cost_declared === false ? (
              <Col xs={24} sm={12}>
                <Statistic title="預估毛利" value="—" />
                <div style={{ fontSize: 12, color: '#faad14', marginTop: 4 }}>
                  尚未填寫成本，無法計算毛利
                </div>
              </Col>
            ) : (
              <>
                <Col xs={12} sm={12} lg={6}><Statistic title="預估毛利" value={grossProfit} precision={0} styles={{ content: { color: grossProfit >= 0 ? '#3f8600' : '#cf1322' } }} /></Col>
                <Col xs={12} sm={12} lg={6}><Statistic title="預估毛利率" value={quotation.gross_margin ? Number(quotation.gross_margin) : 0} suffix="%" precision={1} /></Col>
              </>
            )}
          </Row>
        </Card>

        {/* 應收/應付概況 */}
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Card size="small" title="應收概況 (委託單位)">
              <Row gutter={[16, 8]}>
                <Col xs={12} sm={12} lg={6}><Statistic title="應收總額" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
                <Col xs={12} sm={12} lg={6}><Statistic title="已請款" value={Number(quotation.total_billed)} precision={0} /></Col>
                <Col xs={12} sm={12} lg={6}><Statistic title="已收款" value={Number(quotation.total_received)} precision={0} styles={{ content: { color: '#52c41a' } }} /></Col>
                <Col xs={12} sm={12} lg={6}><Statistic title="未收款" value={Number(quotation.total_price ?? 0) - Number(quotation.total_received)} precision={0} styles={{ content: { color: Number(quotation.total_price ?? 0) > Number(quotation.total_received) ? '#ff4d4f' : '#52c41a' } }} /></Col>
              </Row>
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card size="small" title="應付概況 (協力廠商)">
              <Row gutter={[16, 8]}>
                <Col xs={12} sm={12} lg={8}><Statistic title="應付總額" value={Number(quotation.total_payable)} precision={0} /></Col>
                <Col xs={12} sm={12} lg={8}><Statistic title="已付款" value={Number(quotation.total_paid)} precision={0} styles={{ content: { color: '#52c41a' } }} /></Col>
                <Col xs={12} sm={12} lg={8}><Statistic title="未付款" value={Number(quotation.total_payable) - Number(quotation.total_paid)} precision={0} styles={{ content: { color: Number(quotation.total_payable) > Number(quotation.total_paid) ? '#ff4d4f' : '#52c41a' } }} /></Col>
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
            <Col xs={12} sm={12} lg={6}><Statistic title="營收 (含稅)" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
            <Col xs={12} sm={12} lg={6}><Statistic title="稅額" value={Number(quotation.tax_amount)} precision={0} /></Col>
            <Col xs={12} sm={12} lg={6}><Statistic title="營收 (未稅)" value={Number(quotation.total_price ?? 0) - Number(quotation.tax_amount)} precision={0} /></Col>
            {/* 2026-08-15：原本這裡顯示「淨利」，而 net_profit 與 gross_profit
                是**同一個數字** —— 兩者並排會被讀成兩個不同的財務指標。
                真正的淨利要再扣營運費用與稅，那些資料不在報價這一層。
                改顯示「實際毛利」：以已入帳的實際成本為基準，與上方的預估毛利對照。 */}
            <Col xs={12} sm={12} lg={6}>
              <Statistic
                title="實際毛利（已入帳成本）"
                value={Number(quotation.total_price ?? 0) - Number(quotation.tax_amount) - Number(quotation.actual_cost ?? 0)}
                precision={0}
                styles={{ content: { color: '#1677ff' } }}
              />
              <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                僅計已入帳成本，與上方預估毛利基準不同
              </div>
            </Col>
          </Row>
          <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small" style={{ marginTop: 16 }}>
            <Descriptions.Item label="外包費">
              {Number(quotation.outsourcing_fee).toLocaleString()}
              {/* 2026-08-16：外包費與已建應付的落差。
                  實測 35 筆有應付的報價，**32 筆的外包費已經等於應付合計** ——
                  也就是有人在手動抄。剩下 3 筆沒抄，於是估列成本是 0
                  而應付已建 100 萬／200 萬／90 萬，毛利率顯示 100%。
                  **刻意不自動覆寫**：估列與實際是兩件事（owner 明確要求區分），
                  自動帶入會把「還沒估」與「估了剛好等於應付」混成一樣。
                  只把落差說出來，帶不帶入由人決定。 */}
              {Number(quotation.total_payable) > 0
                && Number(quotation.outsourcing_fee) !== Number(quotation.total_payable) && (
                <div style={{ fontSize: 12, color: '#faad14', marginTop: 4 }}>
                  已建應付 {Number(quotation.total_payable).toLocaleString()}
                  {Number(quotation.outsourcing_fee) === 0 ? '，但外包費尚未估列' : '，與估列不符'}
                </div>
              )}
            </Descriptions.Item>
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
    // 2026-08-16 owner：「線上報價單機制」。
    // 報價的起點是逐項內容，成本是後面才拆的。
    createTabItem('items', { icon: <ProfileOutlined />, text: '報價明細' }, (
      <QuotationItemsTab quotationId={quotation.id} caseName={quotation.case_name} caseCode={quotation.case_code} />
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
