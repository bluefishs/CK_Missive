/**
 * ERP 財務儀表板頁面
 *
 * 功能：全公司財務總覽 + 專案一覽 + 預算警報
 */
import React, { useState, useMemo } from 'react';
import {
  Card, Table, Typography, Statistic, Row, Col, Tag, Select, Progress, Space, Button, Alert, Segmented,
} from 'antd';
import { ReloadOutlined, WarningOutlined, DownloadOutlined, ProjectOutlined, ShopOutlined, ToolOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { useCompanyFinancialOverview, useAllProjectsSummary, useExportExpenses, useExportLedger, useMonthlyTrend, useBudgetRanking, useAgingAnalysis } from '../hooks';
import type { ProjectFinancialSummary, CompanyOverviewRequest, BudgetRankingItem, AgingBucket } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import {
  ProfitRankingChart, CategoryPieChart, MonthlyTrendChart, BudgetRankingChart,
} from './erpDashboard';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const { Title, Text } = Typography;

const ALERT_COLORS: Record<string, string> = {
  normal: 'green',
  warning: 'orange',
  critical: 'red',
};

const ALERT_LABELS: Record<string, string> = {
  normal: '正常',
  warning: '注意',
  critical: '超支警報',
};

const currentYear = new Date().getFullYear() - 1911;
const yearOptions = Array.from({ length: 5 }, (_, i) => ({
  value: currentYear - i,
  label: `${currentYear - i} 年`,
}));

const ERPFinancialDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [dashView, setDashView] = useState<'all' | 'project' | 'operational' | 'asset'>('all');
  const [overviewParams] = useState<CompanyOverviewRequest>({ top_n: 10 });
  const [projectsYear, setProjectsYear] = useState<number | undefined>();
  const { data: overviewData, isLoading: overviewLoading, isError: overviewError, refetch: refetchOverview } = useCompanyFinancialOverview(overviewParams);
  const { data: projectsData, isLoading: projectsLoading } = useAllProjectsSummary({ year: projectsYear, limit: 50 });
  const { data: trendData, isLoading: trendLoading } = useMonthlyTrend({ months: 12 });
  const { data: rankingData, isLoading: rankingLoading } = useBudgetRanking({ top_n: 15 });
  const { data: arAgingData, isLoading: arAgingLoading } = useAgingAnalysis({ direction: 'receivable' });
  const { data: apAgingData, isLoading: apAgingLoading } = useAgingAnalysis({ direction: 'payable' });
  const exportExpensesMutation = useExportExpenses();
  const exportLedgerMutation = useExportLedger();

  const overview = overviewData?.data;
  const projects = useMemo(() => projectsData?.items ?? [], [projectsData?.items]);
  const trendMonths = trendData?.data?.months ?? [];
  const rankingItems: BudgetRankingItem[] = rankingData?.data?.items ?? [];
  const arBuckets = arAgingData?.data?.buckets ?? [];
  // AR vs AP 對比圖資料
  const arVsApData = useMemo(() => {
    const arBkts = arAgingData?.data?.buckets ?? [];
    const apBkts = apAgingData?.data?.buckets ?? [];
    if (!arBkts.length && !apBkts.length) return [];
    const bucketNames = ['0-30', '31-60', '61-90', '90+'];
    return bucketNames.map((name) => {
      const ar = arBkts.find((b) => b.bucket === name);
      const ap = apBkts.find((b) => b.bucket === name);
      return { bucket: `${name} 天`, receivable: Number(ar?.amount ?? 0), payable: Number(ap?.amount ?? 0) };
    });
  }, [arAgingData?.data?.buckets, apAgingData?.data?.buckets]);

  // 利潤率排名 (淨額 Top 15)
  const profitChartData = useMemo(() => {
    if (!projects.length) return [];
    return [...projects]
      .sort((a, b) => Number(b.net_balance) - Number(a.net_balance))
      .slice(0, 15)
      .map((p) => ({
        name: p.case_name || p.project_code || p.case_code,
        caseCode: p.case_code,
        income: Number(p.total_income),
        expense: Number(p.total_expense),
        net: Number(p.net_balance),
        profitRate: Number(p.total_income) > 0
          ? ((Number(p.net_balance) / Number(p.total_income)) * 100)
          : 0,
      }));
  }, [projects]);

  // 支出分類圓餅
  const categoryPieData = useMemo(() => {
    if (!overview?.expense_by_category) return [];
    return Object.entries(overview.expense_by_category)
      .filter(([, amount]) => Number(amount) > 0)
      .map(([cat, amount]) => ({ name: cat, value: Number(amount) }))
      .sort((a, b) => b.value - a.value);
  }, [overview]);

  const projectColumns: ColumnsType<ProjectFinancialSummary> = [
    {
      title: '案號',
      key: 'project_code',
      width: 160,
      render: (_: unknown, record: ProjectFinancialSummary) => {
        const code = record.project_code || record.case_code;
        return record.erp_quotation_id ? (
          <a onClick={() => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.erp_quotation_id)))}>{code}</a>
        ) : (
          <a onClick={() => navigate(`${ROUTES.ERP_EXPENSES}?case_code=${record.case_code}`)}>{code}</a>
        );
      },
    },
    { title: '案名', dataIndex: 'case_name', key: 'case_name', ellipsis: true },
    {
      title: '預算',
      dataIndex: 'budget_total',
      key: 'budget_total',
      width: 120,
      align: 'right',
      render: (v: number | null) => v ? Number(v).toLocaleString() : '-',
    },
    {
      title: '收入',
      dataIndex: 'total_income',
      key: 'total_income',
      width: 120,
      align: 'right',
      render: (v: number) => <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span>,
    },
    {
      title: '支出',
      dataIndex: 'total_expense',
      key: 'total_expense',
      width: 120,
      align: 'right',
      render: (v: number) => <span style={{ color: '#ff4d4f' }}>{Number(v).toLocaleString()}</span>,
    },
    {
      title: '淨額',
      dataIndex: 'net_balance',
      key: 'net_balance',
      width: 120,
      align: 'right',
      render: (v: number) => {
        const num = Number(v);
        return <span style={{ color: num >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 600 }}>{num.toLocaleString()}</span>;
      },
    },
    {
      title: '預算使用',
      dataIndex: 'budget_used_percentage',
      key: 'budget_used_percentage',
      width: 150,
      render: (v: number | null) =>
        v != null ? (
          <Progress
            percent={Math.min(v, 100)}
            size="small"
            status={v > 95 ? 'exception' : v > 80 ? 'active' : 'normal'}
            format={() => `${v.toFixed(1)}%`}
          />
        ) : '-',
    },
    {
      title: '警報',
      dataIndex: 'budget_alert',
      key: 'budget_alert',
      width: 100,
      render: (v: string | null) =>
        v ? (
          <Tag color={ALERT_COLORS[v]} icon={v === 'critical' ? <WarningOutlined /> : undefined}>
            {ALERT_LABELS[v] ?? v}
          </Tag>
        ) : '-',
    },
    {
      title: '報銷',
      key: 'expense_invoices',
      width: 100,
      render: (_: unknown, record: ProjectFinancialSummary) =>
        `${record.expense_invoice_count} 筆 / ${Number(record.expense_invoice_total).toLocaleString()}`,
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {overviewError && <Alert type="error" message="財務資料載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      {/* 全公司財務總覽 */}
      <Card
        title={<Title level={3} style={{ margin: 0 }}>財務儀表板</Title>}
        extra={
          <Space>
            <Button icon={<DownloadOutlined />} onClick={() => exportExpensesMutation.mutate({})} loading={exportExpensesMutation.isPending}>匯出費用</Button>
            <Button icon={<DownloadOutlined />} onClick={() => exportLedgerMutation.mutate({})} loading={exportLedgerMutation.isPending}>匯出帳本</Button>
            <Button icon={<ReloadOutlined />} onClick={() => refetchOverview()}>重新整理</Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
        loading={overviewLoading}
      >
        {overview && (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Statistic title="總收入" value={Number(overview.total_income)} precision={0} styles={{ content: { color: '#3f8600' } }} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="總支出" value={Number(overview.total_expense)} precision={0} styles={{ content: { color: '#cf1322' } }} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="淨額"
                  value={Number(overview.net_balance)}
                  precision={0}
                  styles={{ content: { color: Number(overview.net_balance) >= 0 ? '#3f8600' : '#cf1322' } }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="統計區間" value={`${overview.period_start} ~ ${overview.period_end}`} />
              </Col>
            </Row>
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={12} sm={6}>
                <Statistic title="專案支出" value={Number(overview.project_expense)} precision={0} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="營運支出" value={Number(overview.operation_expense)} precision={0} />
              </Col>
            </Row>

            {/* 支出分類拆解 */}
            {overview.expense_by_category && Object.keys(overview.expense_by_category).length > 0 && (
              <Card title="支出分類" size="small" style={{ marginTop: 16 }}>
                <Row gutter={[8, 8]}>
                  {Object.entries(overview.expense_by_category).map(([cat, amount]) => (
                    <Col key={cat} xs={12} sm={8} md={6}>
                      <Statistic title={cat} value={Number(amount)} precision={0} />
                    </Col>
                  ))}
                </Row>
              </Card>
            )}
          </>
        )}
      </Card>

      {/* 面向切換 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Segmented
          block
          value={dashView}
          onChange={(v) => setDashView(v as typeof dashView)}
          options={[
            { value: 'all', icon: <ReloadOutlined />, label: '全部' },
            { value: 'project', icon: <ProjectOutlined />, label: '專案財務' },
            { value: 'operational', icon: <ShopOutlined />, label: '營運財務' },
            { value: 'asset', icon: <ToolOutlined />, label: '資產財務' },
          ]}
        />
      </Card>

      {/* 圖表分析區 — 依面向篩選 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={14} style={{ display: (dashView === 'all' || dashView === 'project') ? undefined : 'none' }}>
          <ProfitRankingChart data={profitChartData} />
        </Col>
        <Col xs={24} lg={10} style={{ display: (dashView === 'all' || dashView === 'operational') ? undefined : 'none' }}>
          <CategoryPieChart data={categoryPieData} />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16, display: (dashView === 'all' || dashView === 'project') ? undefined : 'none' }}>
        <Col xs={24} lg={14}>
          <MonthlyTrendChart
            data={trendMonths.map((m) => ({ ...m, income: Number(m.income), expense: Number(m.expense), net: Number(m.net) }))}
            loading={trendLoading}
          />
        </Col>
        <Col xs={24} lg={10}>
          <BudgetRankingChart data={rankingItems} loading={rankingLoading} />
        </Col>
      </Row>

      {/* 帳齡分析 + AR vs AP 對比 (全部/專案) */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16, display: (dashView === 'all' || dashView === 'project') ? undefined : 'none' }}>
        <Col xs={24} lg={14}>
          <Card title={<Text strong>應收 vs 應付帳齡對比</Text>} size="small" loading={arAgingLoading || apAgingLoading}>
            {arVsApData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={arVsApData} margin={{ left: 10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`} />
                  <Tooltip formatter={(value: number, name: string) => [
                    `${value.toLocaleString()} 元`,
                    name === 'receivable' ? '應收' : '應付',
                  ]} />
                  <Bar dataKey="receivable" name="應收" fill="#1890ff" barSize={20} />
                  <Bar dataKey="payable" name="應付" fill="#ff7a45" barSize={20} />
                  <Legend />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無帳齡資料</div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<Text strong>應收帳齡明細</Text>} size="small" loading={arAgingLoading}>
            <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
              <Col span={12}><Statistic title="未收總額" value={Number(arAgingData?.data?.total_outstanding ?? 0)} precision={0} styles={{ content: { color: '#ff4d4f' } }} /></Col>
              <Col span={12}><Statistic title="未收筆數" value={arAgingData?.data?.total_count ?? 0} suffix="筆" /></Col>
            </Row>
            <Table<AgingBucket>
              columns={[
                { title: '帳齡', dataIndex: 'bucket', width: 80, render: (v: string) => `${v} 天` },
                { title: '筆數', dataIndex: 'count', width: 60, align: 'right' },
                { title: '金額', dataIndex: 'amount', align: 'right', render: (v: number) => Number(v).toLocaleString() },
              ]}
              dataSource={arBuckets}
              rowKey="bucket"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
      </Row>

      {/* 專案財務一覽 (專案/全部) */}
      <div style={{ display: (dashView === 'all' || dashView === 'project') ? undefined : 'none' }}>
      <Card
        title={<Text strong>專案財務一覽</Text>}
        extra={
          <Space>
            <Select
              placeholder="年度"
              allowClear
              style={{ width: 120 }}
              options={yearOptions}
              onChange={(v) => setProjectsYear(v)}
            />
          </Space>
        }
      >
        <Table<ProjectFinancialSummary>
          columns={projectColumns}
          dataSource={projects}
          rowKey="case_code"
          loading={projectsLoading}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 專案` }}
          size="middle"
          scroll={{ x: 1200 }}
        />
      </Card>
      </div>

      {/* 營運面向 — 支出佔比 + 快速入口 */}
      {dashView === 'operational' && overview && (
        <Card title="營運財務概覽">
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8}>
              <Statistic title="營運支出" value={Number(overview.operation_expense)} precision={0} prefix="NT$" />
            </Col>
            <Col xs={12} sm={8}>
              <Statistic
                title="佔總支出比"
                value={Number(overview.total_expense) > 0
                  ? (Number(overview.operation_expense) / Number(overview.total_expense) * 100)
                  : 0}
                suffix="%" precision={1}
              />
            </Col>
            <Col xs={12} sm={8}>
              <Button type="primary" onClick={() => navigate(ROUTES.ERP_OPERATIONAL)}>進入營運帳目</Button>
            </Col>
          </Row>
          {/* 支出分類圓餅 (營運面向時同樣顯示) */}
          {categoryPieData.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <CategoryPieChart data={categoryPieData} />
            </div>
          )}
        </Card>
      )}

      {/* 資產面向 — 快速入口 */}
      {dashView === 'asset' && (
        <Card title="資產財務概覽">
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Button type="primary" size="large" onClick={() => navigate(ROUTES.ERP_ASSETS)}>進入資產管理</Button>
            </Col>
          </Row>
        </Card>
      )}
    </ResponsiveContent>
  );
};

export default ERPFinancialDashboardPage;
