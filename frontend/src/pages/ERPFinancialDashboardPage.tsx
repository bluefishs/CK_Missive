/**
 * ERP 財務儀表板頁面
 *
 * 功能：全公司財務總覽 + 專案一覽 + 預算警報
 */
import React, { useState, useMemo } from 'react';
import {
  Card, Table, Typography, Statistic, Row, Col, Tag, Select, Progress, Space, Button,
} from 'antd';
import { ReloadOutlined, WarningOutlined, DownloadOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { useCompanyFinancialOverview, useAllProjectsSummary, useExportExpenses, useExportLedger, useMonthlyTrend, useBudgetRanking } from '../hooks';
import type { ProjectFinancialSummary, CompanyOverviewRequest, BudgetRankingItem } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend, LineChart, Line,
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

const PIE_COLORS = ['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5', '#70AD47', '#264478', '#9B59B6', '#E74C3C', '#1ABC9C', '#F39C12', '#2C3E50', '#8E44AD', '#16A085', '#D35400'];

const currentYear = new Date().getFullYear() - 1911;
const yearOptions = Array.from({ length: 5 }, (_, i) => ({
  value: currentYear - i,
  label: `${currentYear - i} 年`,
}));

const ERPFinancialDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [overviewParams] = useState<CompanyOverviewRequest>({ top_n: 10 });
  const [projectsYear, setProjectsYear] = useState<number | undefined>();
  const { data: overviewData, isLoading: overviewLoading, refetch: refetchOverview } = useCompanyFinancialOverview(overviewParams);
  const { data: projectsData, isLoading: projectsLoading } = useAllProjectsSummary({ year: projectsYear, limit: 50 });
  const { data: trendData, isLoading: trendLoading } = useMonthlyTrend({ months: 12 });
  const { data: rankingData, isLoading: rankingLoading } = useBudgetRanking({ top_n: 15 });
  const exportExpensesMutation = useExportExpenses();
  const exportLedgerMutation = useExportLedger();

  const overview = overviewData?.data;
  const projects = useMemo(() => projectsData?.items ?? [], [projectsData?.items]);
  const trendMonths = trendData?.data?.months ?? [];
  const rankingItems: BudgetRankingItem[] = rankingData?.data?.items ?? [];

  // 利潤率排名 (淨額 Top 15)
  const profitChartData = useMemo(() => {
    if (!projects.length) return [];
    return [...projects]
      .sort((a, b) => Number(b.net_balance) - Number(a.net_balance))
      .slice(0, 15)
      .map((p) => ({
        name: p.case_name || p.case_code,
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
      dataIndex: 'case_code',
      key: 'case_code',
      width: 140,
      render: (v: string) => <a onClick={() => navigate(`${ROUTES.ERP_EXPENSES}?case_code=${v}`)}>{v}</a>,
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

      {/* 圖表分析區 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {/* 跨專案利潤率排名 */}
        <Col xs={24} lg={14}>
          <Card title={<Text strong>專案利潤排名 (Top 15)</Text>} size="small">
            {profitChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={360}>
                <BarChart data={profitChartData} layout="vertical" margin={{ left: 80, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`} />
                  <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value: number, name: string) => [
                      `${value.toLocaleString()} 元`,
                      name === 'income' ? '收入' : name === 'expense' ? '支出' : '淨額',
                    ]}
                  />
                  <Bar dataKey="income" name="收入" fill="#52c41a" barSize={8} />
                  <Bar dataKey="expense" name="支出" fill="#ff4d4f" barSize={8} />
                  <Bar dataKey="net" name="淨額" barSize={10}>
                    {profitChartData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.net >= 0 ? '#1890ff' : '#faad14'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無專案資料</div>
            )}
          </Card>
        </Col>

        {/* 支出分類圓餅圖 */}
        <Col xs={24} lg={10}>
          <Card title={<Text strong>支出分類分布</Text>} size="small">
            {categoryPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={360}>
                <PieChart>
                  <Pie
                    data={categoryPieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    dataKey="value"
                    label={(props) => {
                      const { name, percent } = props as { name: string; percent: number };
                      return `${name} ${(percent * 100).toFixed(1)}%`;
                    }}
                    labelLine={{ strokeWidth: 1 }}
                  >
                    {categoryPieData.map((_, idx) => (
                      <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [`${value.toLocaleString()} 元`]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無分類資料</div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 月度收支趨勢 + 預算使用率排行 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={14}>
          <Card title={<Text strong>月度收支趨勢 (近 12 個月)</Text>} size="small" loading={trendLoading}>
            {trendMonths.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={trendMonths.map((m) => ({ ...m, income: Number(m.income), expense: Number(m.expense), net: Number(m.net) }))} margin={{ left: 10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`} />
                  <Tooltip formatter={(value: number, name: string) => [
                    `${value.toLocaleString()} 元`,
                    name === 'income' ? '收入' : name === 'expense' ? '支出' : '淨額',
                  ]} />
                  <Line type="monotone" dataKey="income" name="收入" stroke="#52c41a" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="expense" name="支出" stroke="#ff4d4f" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="net" name="淨額" stroke="#1890ff" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無趨勢資料</div>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title={<Text strong>預算使用率排行 (Top 15)</Text>} size="small" loading={rankingLoading}>
            {rankingItems.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={rankingItems.map((r) => ({ name: r.case_name || r.case_code, usage: r.usage_pct ?? 0, alert: r.alert }))} layout="vertical" margin={{ left: 100, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, (max: number) => Math.max(max, 100)]} tickFormatter={(v: number) => `${v}%`} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, '使用率']} />
                  <Bar dataKey="usage" name="使用率" barSize={14}>
                    {rankingItems.map((r, idx) => (
                      <Cell key={idx} fill={r.alert === 'critical' ? '#ff4d4f' : r.alert === 'warning' ? '#faad14' : '#52c41a'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無排行資料</div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 專案財務一覽 */}
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
    </ResponsiveContent>
  );
};

export default ERPFinancialDashboardPage;
