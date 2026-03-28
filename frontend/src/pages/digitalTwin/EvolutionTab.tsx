/**
 * Agent 進化歷程 Tab — 展示自主進化閉環的可視化
 *
 * 三區塊：品質趨勢 + 工具健康度 + 進化日誌
 *
 * @version 1.0.0
 * @created 2026-03-27
 */

import React from 'react';
import { Card, Row, Col, Tag, Timeline, Progress, Table, Empty, Spin, Statistic, Badge, Tooltip, Typography, Space } from 'antd';
import {
  CheckCircleOutlined, WarningOutlined, ClockCircleOutlined,
  ThunderboltOutlined, ToolOutlined, RiseOutlined, FallOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { enhanceColumns } from '../../utils/tableEnhancer';

const { Text } = Typography;

// ── API 呼叫 ──

const fetchEvolutionStatus = () =>
  apiClient.post<Record<string, unknown>>('/ai/agent/evolution/status', {});

const fetchEvolutionJournal = () =>
  apiClient.post<{ entries: Array<Record<string, unknown>> }>('/ai/agent/evolution/journal', {});

const fetchToolHealth = () =>
  apiClient.post<{ tools: ToolHealthItem[]; degraded_count: number }>('/ai/agent/tool-health', {});

interface ToolHealthItem {
  name: string;
  total_calls: number;
  success_rate: number;
  avg_latency_ms: number;
  is_degraded: boolean;
}

// ── 品質趨勢卡 ──

const QualityTrendCard: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['evolution-status'],
    queryFn: fetchEvolutionStatus,
    staleTime: 60_000,
  });

  if (isLoading) return <Card size="small"><Spin /></Card>;
  if (!data) return <Card size="small"><Empty description="無資料" /></Card>;

  const trend = (data.quality_trend as string) ?? 'stable';
  const lastRun = data.last_run_at as string;
  const promoted = (data.promoted_count as number) ?? 0;
  const demoted = (data.demoted_count as number) ?? 0;
  const queryCount = (data.total_queries as number) ?? 0;

  const trendIcon = trend === 'improving' ? <RiseOutlined style={{ color: '#52c41a' }} /> :
    trend === 'declining' ? <FallOutlined style={{ color: '#ff4d4f' }} /> :
    <ClockCircleOutlined style={{ color: '#faad14' }} />;

  const trendLabel = trend === 'improving' ? '上升中' : trend === 'declining' ? '下降中' : '穩定';

  return (
    <Card size="small" title={<span><ThunderboltOutlined /> 品質趨勢</span>}>
      <Row gutter={16}>
        <Col span={6}>
          <Statistic title="總查詢" value={queryCount} />
        </Col>
        <Col span={6}>
          <Statistic
            title="趨勢"
            value={trendLabel}
            prefix={trendIcon}
            valueStyle={{ fontSize: 16 }}
          />
        </Col>
        <Col span={6}>
          <Statistic title="已升級模式" value={promoted} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} />
        </Col>
        <Col span={6}>
          <Statistic title="已降級模式" value={demoted} valueStyle={{ color: '#ff4d4f' }} prefix={<WarningOutlined />} />
        </Col>
      </Row>
      {lastRun && (
        <Text type="secondary" style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
          上次進化: {new Date(lastRun).toLocaleString('zh-TW')}
        </Text>
      )}
    </Card>
  );
};

// ── 工具健康度 ──

const ToolHealthCard: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['tool-health'],
    queryFn: fetchToolHealth,
    staleTime: 60_000,
  });

  if (isLoading) return <Card size="small"><Spin /></Card>;

  const tools = data?.tools ?? [];
  const degradedCount = data?.degraded_count ?? 0;

  const columns = [
    {
      title: '工具',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string, record: ToolHealthItem) => (
        <Space>
          <Badge status={record.is_degraded ? 'error' : 'success'} />
          <Text style={{ fontSize: 12 }}>{name}</Text>
        </Space>
      ),
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 120,
      render: (rate: number, record: ToolHealthItem) => (
        <Tooltip title={`${record.total_calls} 次呼叫`}>
          <Progress
            percent={Math.round(rate * 100)}
            size="small"
            status={record.is_degraded ? 'exception' : rate >= 0.7 ? 'success' : 'normal'}
            format={(p) => `${p}%`}
          />
        </Tooltip>
      ),
    },
    {
      title: '延遲',
      dataIndex: 'avg_latency_ms',
      key: 'latency',
      width: 80,
      render: (ms: number) => (
        <Tag color={ms > 5000 ? 'red' : ms > 2000 ? 'orange' : 'green'}>
          {ms > 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`}
        </Tag>
      ),
    },
    {
      title: '狀態',
      key: 'status',
      width: 80,
      render: (_: unknown, record: ToolHealthItem) => (
        record.is_degraded
          ? <Tag color="error" icon={<WarningOutlined />}>降級</Tag>
          : <Tag color="success">正常</Tag>
      ),
    },
  ];

  return (
    <Card
      size="small"
      title={
        <span>
          <ToolOutlined /> 工具健康度
          {degradedCount > 0 && <Tag color="error" style={{ marginLeft: 8 }}>{degradedCount} 個降級</Tag>}
        </span>
      }
    >
      <Table
        dataSource={tools}
        columns={enhanceColumns(columns, tools)}
        rowKey="name"
        size="small"
        pagination={false}
        scroll={{ y: 300 }}
      />
    </Card>
  );
};

// ── 進化日誌 ──

const EvolutionJournalCard: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['evolution-journal'],
    queryFn: fetchEvolutionJournal,
    staleTime: 60_000,
  });

  if (isLoading) return <Card size="small"><Spin /></Card>;

  const entries = data?.entries ?? [];
  if (entries.length === 0) return <Card size="small" title="進化日誌"><Empty description="尚無進化記錄" /></Card>;

  return (
    <Card size="small" title="進化日誌" style={{ maxHeight: 400, overflow: 'auto' }}>
      <Timeline
        items={entries.slice(0, 15).map((entry, i) => ({
          key: i,
          color: (entry.promoted_count as number) > 0 ? 'green' : (entry.demoted_count as number) > 0 ? 'red' : 'blue',
          children: (
            <div>
              <Text strong style={{ fontSize: 12 }}>
                {entry.triggered_by === 'query_count' ? '查詢觸發' : '定時觸發'}
              </Text>
              <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                {entry.timestamp ? new Date(entry.timestamp as string).toLocaleString('zh-TW') : ''}
              </Text>
              <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                信號 {(entry.signals_consumed as number) ?? 0} 筆
                {Number(entry.promoted_count ?? 0) > 0 && <Tag color="green" style={{ fontSize: 10, marginLeft: 4 }}>+{String(entry.promoted_count)} 升級</Tag>}
                {Number(entry.demoted_count ?? 0) > 0 && <Tag color="red" style={{ fontSize: 10, marginLeft: 4 }}>-{String(entry.demoted_count)} 降級</Tag>}
              </div>
            </div>
          ),
        }))}
      />
    </Card>
  );
};

// ── 主元件 ──

export const EvolutionTab: React.FC = () => {
  return (
    <div>
      <QualityTrendCard />
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={14}>
          <ToolHealthCard />
        </Col>
        <Col xs={24} lg={10}>
          <EvolutionJournalCard />
        </Col>
      </Row>
    </div>
  );
};
