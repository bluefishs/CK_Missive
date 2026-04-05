/**
 * Agent Evolution Metrics Card — graduation/chronic/evolution history
 *
 * Displays graduation rate, chronic rate, recent evolution history,
 * and chronic patterns that need structural attention.
 *
 * @version 1.0.0
 * @created 2026-04-05
 */

import React from 'react';
import {
  Card, Statistic, Row, Col, Table, Tag, Progress,
  Empty, Spin, Typography, Space, Tooltip,
} from 'antd';
import {
  RiseOutlined, WarningOutlined, ExperimentOutlined,
  CheckCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { AI_ENDPOINTS } from '../../api/endpoints';
import { enhanceColumns } from '../../utils/tableEnhancer';

const { Text } = Typography;

interface EvolutionMetrics {
  graduation_stats: Record<string, number>;
  graduation_rate: number;
  chronic_rate: number;
  total_learnings: number;
  evolution_history: EvolutionHistoryItem[];
  chronic_patterns: ChronicPatternItem[];
}

interface EvolutionHistoryItem {
  id: string;
  trigger: string;
  signals: number;
  promoted: number;
  demoted: number;
  graduated: number;
  chronic: number;
  score_before: number | null;
  score_after: number | null;
  created_at: string | null;
}

interface ChronicPatternItem {
  id: number;
  type: string;
  content: string;
  failure_count: number;
  created_at: string | null;
}

const triggerLabels: Record<string, string> = {
  query_count: '查詢觸發',
  daily_cycle: '每日循環',
  manual: '手動觸發',
};

const historyColumns = [
  {
    title: '時間',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 150,
    render: (v: string | null) => v ? new Date(v).toLocaleString('zh-TW') : '-',
  },
  {
    title: '觸發',
    dataIndex: 'trigger',
    key: 'trigger',
    width: 90,
    render: (v: string) => <Tag>{triggerLabels[v] ?? v}</Tag>,
  },
  {
    title: '信號',
    dataIndex: 'signals',
    key: 'signals',
    width: 60,
  },
  {
    title: '升級/降級',
    key: 'promo_demo',
    width: 100,
    render: (_: unknown, r: EvolutionHistoryItem) => (
      <Space size={4}>
        {r.promoted > 0 && <Tag color="green">+{r.promoted}</Tag>}
        {r.demoted > 0 && <Tag color="red">-{r.demoted}</Tag>}
        {r.promoted === 0 && r.demoted === 0 && <Text type="secondary">-</Text>}
      </Space>
    ),
  },
  {
    title: '畢業/慢性',
    key: 'grad_chron',
    width: 100,
    render: (_: unknown, r: EvolutionHistoryItem) => (
      <Space size={4}>
        {r.graduated > 0 && <Tag color="blue">{r.graduated} 畢業</Tag>}
        {r.chronic > 0 && <Tag color="orange">{r.chronic} 慢性</Tag>}
        {r.graduated === 0 && r.chronic === 0 && <Text type="secondary">-</Text>}
      </Space>
    ),
  },
  {
    title: '分數變化',
    key: 'score',
    width: 110,
    render: (_: unknown, r: EvolutionHistoryItem) => {
      if (r.score_before == null || r.score_after == null) return <Text type="secondary">-</Text>;
      const delta = r.score_after - r.score_before;
      return (
        <Tooltip title={`${r.score_before.toFixed(2)} -> ${r.score_after.toFixed(2)}`}>
          <Text style={{ color: delta > 0 ? '#52c41a' : delta < 0 ? '#ff4d4f' : undefined }}>
            {r.score_before.toFixed(2)} {'>'} {r.score_after.toFixed(2)}
          </Text>
        </Tooltip>
      );
    },
  },
];

const chronicColumns = [
  { title: '類型', dataIndex: 'type', key: 'type', width: 100, render: (v: string) => <Tag>{v}</Tag> },
  { title: '內容', dataIndex: 'content', key: 'content', ellipsis: true },
  { title: '失敗次數', dataIndex: 'failure_count', key: 'failure_count', width: 90, render: (v: number) => <Text type="danger">{v}</Text> },
];

export const EvolutionMetricsCard: React.FC = () => {
  const { data, isLoading } = useQuery<EvolutionMetrics>({
    queryKey: ['evolution-metrics'],
    queryFn: () => apiClient.post<{ data: EvolutionMetrics }>(AI_ENDPOINTS.STATS_EVOLUTION_METRICS, {}).then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  if (isLoading) return <Card size="small"><Spin tip="載入進化指標..." style={{ display: 'block', padding: 24, textAlign: 'center' }} /></Card>;
  if (!data) return <Card size="small"><Empty description="無進化指標資料" /></Card>;

  const gradPercent = Math.min(100, data.graduation_rate);
  const chronicPercent = Math.min(100, data.chronic_rate);

  return (
    <div>
      {/* Stats Row */}
      <Card size="small" title={<span><ExperimentOutlined /> 進化指標</span>} style={{ marginBottom: 12 }}>
        <Row gutter={16}>
          <Col xs={12} sm={6}>
            <Statistic title="學習記錄" value={data.total_learnings} prefix={<ClockCircleOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="畢業率" value={`${gradPercent.toFixed(1)}%`} prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />} />
            <Progress percent={gradPercent} size="small" showInfo={false} strokeColor="#52c41a" style={{ marginTop: 4 }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="慢性率" value={`${chronicPercent.toFixed(1)}%`} prefix={<WarningOutlined style={{ color: '#faad14' }} />} />
            <Progress percent={chronicPercent} size="small" showInfo={false} strokeColor="#faad14" status="active" style={{ marginTop: 4 }} />
          </Col>
          <Col xs={12} sm={6}>
            {Object.entries(data.graduation_stats).map(([k, v]) => (
              <Tag key={k} style={{ marginBottom: 4 }}>{k}: {v}</Tag>
            ))}
          </Col>
        </Row>
      </Card>

      {/* Evolution History + Chronic Patterns */}
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={14}>
          <Card size="small" title={<span><RiseOutlined /> 進化歷史 (近 10 次)</span>}>
            <Table
              dataSource={data.evolution_history}
              columns={enhanceColumns(historyColumns, data.evolution_history)}
              rowKey="id"
              size="small"
              pagination={false}
              scroll={{ x: 600, y: 280 }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title={<span><WarningOutlined style={{ color: '#faad14' }} /> 慢性模式 (需關注)</span>}>
            {data.chronic_patterns.length === 0 ? (
              <Empty description="無慢性模式" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table
                dataSource={data.chronic_patterns}
                columns={enhanceColumns(chronicColumns, data.chronic_patterns)}
                rowKey="id"
                size="small"
                pagination={false}
                scroll={{ y: 280 }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};
