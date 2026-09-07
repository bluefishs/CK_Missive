/**
 * 我的專案統整 —— 個人儀表板核心卡（2026-09-03）。
 *
 * owner：「稽催機制目前僅透過 LINE，實應配合承辦同仁建構通知機制；個人儀表板核心目標
 * 有逐漸建構個人專案相關統整資訊」。
 *
 * 這張卡回答承辦每天上班要問的四件事：我手上幾件在跑、有多少錢還沒收、哪幾筆逾期了、
 * 有沒有成案卻連請款都沒開的。數字全是後端全量（§2.6 ①），卡片可點進對應列表（§2.6 ②）。
 * 資料：`POST /erp/my-summary`，以登入者為承辦（指派表兩條綁法都認）。
 * 沒有任何案件的使用者（非承辦）整張不顯示——和 MyFilingGapsCard 同一個判準。
 */
import React from 'react';
import { Card, Col, Row, Statistic, Tag, Typography, Space, Button, Table } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ProjectOutlined, DollarOutlined, WarningOutlined, ExclamationCircleOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { ROUTES } from '../../router/types';
import { authService } from '../../services/authService';
import type { MyErpSummary, MyOverdueItem } from '../../types/erp';

const { Text } = Typography;
const money = (n?: number) => `NT$ ${(n ?? 0).toLocaleString()}`;


/**
 * 2026-09-07 owner：「重點要讓各承辦同仁完整掌握創案→報價→管理→財務流程與稽催通報，
 * 併同個人儀表板整合優化」。
 *
 * 每個數字都要**點得進去**，而且落地時已經依承辦篩好 —— 否則看到「逾期 6 筆」的下一個
 * 動作是自己去列表把條件重設一次，而那正是「掌握不了流程」的樣子。
 * 三頁的 `staff_user_id` 篩選是同一天做的，這裡直接帶上去。
 */
const Clickable: React.FC<{ onClick?: () => void; children: React.ReactNode }> = ({ onClick, children }) => (
  <div
    onClick={onClick}
    style={{ cursor: onClick ? 'pointer' : undefined, borderRadius: 6, padding: 4, margin: -4 }}
    onMouseEnter={(e) => { if (onClick) e.currentTarget.style.background = '#f5f5f5'; }}
    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
  >
    {children}
  </div>
);

export const MyErpSummaryCard: React.FC = () => {
  const navigate = useNavigate();
  // 承辦篩選要帶自己的 id —— 從已登入資訊取（與選單、權限同一個來源）
  const myUserId = (() => {
    try { return authService.getUserInfo()?.id; } catch { return undefined; }
  })();
  const withMe = (base: string, extra = '') =>
    `${base}?${myUserId ? `staff_user_id=${myUserId}` : ''}${extra}`;
  const { data, isLoading } = useQuery<MyErpSummary>({
    queryKey: ['my-erp-summary'],
    queryFn: async () => {
      const res = await apiClient.post<{ data: MyErpSummary }>(API_ENDPOINTS.ERP.MY_SUMMARY, {});
      return res.data;
    },
    staleTime: 60_000,
  });

  if (isLoading || !data) return null;
  const hasAnything = data.cases_active + data.cases_closed + data.quotes_unawarded + data.pending_count > 0;
  if (!hasAnything) return null;

  const columns = [
    { title: '案件', key: 'case', render: (_: unknown, r: MyOverdueItem) => (
      <Space direction="vertical" size={0}>
        <Text style={{ fontSize: 13 }}>{r.case_name}</Text>
        <Text type="secondary" style={{ fontSize: 11 }}>{r.case_code}{r.billing_period ? `・${r.billing_period}` : ''}</Text>
      </Space>
    ) },
    { title: '未收', key: 'amount', width: 120, align: 'right' as const, render: (_: unknown, r: MyOverdueItem) => <Text strong>{money(r.amount)}</Text> },
    { title: '逾期', key: 'days', width: 90, align: 'center' as const, render: (_: unknown, r: MyOverdueItem) => (
      <Tag color={r.days_overdue > 30 ? 'red' : 'orange'}>{r.days_overdue} 天</Tag>
    ) },
  ];

  return (
    <Card
      size="small"
      style={{ marginBottom: 16 }}
      title={<Space><ProjectOutlined /><span>我的專案統整</span><Text type="secondary" style={{ fontSize: 12 }}>以承辦身分計算</Text></Space>}
      extra={<Button type="link" size="small" onClick={() => navigate(ROUTES.ERP_QUOTATIONS)}>報價單列表</Button>}
    >
      <Row gutter={[12, 12]}>
        <Col xs={12} sm={8} md={4}>
          <Clickable onClick={() => navigate(withMe(ROUTES.CONTRACT_CASES))}>
            <Statistic title="執行中案件" value={data.cases_active} prefix={<ProjectOutlined />} />
          </Clickable>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Clickable onClick={() => navigate(withMe(ROUTES.PM_CASES))}>
            <Statistic title="未成案報價" value={data.quotes_unawarded} />
          </Clickable>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Clickable onClick={() => navigate(withMe(ROUTES.ERP_QUOTATIONS, '&card=outstanding'))}>
          <Statistic title="待收" value={data.pending_count} suffix="筆" prefix={<DollarOutlined />} />
          <Text type="secondary" style={{ fontSize: 12 }}>{money(data.pending_amount)}</Text>
          </Clickable>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic title="逾期" value={data.overdue_count} suffix="筆" valueStyle={{ color: data.overdue_count ? '#cf1322' : undefined }} prefix={<WarningOutlined />} />
          <Text type="secondary" style={{ fontSize: 12 }}>{money(data.overdue_amount)}{data.overdue_30_count ? `・>30天 ${data.overdue_30_count} 筆` : ''}</Text>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic title="今年已收" value={money(data.received_ytd)} valueStyle={{ fontSize: 16 }} prefix={<CheckCircleOutlined />} />
        </Col>
        <Col xs={12} sm={8} md={4}>
          {/* 創案→報價的缺口：案建了但一張報價單都沒有 ⇒ 它在報價、請款、稽催的每一條鏈上都還不存在 */}
          <Clickable onClick={() => navigate(withMe(ROUTES.PM_CASES))}>
            <Statistic title="尚未報價" value={data.no_quotation ?? 0}
              valueStyle={{ color: (data.no_quotation ?? 0) ? '#d46b08' : undefined }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {(data.no_quotation ?? 0) ? '建了案還沒開報價單' : '都已開報價單'}
            </Text>
          </Clickable>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic title="成案未開請款" value={data.no_billing} valueStyle={{ color: data.no_billing ? '#d46b08' : undefined }} prefix={<ExclamationCircleOutlined />} />
          <Text type="secondary" style={{ fontSize: 12 }}>{data.no_billing ? '自動第一期沒接到' : '全部有請款'}</Text>
        </Col>
      </Row>
      {data.overdue_items.length > 0 && (
        <Table<MyOverdueItem>
          size="small" style={{ marginTop: 12 }} pagination={false} rowKey="billing_id"
          dataSource={data.overdue_items} columns={columns}
          onRow={(r) => ({ style: { cursor: 'pointer' }, onClick: () => navigate(`${ROUTES.ERP_QUOTATIONS}/${r.quotation_id}?tab=receivable`) })}
          footer={() => <Text type="secondary" style={{ fontSize: 12 }}>最早的 {data.overdue_items.length} 筆；夜間吹哨者逾 30 天會升為 critical</Text>}
        />
      )}
    </Card>
  );
};

export default MyErpSummaryCard;
