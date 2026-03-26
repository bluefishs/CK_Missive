/**
 * 查詢軌跡 Tab — 最近查詢列表 + Span 瀑布圖 + 工具成功率
 */
import React, { useState } from 'react';
import { Row, Col, Card, Typography, Table, Tag, Space, Empty, Spin, Alert, Progress } from 'antd';
import type { TableProps } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { AI_ENDPOINTS } from '../../api/endpoints';
import dayjs from 'dayjs';

const { Text } = Typography;

interface AgentTrace {
  id: number;
  question: string;
  answer_preview?: string;
  total_ms: number;
  tools_called: number;
  tools_succeeded: number;
  route_type: string;
  created_at: string;
  tool_calls?: Array<{
    tool_name: string;
    success: boolean;
    duration_ms: number;
    result_count?: number;
  }>;
}

interface TracesResponse {
  items: AgentTrace[];
  total: number;
}

const ROUTE_COLORS: Record<string, string> = {
  chitchat: 'cyan', pattern: 'purple', llm: 'blue', rule: 'orange',
};

export const TraceWaterfallTab: React.FC = () => {
  const [selectedTrace, setSelectedTrace] = useState<AgentTrace | null>(null);

  const { data, isLoading, isError } = useQuery<TracesResponse>({
    queryKey: ['dt-traces'],
    queryFn: () => apiClient.post(AI_ENDPOINTS.STATS_AGENT_TRACES, { limit: 20 }),
    staleTime: 60_000,
  });

  if (isLoading) return <Spin tip="載入查詢軌跡..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError) return <Alert type="warning" showIcon title="軌跡資料載入失敗" />;

  const traces = data?.items ?? [];

  // 工具成功率統計
  const toolStats: Record<string, { total: number; success: number }> = {};
  for (const trace of traces) {
    const calls = trace.tool_calls ?? [];
    for (const tc of calls) {
      const name = tc.tool_name;
      if (!toolStats[name]) toolStats[name] = { total: 0, success: 0 };
      toolStats[name].total++;
      if (tc.success) toolStats[name].success++;
    }
  }
  const toolRanking = Object.entries(toolStats)
    .map(([name, s]) => ({ name, ...s, rate: s.total > 0 ? Math.round((s.success / s.total) * 100) : 0 }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 10);

  const columns: TableProps<AgentTrace>['columns'] = [
    {
      title: '問題', dataIndex: 'question', key: 'question', ellipsis: true, width: 250,
      render: (q: string) => <Text style={{ fontSize: 12 }}>{q}</Text>,
    },
    {
      title: '路由', dataIndex: 'route_type', key: 'route', width: 80,
      render: (r: string) => <Tag color={ROUTE_COLORS[r] ?? 'default'}>{r}</Tag>,
    },
    {
      title: '工具', key: 'tools', width: 100,
      render: (_, record) => (
        <Space size={4}>
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
          <Text style={{ fontSize: 12 }}>{record.tools_succeeded}/{record.tools_called}</Text>
        </Space>
      ),
    },
    {
      title: '延遲', dataIndex: 'total_ms', key: 'latency', width: 80,
      render: (ms: number) => (
        <Tag color={ms < 3000 ? 'green' : ms < 8000 ? 'orange' : 'red'}>{ms}ms</Tag>
      ),
    },
    {
      title: '時間', dataIndex: 'created_at', key: 'time', width: 130,
      render: (dt: string) => <Text style={{ fontSize: 11 }}>{dayjs(dt).format('MM/DD HH:mm')}</Text>,
    },
  ];

  return (
    <Row gutter={[16, 16]}>
      {/* 查詢列表 */}
      <Col xs={24} lg={16}>
        <Card title={`最近查詢 (${traces.length})`} size="small">
          {traces.length > 0 ? (
            <Table
              columns={columns}
              dataSource={traces}
              rowKey="id"
              size="small"
              pagination={false}
              scroll={{ y: 400 }}
              onRow={(record) => ({
                onClick: () => setSelectedTrace(record),
                style: { cursor: 'pointer', background: selectedTrace?.id === record.id ? '#e6f7ff' : undefined },
              })}
            />
          ) : (
            <Empty description="尚無查詢紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Col>

      {/* 工具成功率 + 選定查詢詳情 */}
      <Col xs={24} lg={8}>
        <Card title="工具成功率" size="small" style={{ marginBottom: 16 }}>
          {toolRanking.length > 0 ? (
            <div>
              {toolRanking.map(t => (
                <div key={t.name} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                    <Text>{t.name}</Text>
                    <Text type="secondary">{t.success}/{t.total}</Text>
                  </div>
                  <Progress
                    percent={t.rate}
                    size="small"
                    status={t.rate >= 80 ? 'success' : t.rate >= 50 ? 'normal' : 'exception'}
                    format={(p) => `${p}%`}
                  />
                </div>
              ))}
            </div>
          ) : (
            <Empty description="尚無工具使用資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        {/* 選定查詢的 Span 瀑布 */}
        {selectedTrace && (
          <Card title={`Span 瀑布 (#${selectedTrace.id})`} size="small">
            {(selectedTrace.tool_calls ?? []).length > 0 ? (
              <div>
                {selectedTrace.tool_calls!.map((tc, idx) => (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6,
                    padding: '4px 8px', borderRadius: 4,
                    background: tc.success ? '#f6ffed' : '#fff2f0',
                  }}>
                    {tc.success
                      ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                      : <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 12 }} />}
                    <Text style={{ fontSize: 11, flex: 1 }}>{tc.tool_name}</Text>
                    <Tag style={{ fontSize: 10 }}>
                      <ClockCircleOutlined /> {tc.duration_ms}ms
                    </Tag>
                  </div>
                ))}
                <div style={{ textAlign: 'right', marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    總計 {selectedTrace.total_ms}ms
                  </Text>
                </div>
              </div>
            ) : (
              <Text type="secondary" style={{ fontSize: 11 }}>此查詢無工具呼叫（閒聊或快取命中）</Text>
            )}
          </Card>
        )}
      </Col>
    </Row>
  );
};
