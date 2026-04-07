/**
 * 機關生態分析 — 歷年標案 + 得標廠商分布 + 年度趨勢
 *
 * 參考: https://app.acebidx.com/orgecosystem/report/
 */
import React, { useState } from 'react';
import {
  Card, Row, Col, Statistic, Table, Typography, Spin, Input, Button, Empty, Space,
} from 'antd';
import { BankOutlined, SearchOutlined } from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import apiClient from '../api/client';
import { TENDER_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
const { Title } = Typography;
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];

interface OrgData {
  org_name: string;
  total: number;
  year_trend: Array<{ year: string; count: number }>;
  category_distribution: Array<{ name: string; value: number }>;
  top_winners: Array<{ name: string; count: number }>;
  recent_tenders: Array<{
    title: string; date: string; type: string; unit_name: string;
    unit_id: string; job_number: string; winner_names?: string[];
  }>;
}

const TenderOrgEcosystemPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialOrg = searchParams.get('org') || '';
  const [orgInput, setOrgInput] = useState(initialOrg);
  const [orgName, setOrgName] = useState(initialOrg);

  const { data, isLoading } = useQuery<OrgData>({
    queryKey: ['org-ecosystem', orgName],
    queryFn: async () => {
      const res = await apiClient.post<{ data: OrgData }>(
        TENDER_ENDPOINTS.ANALYTICS_ORG_ECOSYSTEM,
        { org_name: orgName },
      );
      return res.data;
    },
    enabled: !!orgName,
    staleTime: 10 * 60_000,
  });

  const doSearch = () => {
    if (orgInput.trim()) {
      setOrgName(orgInput.trim());
      setSearchParams({ org: orgInput.trim() });
    }
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: '0 0 12px' }}><BankOutlined /> 機關生態分析</Title>
        <Space.Compact style={{ width: '100%', maxWidth: 600 }}>
          <Input
            placeholder="輸入機關名稱 (如: 交通部公路局中區養護工程分局)"
            value={orgInput}
            onChange={(e) => setOrgInput(e.target.value)}
            onPressEnter={doSearch}
            size="large"
          />
          <Button type="primary" icon={<SearchOutlined />} size="large" onClick={doSearch}>分析</Button>
        </Space.Compact>
      </Card>

      {isLoading && <Spin style={{ display: 'block', margin: '60px auto' }} size="large" />}

      {data && data.total > 0 && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8}><Card><Statistic title="相關標案數" value={data.total} /></Card></Col>
            <Col xs={12} sm={8}><Card><Statistic title="得標廠商數" value={data.top_winners?.length ?? 0} /></Card></Col>
            <Col xs={12} sm={8}><Card><Statistic title="標案類別數" value={data.category_distribution?.length ?? 0} /></Card></Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* 年度趨勢 — 超過 15 年智能裁剪 */}
            <Col xs={24} lg={14}>
              {(() => {
                const raw = data.year_trend.filter(d => d.year && d.year !== '未知').sort((a, b) => a.year.localeCompare(b.year));
                const MAX_YEARS = 15;
                const display = raw.length > MAX_YEARS ? raw.slice(-MAX_YEARS) : raw;
                const yearRange = display.length > 0
                  ? `${display[0]?.year ?? ''} – ${display[display.length - 1]?.year ?? ''}`
                  : '';
                const title = raw.length > MAX_YEARS
                  ? `年度標案趨勢 (近 ${MAX_YEARS} 年: ${yearRange}，共 ${raw.length} 年資料)`
                  : `年度標案趨勢 ${yearRange ? `(${yearRange})` : ''}`;
                return (
                  <Card title={title} size="small">
                    {display.length > 0 ? (
                      <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={display}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="year" angle={display.length > 10 ? -45 : 0} textAnchor={display.length > 10 ? 'end' : 'middle'} height={display.length > 10 ? 60 : 30} />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="count" name="標案數" fill="#1890ff" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : <Empty />}
                  </Card>
                );
              })()}
            </Col>

            {/* 類別分布 — 超過 6 類合併小項為「其他」 */}
            <Col xs={24} lg={10}>
              <Card title="標案類別分布" size="small">
                {data.category_distribution.length > 0 ? (() => {
                  const MAX_SLICES = 6;
                  const raw = data.category_distribution;
                  let pieData = raw;
                  if (raw.length > MAX_SLICES) {
                    const top = raw.slice(0, MAX_SLICES - 1);
                    const otherValue = raw.slice(MAX_SLICES - 1).reduce((s, d) => s + d.value, 0);
                    pieData = [...top, { name: `其他 (${raw.length - MAX_SLICES + 1} 類)`, value: otherValue }];
                  }
                  return (
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={false}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip /><Legend />
                    </PieChart>
                  </ResponsiveContainer>
                  );
                })() : <Empty />}
              </Card>
            </Col>
          </Row>

          {/* 得標廠商排行 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} lg={12}>
              <Card title="得標廠商排行 (Top 20)" size="small">
                <Table
                  columns={[
                    { title: '排名', key: 'rank', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
                    {
                      title: '廠商', dataIndex: 'name', key: 'name',
                      render: (v: string) => (
                        <a onClick={() => navigate(`${ROUTES.TENDER_COMPANY_PROFILE}?company=${encodeURIComponent(v)}`)}>{v}</a>
                      ),
                    },
                    { title: '得標次數', dataIndex: 'count', key: 'count', width: 100, align: 'right' as const },
                  ]}
                  dataSource={data.top_winners}
                  rowKey="name"
                  size="small"
                  pagination={false}
                />
              </Card>
            </Col>

            {/* 近期標案 */}
            <Col xs={24} lg={12}>
              <Card title="近期標案" size="small">
                <Table
                  columns={[
                    {
                      title: '標案', dataIndex: 'title', key: 'title', ellipsis: true,
                      render: (v: string, r: OrgData['recent_tenders'][0]) => (
                        <a onClick={() => navigate(`/tender/${r.unit_id}/${r.job_number}`)}>{v}</a>
                      ),
                    },
                    { title: '日期', dataIndex: 'date', key: 'date', width: 100 },
                    {
                      title: '得標', key: 'winner', width: 120, ellipsis: true,
                      render: (_: unknown, r: OrgData['recent_tenders'][0]) => r.winner_names?.join(', ') || '-',
                    },
                  ]}
                  dataSource={data.recent_tenders}
                  rowKey={(r) => `${r.unit_id}-${r.job_number}`}
                  size="small"
                  pagination={false}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}

      {data && data.total === 0 && <Empty description={`找不到「${orgName}」的相關標案`} />}
    </ResponsiveContent>
  );
};

export default TenderOrgEcosystemPage;
