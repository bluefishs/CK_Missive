/**
 * 招標採購儀表板 — 近期標案統計 + 類別分布 + 推薦標案
 */
import React from 'react';
import {
  Card, Row, Col, Statistic, Table, Tag, Typography, Spin, Button, Space, Empty,
} from 'antd';
import {
  FundOutlined, ReloadOutlined, BankOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import apiClient from '../api/client';
import { TENDER_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];

interface DashboardData {
  total_found: number;
  keywords_used: string[];
  recent_tenders: Array<{
    title: string; date: string; type: string; category: string;
    unit_name: string; unit_id: string; job_number: string;
    winner_names?: string[]; matched_keyword?: string;
  }>;
  category_distribution: Array<{ name: string; value: number }>;
  type_distribution: Array<{ name: string; value: number }>;
  top_agencies: Array<{ name: string; count: number }>;
}

const TenderDashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const { data, isLoading, refetch } = useQuery<DashboardData>({
    queryKey: ['tender-dashboard'],
    queryFn: async () => {
      const res = await apiClient.post<{ data: DashboardData }>(
        TENDER_ENDPOINTS.ANALYTICS_DASHBOARD, {},
      );
      return res.data;
    },
    staleTime: 5 * 60_000,
  });

  const tenderColumns: ColumnsType<DashboardData['recent_tenders'][0]> = [
    {
      title: '標案名稱', dataIndex: 'title', key: 'title', ellipsis: true,
      render: (v: string, r) => (
        <a onClick={() => navigate(`/tender/${r.unit_id}/${r.job_number}`)}>{v}</a>
      ),
    },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '類型', dataIndex: 'type', key: 'type', width: 120, render: (v: string) => <Tag>{v}</Tag> },
    {
      title: '機關', dataIndex: 'unit_name', key: 'unit', width: 180, ellipsis: true,
      render: (v: string) => (
        <a onClick={() => navigate(`${ROUTES.TENDER_ORG_ECOSYSTEM}?org=${encodeURIComponent(v)}`)}>{v}</a>
      ),
    },
    {
      title: '關鍵字', dataIndex: 'matched_keyword', key: 'kw', width: 80,
      render: (v?: string) => v ? <Tag color="blue">{v}</Tag> : null,
    },
  ];

  if (isLoading) return <Spin style={{ display: 'block', margin: '80px auto' }} size="large" />;

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}><FundOutlined /> 招標採購儀表板</Title></Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
              <Button type="primary" onClick={() => navigate(ROUTES.TENDER_SEARCH)}>搜尋標案</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 統計卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card><Statistic title="推薦標案總數" value={data?.total_found ?? 0} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="監控關鍵字" value={data?.keywords_used?.length ?? 0} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="標案類別數" value={data?.category_distribution?.length ?? 0} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="涉及機關數" value={data?.top_agencies?.length ?? 0} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {/* 類別分布 */}
        <Col xs={24} lg={12}>
          <Card title="標案類別分布" size="small">
            {data?.category_distribution && data.category_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={data.category_distribution} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                    {data.category_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip /><Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <Empty description="無資料" />}
          </Card>
        </Col>

        {/* 熱門機關 */}
        <Col xs={24} lg={12}>
          <Card title="熱門招標機關 (Top 10)" size="small">
            {data?.top_agencies?.map((a, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                <a onClick={() => navigate(`${ROUTES.TENDER_ORG_ECOSYSTEM}?org=${encodeURIComponent(a.name)}`)}>
                  <BankOutlined style={{ marginRight: 6 }} />{a.name}
                </a>
                <Tag>{a.count} 件</Tag>
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      {/* 近期推薦標案 */}
      <Card title="近期推薦標案" size="small">
        <Table
          columns={tenderColumns}
          dataSource={data?.recent_tenders ?? []}
          rowKey={(r, i) => `${r.unit_id}-${r.job_number}-${i}`}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default TenderDashboardPage;
