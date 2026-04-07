/**
 * 廠商分析頁面 — 得標歷史 + 機關分布 + 勝率
 *
 * 參考: https://app.acebidx.com/orgbidder/report/
 */
import React, { useState } from 'react';
import {
  Card, Row, Col, Statistic, Table, Tag, Typography, Spin, Input, Button, Empty, Space, Progress,
} from 'antd';
import { TeamOutlined, SearchOutlined, TrophyOutlined } from '@ant-design/icons';
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

const { Title, Text } = Typography;
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96'];

interface CompanyData {
  company_name: string;
  total: number;
  won_count: number;
  win_rate: number;
  year_trend: Array<{ year: string; count: number }>;
  top_agencies: Array<{ name: string; count: number }>;
  category_distribution: Array<{ name: string; value: number }>;
  recent_tenders: Array<{
    title: string; date: string; unit_name: string;
    unit_id: string; job_number: string; type?: string; category?: string;
    winner_names?: string[]; bidder_names?: string[]; is_won?: boolean;
  }>;
}

const TenderCompanyProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCompany = searchParams.get('company') || '';
  const [companyInput, setCompanyInput] = useState(initialCompany);
  const [companyName, setCompanyName] = useState(initialCompany);

  const { data, isLoading } = useQuery<CompanyData>({
    queryKey: ['company-profile', companyName],
    queryFn: async () => {
      const res = await apiClient.post<{ data: CompanyData }>(
        TENDER_ENDPOINTS.ANALYTICS_COMPANY_PROFILE,
        { company_name: companyName },
      );
      return res.data;
    },
    enabled: !!companyName,
    staleTime: 10 * 60_000,
  });

  const doSearch = () => {
    if (companyInput.trim()) {
      setCompanyName(companyInput.trim());
      setSearchParams({ company: companyInput.trim() });
    }
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: '0 0 12px' }}><TeamOutlined /> 廠商投標分析</Title>
        <Space.Compact style={{ width: '100%', maxWidth: 600 }}>
          <Input
            placeholder="輸入廠商名稱 (如: 乾坤測繪科技有限公司)"
            value={companyInput}
            onChange={(e) => setCompanyInput(e.target.value)}
            onPressEnter={doSearch}
            size="large"
          />
          <Button type="primary" icon={<SearchOutlined />} size="large" onClick={doSearch}>分析</Button>
        </Space.Compact>
      </Card>

      {isLoading && <Spin style={{ display: 'block', margin: '60px auto' }} size="large" />}

      {data && data.total > 0 && (
        <>
          {/* 統計卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}>
              <Card><Statistic title="參與標案" value={data.total} suffix="件" /></Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic
                  title="得標數" value={data.won_count} suffix="件"
                  prefix={<TrophyOutlined style={{ color: '#faad14' }} />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Text type="secondary">得標率</Text>
                <div style={{ marginTop: 8 }}>
                  <Progress
                    type="circle" size={80}
                    percent={data.win_rate}
                    format={(p) => `${p}%`}
                    strokeColor={data.win_rate >= 50 ? '#52c41a' : data.win_rate >= 30 ? '#faad14' : '#ff4d4f'}
                  />
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card><Statistic title="合作機關" value={data.top_agencies?.length ?? 0} suffix="個" /></Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* 年度趨勢 */}
            <Col xs={24} lg={14}>
              <Card title="年度投標趨勢" size="small">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.year_trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" name="參與標案" fill="#1890ff" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>

            {/* 類別分布 */}
            <Col xs={24} lg={10}>
              <Card title="標案類別分布" size="small">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={data.category_distribution} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                      {data.category_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip /><Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* 合作機關排行 */}
            <Col xs={24} lg={12}>
              <Card title="常合作機關 (Top 15)" size="small">
                {data.top_agencies.map((a, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <a onClick={() => navigate(`${ROUTES.TENDER_ORG_ECOSYSTEM}?org=${encodeURIComponent(a.name)}`)}>{a.name}</a>
                    <Tag>{a.count}</Tag>
                  </div>
                ))}
              </Card>
            </Col>

            {/* 近期標案 — 含得標結果 */}
            <Col xs={24} lg={12}>
              <Card title="投標紀錄" size="small">
                <Table
                  columns={[
                    {
                      title: '標案', dataIndex: 'title', key: 'title', ellipsis: true,
                      render: (v: string, r: CompanyData['recent_tenders'][0]) => (
                        <a onClick={() => navigate(`/tender/${r.unit_id}/${r.job_number}`)}>{v}</a>
                      ),
                    },
                    { title: '日期', dataIndex: 'date', key: 'date', width: 100 },
                    { title: '類型', dataIndex: 'type', key: 'type', width: 70,
                      render: (v: string) => <Tag>{v || '未知'}</Tag>,
                    },
                    {
                      title: '結果', key: 'result', width: 80,
                      render: (_: unknown, r: CompanyData['recent_tenders'][0]) => {
                        // 模糊匹配：搜尋名稱包含在得標廠商名中
                        const isWon = r.is_won || (r.winner_names || []).some(
                          (w: string) => w.includes(companyName) || companyName.includes(w)
                        );
                        return isWon
                          ? <Tag color="green">得標</Tag>
                          : <Tag color="default">投標</Tag>;
                      },
                    },
                    {
                      title: '得標廠商', key: 'winner', width: 140, ellipsis: true,
                      render: (_: unknown, r: CompanyData['recent_tenders'][0]) => {
                        const winners = r.winner_names || [];
                        if (winners.length === 0) return <Text type="secondary">-</Text>;
                        return <Text style={{ fontSize: 12 }}>{winners.join('、')}</Text>;
                      },
                    },
                  ]}
                  dataSource={data.recent_tenders}
                  rowKey={(r) => `${r.unit_id}-${r.job_number}`}
                  size="small"
                  pagination={{ pageSize: 10, showSizeChanger: false }}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}

      {data && data.total === 0 && <Empty description={`找不到「${companyName}」的投標紀錄`} />}
    </ResponsiveContent>
  );
};

export default TenderCompanyProfilePage;
