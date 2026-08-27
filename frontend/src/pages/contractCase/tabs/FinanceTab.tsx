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
import { useQuery } from '@tanstack/react-query';
import { useCrossModuleLookup } from '../../../hooks/business/usePMCases';
import { tenderApi } from '../../../api/tenderApi';
import { ROUTES } from '../../../router/types';

const { Text } = Typography;

interface Props {
  caseCode: string | null;
  projectCode?: string | null;
  projectName?: string | null;
  /** 來源標案 ID（2026-07-31 L4：用來把標案預算帶進報價表單） */
  sourceTenderId?: number | null;
}

const FinanceTab: React.FC<Props> = ({ caseCode, projectCode, projectName, sourceTenderId }) => {
  const navigate = useNavigate();
  const lookupKey = caseCode || projectCode || null;
  const { data: crossData, isLoading } = useCrossModuleLookup(lookupKey);
  const { data: sourceTender } = useQuery({
    queryKey: ['tender-by-id', sourceTenderId],
    queryFn: () => tenderApi.getById(sourceTenderId as number),
    enabled: !!sourceTenderId,
    staleTime: 5 * 60 * 1000,
  });
  const erp = crossData?.erp;
  const sourceTenderBudget = sourceTender?.budget ?? null;

  if (isLoading) return null;

  // 無 ERP 報價 — 引導建立
  if (!erp) {
    /**
     * 2026-07-29：直接建立/歷史匯入的承攬案件沒有 case_code，過去只能被導去
     * 邀標報價「重新開一個案」→ 會與既有承攬案件重複。改為帶著本案的
     * project_code + 案名跳到報價建立頁預填，存檔後即自動關聯回本案
     * （後端 cross_module_lookup 已支援 project_code fallback）。
     */
    const createParams = new URLSearchParams();
    if (projectCode) createParams.set('project_code', projectCode);
    if (projectName) createParams.set('case_name', projectName);
    // 2026-07-31 L4 財務接續：把來源標案的預算帶進報價表單的「預算上限」，
    // 否則使用者得回標案頁抄一次金額（資料明明就在系統裡）。
    if (sourceTenderBudget) createParams.set('budget_limit', sourceTenderBudget);
    const createUrl = `${ROUTES.ERP_QUOTATION_CREATE}?${createParams.toString()}`;

    return (
      <Empty
        image={<DollarOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={
          <>
            <Text>此案件尚無 ERP 報價紀錄</Text>
            <br />
            <Text type="secondary">
              {projectCode
                ? '可直接建立報價並綁定本案（會自動帶入成案編號與案名）'
                : '請先在邀標/報價模組建立報價，成案後會自動關聯'}
            </Text>
          </>
        }
      >
        <Space>
          {projectCode && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(createUrl)}>
              建立報價並綁定此案
            </Button>
          )}
          <Button icon={<PlusOutlined />} onClick={() => navigate(ROUTES.PM_CASES)}>
            前往邀標報價
          </Button>
        </Space>
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

      {/* 2026-08-27 owner：「以利掌握公司專案資金管理」。
          上面那張卡是**談定的**（合約總價／毛利），這一張是**真的進出的**。
          在此之前這一頁看不到任何實際金流 —— 而「這個案子談成 765 萬」
          與「這個案子收到 225 萬」是兩個不同的問題。 */}
      <Card size="small" title="實際金流" style={{ marginBottom: 16 }}>
        <Row gutter={[24, 16]}>
          <Col xs={12} sm={4}>
            <Statistic title="已開請款" value={Number(erp.billed_total ?? 0)} precision={0} prefix="NT$" />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="已收款" value={Number(erp.received_total ?? 0)} precision={0} prefix="NT$"
              styles={{ content: { color: '#52c41a' } }} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="未收" value={Number(erp.unreceived ?? 0)} precision={0} prefix="NT$"
              styles={{ content: { color: Number(erp.unreceived ?? 0) > 0 ? '#fa8c16' : undefined } }} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="應付" value={Number(erp.payable_total ?? 0)} precision={0} prefix="NT$" />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="已付" value={Number(erp.paid_total ?? 0)} precision={0} prefix="NT$" />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic title="未付" value={Number(erp.unpaid ?? 0)} precision={0} prefix="NT$"
              styles={{ content: { color: Number(erp.unpaid ?? 0) > 0 ? '#fa8c16' : undefined } }} />
          </Col>
        </Row>
        {Number(erp.billed_total ?? 0) === 0 && Number(erp.payable_total ?? 0) === 0 && (
          // ⚠️「還沒開始走金流」與「載不到」意思不同 —— 這裡是前者，明說出來。
          // 2026-08-27 量測：88 個承攬專案裡 9 個執行中的案子完全沒有金流紀錄，
          // 合約金額合計 1,155 萬。那不是系統故障，是**沒有人看見**。
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            這個案子還沒有任何請款或應付紀錄。
          </Text>
        )}
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
