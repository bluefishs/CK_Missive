/**
 * 招標採購儀表板
 *
 * 參照 acebidx.com 設計，提供多區塊分類統計：
 * - 統計卡片: 今日招標/決標、本週招標/決標、無法決標、公開徵求
 * - 列表: 本週招標/決標/得標廠商/無法決標
 * - 圖表: 類別分布/類型分布
 *
 * @version 2.0.0
 */
import React, { useState } from 'react';
import {
  Card, Row, Col, Table, Tag, Typography, Spin, Button, Space,
} from 'antd';
import {
  FundOutlined, ReloadOutlined, BankOutlined, TrophyOutlined,
  FileSearchOutlined, WarningOutlined, CalendarOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { ClickableStatCard } from '../components/common';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useResponsive } from '../hooks';
import apiClient from '../api/client';
import CategoryPieChart from '../components/tender/CategoryPieChart';
import { TENDER_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

interface TenderItem {
  title: string; date: string; type: string; category: string;
  unit_name: string; unit_id: string; job_number: string;
  winner_names?: string[]; matched_keyword?: string;
}

interface DashboardData {
  total_found: number;
  keywords_used: string[];
  latest_date: string;
  today_date: string;
  ezbid_count: number;
  date_ranges: Record<string, string>;
  stats: {
    latest_bid: number; latest_award: number;
    week_new_bid: number; week_new_award: number;
    failed_award: number; rfp_count: number;
  };
  latest_bid_list: TenderItem[];
  latest_award_list: TenderItem[];
  week_new_bid_list: TenderItem[];
  week_new_award_list: TenderItem[];
  failed_award_list: TenderItem[];
  rfp_list: TenderItem[];
  top_winners: Array<{ name: string; count: number }>;
  category_distribution: Array<{ name: string; value: number }>;
  type_distribution: Array<{ name: string; value: number }>;
  budget_distribution: Array<{ name: string; value: number }>;
  top_agencies: Array<{ name: string; count: number }>;
}

const TenderDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });
  const [activeList, setActiveList] = useState('week_bid');

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

  const stats = data?.stats;

  // 共用表格欄位
  const tenderColumns: ColumnsType<TenderItem> = [
    {
      title: '公告日', dataIndex: 'date', width: 100,
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '標案名稱', dataIndex: 'title', ellipsis: true,
      render: (v: string, r) => (
        <a onClick={() => navigate(`/tender/${encodeURIComponent(r.unit_id)}/${encodeURIComponent(r.job_number)}`)} style={{ fontWeight: 500 }}>{v}</a>
      ),
    },
    {
      title: '招標機關', dataIndex: 'unit_name', width: 160, ellipsis: true,
      render: (v: string) => <><BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{v}</>,
    },
    {
      title: '得標', key: 'winner', width: 120, ellipsis: true,
      render: (_: unknown, r: TenderItem) =>
        r.winner_names?.length ? <Text style={{ color: '#52c41a' }}>{r.winner_names[0]}</Text> : <Text type="secondary">-</Text>,
    },
  ];

  const dr = data?.date_ranges ?? {};

  // 列表資料映射 — 使用後端回傳的實際日期範圍
  const listDataMap: Record<string, { title: string; data: TenderItem[] }> = {
    latest_bid: { title: `最新招標 (${dr.latest_bid || '–'})`, data: data?.latest_bid_list ?? [] },
    latest_award: { title: `最新決標 (${dr.latest_award || '–'})`, data: data?.latest_award_list ?? [] },
    week_bid: { title: `本週招標 (${dr.week_bid || '–'})`, data: data?.week_new_bid_list ?? [] },
    week_award: { title: `本週決標 (${dr.week_award || '–'})`, data: data?.week_new_award_list ?? [] },
    failed: { title: `無法決標 (${dr.failed || '近期'})`, data: data?.failed_award_list ?? [] },
    rfp: { title: `公開徵求 (${dr.rfp || '近期'})`, data: data?.rfp_list ?? [] },
  };

  const currentList = listDataMap[activeList] ?? { title: '本週最新招標', data: [] };

  if (isLoading) return <Spin style={{ display: 'block', margin: '80px auto' }} size="large" />;

  return (
    <div style={{ padding: pagePadding }}>
      {/* 標題列 */}
      <Card size={isMobile ? 'small' : undefined} style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={isMobile ? 4 : 3} style={{ margin: 0 }}><FundOutlined /> 招標採購儀表板</Title></Col>
          <Col>
            <Space>
              <Text type="secondary">共 {data?.total_found?.toLocaleString() ?? 0} 筆</Text>
              {(data?.ezbid_count ?? 0) > 0 && <Tag color="green">含 {data?.ezbid_count} 筆即時</Tag>}
              <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
              <Button type="primary" onClick={() => navigate(ROUTES.TENDER_SEARCH)}>搜尋標案</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 統計卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <ClickableStatCard
            title={`最新招標 (${dr.latest_bid || '–'})`} value={stats?.latest_bid ?? 0}
            icon={<CalendarOutlined />} color="#1890ff"
            active={activeList === 'latest_bid'}
            onClick={() => setActiveList('latest_bid')}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <ClickableStatCard
            title={`最新決標 (${dr.latest_award || '–'})`} value={stats?.latest_award ?? 0}
            icon={<CheckCircleOutlined />} color="#52c41a"
            active={activeList === 'latest_award'}
            onClick={() => setActiveList('latest_award')}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <ClickableStatCard
            title={`本週招標 (${dr.week_bid || '–'})`} value={stats?.week_new_bid ?? 0}
            icon={<FileSearchOutlined />} color="#722ed1"
            active={activeList === 'week_bid'}
            onClick={() => setActiveList('week_bid')}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <ClickableStatCard
            title={`本週決標 (${dr.week_award || '–'})`} value={stats?.week_new_award ?? 0}
            icon={<TrophyOutlined />} color="#13c2c2"
            active={activeList === 'week_award'}
            onClick={() => setActiveList('week_award')}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <ClickableStatCard
            title={`無法決標 (${dr.failed || '近期'})`} value={stats?.failed_award ?? 0}
            icon={<WarningOutlined />} color="#ff4d4f"
            active={activeList === 'failed'}
            onClick={() => setActiveList('failed')}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <ClickableStatCard
            title={`公開徵求 (${dr.rfp || '近期'})`} value={stats?.rfp_count ?? 0}
            icon={<FileSearchOutlined />} color="#faad14"
            active={activeList === 'rfp'}
            onClick={() => setActiveList('rfp')}
          />
        </Col>
      </Row>

      {/* 標案列表 — 點擊統計卡片切換 */}
      <Card
        title={currentList.title}
        size="small"
        extra={<Tag color="blue">{currentList.data.length} 筆</Tag>}
        style={{ marginBottom: 16 }}
      >
        <Table<TenderItem>
          columns={tenderColumns}
          dataSource={currentList.data}
          rowKey={(_r, i) => `tender-${i}`}
          size="small"
          scroll={{ x: 700 }}
          pagination={currentList.data.length > 10 ? { pageSize: 10, showTotal: (t) => `共 ${t} 筆` } : false}
          onRow={(record) => ({
            onClick: () => navigate(`/tender/${encodeURIComponent(record.unit_id)}/${encodeURIComponent(record.job_number)}`),
            style: { cursor: 'pointer' },
          })}
          footer={() => currentList.data.length >= 10 ? (
            <div style={{ textAlign: 'center' }}>
              <Button type="link" onClick={() => navigate(ROUTES.TENDER_SEARCH)}>
                檢視更多標案 →
              </Button>
            </div>
          ) : null}
        />
      </Card>

      {/* 第一排：熱門招標機關 + 標案經費規模 + 近期得標廠商 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="熱門招標機關 Top 10" size="small" styles={{ body: { padding: '8px 16px' } }}>
            {data?.top_agencies?.map((a, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f0f0f0' }}>
                <a onClick={() => navigate(`${ROUTES.TENDER_ORG_ECOSYSTEM}?org=${encodeURIComponent(a.name)}`)} style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <BankOutlined style={{ marginRight: 6, color: i < 3 ? '#1890ff' : '#8c8c8c' }} />{a.name}
                </a>
                <Tag>{a.count} 件</Tag>
              </div>
            ))}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="標案經費規模 Top 10" size="small" styles={{ body: { padding: '8px 16px' } }}>
            {data?.budget_distribution?.length ? data.budget_distribution.map((b, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Text>{b.name}</Text>
                <Tag color={i < 2 ? 'blue' : 'default'}>{b.value} 件</Tag>
              </div>
            )) : <Text type="secondary">無經費資料</Text>}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="近期得標廠商 Top 10" size="small" styles={{ body: { padding: '8px 16px' } }}>
            {data?.top_winners?.length ? data.top_winners.map((w, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f0f0f0' }}>
                <a onClick={() => navigate(`${ROUTES.TENDER_COMPANY_PROFILE}?q=${encodeURIComponent(w.name)}`)} style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <TrophyOutlined style={{ marginRight: 6, color: i < 3 ? '#faad14' : '#8c8c8c' }} />
                  {w.name}
                </a>
                <Tag color={i < 3 ? 'gold' : 'default'}>{w.count} 件</Tag>
              </div>
            )) : <Text type="secondary">無得標資料</Text>}
          </Card>
        </Col>
      </Row>

      {/* 第二排：採購類別分布 + 公告類型分布 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="採購類別分布" size="small">
            <CategoryPieChart data={data?.category_distribution ?? []} height={250} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="公告類型分布" size="small">
            <CategoryPieChart data={data?.type_distribution ?? []} height={250} />
          </Card>
        </Col>
      </Row>

      {/* 資料來源狀態 */}
      <Card size="small" styles={{ body: { padding: '8px 16px' } }}>
        <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            g0v PCC: {data?.latest_date ?? '–'} (30min 快取)
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            ezbid: {data?.today_date ?? '–'} (10min 快取)
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {data?.total_found?.toLocaleString() ?? 0} 筆
            {(data?.ezbid_count ?? 0) > 0 && ` (含 ${data?.ezbid_count} 筆即時)`}
          </Text>
        </Space>
      </Card>
    </div>
  );
};

export default TenderDashboardPage;
