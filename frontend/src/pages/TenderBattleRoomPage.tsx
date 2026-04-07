/**
 * 投標戰情室 — 相似標案分析 + 競爭對手雷達
 *
 * 從 TenderDetailPage 點擊「戰情分析」進入，帶 unit_id + job_number。
 * 參考: https://app.acebidx.com/tender/.../show
 */
import React from 'react';
import {
  Card, Row, Col, Statistic, Table, Tag, Typography, Spin, Empty, Space, Progress, Button,
} from 'antd';
import {
  ThunderboltOutlined, ArrowLeftOutlined, TeamOutlined, TrophyOutlined,
} from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts';
import apiClient from '../api/client';
import { TENDER_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';

const { Title, Text } = Typography;

interface Competitor {
  name: string;
  appear_count: number;
  win_count: number;
  win_rate: number;
}

interface BattleRoomData {
  tender: {
    title: string; unit_id: string; job_number: string;
    agency: string; budget: string | null; method: string | null;
    deadline: string | null; status: string | null;
  };
  similar_tenders: Array<{
    title: string; date: string; unit_name: string;
    unit_id: string; job_number: string;
    winner_names?: string[]; category?: string;
  }>;
  similar_count: number;
  competitors: Competitor[];
  competitor_count: number;
}

const TenderBattleRoomPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const unitId = searchParams.get('unit_id') || '';
  const jobNumber = searchParams.get('job_number') || '';

  const { data, isLoading } = useQuery<BattleRoomData>({
    queryKey: ['battle-room', unitId, jobNumber],
    queryFn: async () => {
      const res = await apiClient.post<{ data: BattleRoomData }>(
        TENDER_ENDPOINTS.ANALYTICS_BATTLE_ROOM,
        { unit_id: unitId, job_number: jobNumber },
      );
      return res.data;
    },
    enabled: !!unitId && !!jobNumber,
    staleTime: 10 * 60_000,
  });

  if (!unitId || !jobNumber) {
    return (
      <ResponsiveContent maxWidth="full" padding="medium">
        <Empty description="請從標案詳情頁進入戰情室">
          <Button onClick={() => navigate(ROUTES.TENDER_SEARCH)}>回到標案搜尋</Button>
        </Empty>
      </ResponsiveContent>
    );
  }

  if (isLoading) return <Spin style={{ display: 'block', margin: '80px auto' }} size="large" />;
  if (!data) return <Empty description="無法載入戰情資料" />;

  const { tender, similar_tenders, competitors } = data;

  // 競爭雷達圖 — 取 top 6 對手
  const radarData = competitors.slice(0, 6).map(c => ({
    name: c.name.length > 6 ? c.name.slice(0, 6) + '…' : c.name,
    fullName: c.name,
    appear: c.appear_count,
    win: c.win_count,
    rate: c.win_rate,
  }));

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* 標案資訊 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col flex="auto">
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} />
              <Title level={4} style={{ margin: 0 }}>
                <ThunderboltOutlined style={{ color: '#faad14', marginRight: 8 }} />
                投標戰情室
              </Title>
            </Space>
            <div style={{ marginTop: 8 }}>
              <Text strong style={{ fontSize: 16 }}>{tender.title}</Text>
            </div>
            <Space style={{ marginTop: 4 }}>
              <Tag color="blue">{tender.agency}</Tag>
              {tender.method && <Tag>{tender.method}</Tag>}
              {tender.status && <Tag color={tender.status === '決標公告' ? 'green' : 'orange'}>{tender.status}</Tag>}
            </Space>
          </Col>
          <Col>
            <Space size="large">
              {tender.budget && <Statistic title="預算金額" value={tender.budget} />}
              {tender.deadline && <Statistic title="截止日" value={tender.deadline} />}
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}><Card><Statistic title="相似標案" value={data.similar_count} suffix="件" /></Card></Col>
        <Col xs={12} sm={6}><Card><Statistic title="潛在對手" value={data.competitor_count} suffix="家" /></Card></Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="最強對手" value={competitors[0]?.name ?? '-'}
              prefix={<TrophyOutlined style={{ color: '#faad14' }} />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="最高勝率" value={competitors[0]?.win_rate ?? 0} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {/* 競爭對手雷達圖 */}
        <Col xs={24} lg={12}>
          <Card title={<><TeamOutlined /> 競爭對手雷達 (Top 6)</>} size="small">
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis />
                  <Radar name="出現次數" dataKey="appear" stroke="#1890ff" fill="#1890ff" fillOpacity={0.3} />
                  <Radar name="得標次數" dataKey="win" stroke="#52c41a" fill="#52c41a" fillOpacity={0.3} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            ) : <Empty description="無競爭對手資料" />}
          </Card>
        </Col>

        {/* 競爭對手排行 */}
        <Col xs={24} lg={12}>
          <Card title="競爭對手排行" size="small">
            <Table
              columns={[
                { title: '排名', key: 'rank', width: 50, render: (_: unknown, __: unknown, i: number) => i + 1 },
                {
                  title: '廠商', dataIndex: 'name', key: 'name', ellipsis: true,
                  render: (v: string) => (
                    <a onClick={() => navigate(`${ROUTES.TENDER_COMPANY_PROFILE}?company=${encodeURIComponent(v)}`)}>{v}</a>
                  ),
                },
                { title: '出現', dataIndex: 'appear_count', key: 'appear', width: 60, align: 'right' as const },
                { title: '得標', dataIndex: 'win_count', key: 'win', width: 60, align: 'right' as const },
                {
                  title: '勝率', dataIndex: 'win_rate', key: 'rate', width: 80,
                  render: (v: number) => <Progress percent={v} size="small" steps={5} />,
                },
              ]}
              dataSource={competitors}
              rowKey="name"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
      </Row>

      {/* 相似標案 */}
      <Card title={`相似標案 (${similar_tenders.length} 件)`} size="small">
        <Table
          columns={[
            {
              title: '標案名稱', dataIndex: 'title', key: 'title', ellipsis: true,
              render: (v: string, r: BattleRoomData['similar_tenders'][0]) => (
                <a onClick={() => navigate(`/tender/${r.unit_id}/${r.job_number}`)}>{v}</a>
              ),
            },
            { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
            {
              title: '機關', dataIndex: 'unit_name', key: 'unit', width: 180, ellipsis: true,
              render: (v: string) => (
                <a onClick={() => navigate(`${ROUTES.TENDER_ORG_ECOSYSTEM}?org=${encodeURIComponent(v)}`)}>{v}</a>
              ),
            },
            {
              title: '得標', key: 'winner', width: 150, ellipsis: true,
              render: (_: unknown, r: BattleRoomData['similar_tenders'][0]) =>
                (r.winner_names || []).map((w, i) => <Tag key={i} color="green">{w}</Tag>),
            },
          ]}
          dataSource={similar_tenders}
          rowKey={(r, i) => `${r.unit_id}-${r.job_number}-${i}`}
          size="small"
          pagination={{ pageSize: 8 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default TenderBattleRoomPage;
