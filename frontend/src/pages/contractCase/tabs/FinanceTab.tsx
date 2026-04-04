/**
 * 承攬案件「財務紀錄」Tab — 導航至 ERP Quotation 詳情頁
 *
 * 專案管理與專案財務獨立發展，透過 case_code 關聯。
 * 此 Tab 顯示摘要 + 導航連結，實際財務資料在 ERP Quotation 維護。
 */
import React from 'react';
import { Card, Empty, Button, Typography, Row, Col, Statistic, Space } from 'antd';
import { DollarOutlined, ArrowRightOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useCrossModuleLookup } from '../../../hooks/business/usePMCases';
import { ROUTES } from '../../../router/types';

const { Text } = Typography;

interface Props {
  caseCode: string | null;
  projectCode?: string | null;
}

const FinanceTab: React.FC<Props> = ({ caseCode, projectCode }) => {
  const navigate = useNavigate();
  const lookupKey = caseCode || projectCode || null;
  const { data: crossData, isLoading } = useCrossModuleLookup(lookupKey);
  const erp = crossData?.erp;

  if (isLoading) return null;

  // 無 ERP 報價 — 引導建立
  if (!erp) {
    return (
      <Empty
        image={<DollarOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={
          <>
            <Text>此案件尚無 ERP 報價紀錄</Text>
            <br />
            <Text type="secondary">請先在邀標/報價模組建立報價，成案後會自動關聯</Text>
          </>
        }
      >
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(ROUTES.PM_CASES)}>
          前往邀標報價
        </Button>
      </Empty>
    );
  }

  // 有 ERP 報價 — 顯示摘要 + 導航按鈕
  const grossProfit = Number(erp.gross_profit ?? 0);
  const erpDetailUrl = ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(erp.id));

  return (
    <div>
      {/* 摘要卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={12} sm={6}>
            <Statistic title="合約總價" value={Number(erp.total_price ?? 0)} precision={0} prefix="NT$" />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="毛利"
              value={grossProfit}
              precision={0}
              prefix="NT$"
              styles={{ content: { color: grossProfit >= 0 ? '#52c41a' : '#ff4d4f' } }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="案件代碼" value={caseCode ?? '-'} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="成案編號" value={projectCode ?? '未成案'} />
          </Col>
        </Row>
      </Card>

      {/* 導航至 ERP Quotation 詳情頁 */}
      <Card>
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          <Space direction="vertical" size="middle" align="center">
            <DollarOutlined style={{ fontSize: 36, color: '#1890ff' }} />
            <Text style={{ fontSize: 16 }}>
              財務紀錄統一在專案財務模組管理
            </Text>
            <Text type="secondary">
              包含成本結構、應收帳款、應付帳款、費用核銷
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<ArrowRightOutlined />}
              onClick={() => navigate(erpDetailUrl)}
            >
              前往專案財務 ({projectCode || caseCode})
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default FinanceTab;
