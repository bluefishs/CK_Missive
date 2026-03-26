/**
 * Agent Performance Dashboard Tab
 *
 * Phase 3A 統計儀表板 — 視覺化 Agent 效能指標：
 * - 工具成功率 (BarChart + 降級警示)
 * - 路由分佈 (PieChart)
 * - 學習模式列表 (Table)
 * - 持久化學習統計 (Stats cards)
 *
 * @version 1.1.0
 * @created 2026-03-15
 */

import React, { useMemo } from 'react';
import {
  Card,
  Col,
  Empty,
  Row,
  Flex,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  Badge,
} from 'antd';
import {
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  XAxis,
  YAxis,
} from 'recharts';
import { AppstoreOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { PatternItem, ToolRegistryItem } from '../../../types/ai';
import { useAgentPerformanceData } from './useAgentPerformanceData';
import { AgentToolSuccessCard } from './AgentToolSuccessCard';
import { AgentAlertsCard } from './AgentAlertsCard';
import { AgentTraceTimeline } from './AgentTraceTimeline';
import { LiveActivityFeed } from './LiveActivityFeed';
import { AgentOrgChart } from './AgentOrgChart';
import { QaImpactCard } from './QaImpactCard';
import { useLiveActivitySSE } from '../../../hooks/system/useLiveActivitySSE';

const { Text } = Typography;

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96'];

const CONTEXT_COLOR_MAP: Record<string, string> = {
  doc: 'blue', pm: 'green', erp: 'orange', agent: 'purple', dispatch: 'cyan',
};

export const AgentPerformanceTab: React.FC = () => {
  const {
    toolStats,
    traces,
    patterns,
    learnings,
    alerts,
    toolRegistry,
    loading,
    toolChartData,
    routeData,
    trendData,
  } = useAgentPerformanceData();

  const { events: liveEvents, isConnected } = useLiveActivitySSE('jobs');

  // ── 工具清單欄位 ──
  const registryColumns = useMemo(() => [
    {
      title: '工具名稱',
      dataIndex: 'name',
      key: 'name',
      width: 160,
      render: (v: string) => <Text strong style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 200,
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      width: 80,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '優先序',
      dataIndex: 'priority',
      key: 'priority',
      width: 70,
      sorter: (a: ToolRegistryItem, b: ToolRegistryItem) => b.priority - a.priority,
    },
    {
      title: '上下文',
      dataIndex: 'contexts',
      key: 'contexts',
      width: 150,
      render: (ctxs: string[]) =>
        ctxs.length > 0 ? (
          <Space size={2} wrap>
            {ctxs.map((c) => (
              <Tag key={c} color={CONTEXT_COLOR_MAP[c] || 'default'}>{c}</Tag>
            ))}
          </Space>
        ) : (
          <Tag>all</Tag>
        ),
    },
    {
      title: '狀態',
      dataIndex: 'is_degraded',
      key: 'status',
      width: 70,
      render: (degraded: boolean) => (
        <Badge
          status={degraded ? 'error' : 'success'}
          text={degraded ? '降級' : '正常'}
        />
      ),
    },
  ], []);

  // ── 模式列表欄位 ──
  const patternColumns = useMemo(() => [
    {
      title: '模板',
      dataIndex: 'template',
      key: 'template',
      ellipsis: true,
      width: 200,
    },
    {
      title: '工具序列',
      dataIndex: 'tool_sequence',
      key: 'tools',
      width: 180,
      render: (tools: string[]) => (
        <Space size={2} wrap>
          {tools.slice(0, 3).map((t) => (
            <Tag key={t} color="blue" style={{ fontSize: 11 }}>{t}</Tag>
          ))}
          {tools.length > 3 && <Tag>+{tools.length - 3}</Tag>}
        </Space>
      ),
    },
    {
      title: '命中',
      dataIndex: 'hit_count',
      key: 'hits',
      width: 60,
      sorter: (a: PatternItem, b: PatternItem) => b.hit_count - a.hit_count,
    },
    {
      title: '延遲',
      dataIndex: 'avg_latency_ms',
      key: 'latency',
      width: 70,
      render: (v: number) => `${Math.round(v)}ms`,
    },
    {
      title: '分數',
      dataIndex: 'score',
      key: 'score',
      width: 60,
      render: (v: number) => v.toFixed(2),
    },
  ], []);

  if (!loading && !toolStats && !traces && !patterns && !learnings) {
    return (
      <Card>
        <Empty description="無法取得 Agent 效能資料，請確認後端服務是否正常" />
      </Card>
    );
  }

  return (
    <Spin spinning={loading}>
      <Flex vertical gap={16} style={{ width: '100%' }}>
        {/* ── 工具成功率 ── */}
        <AgentToolSuccessCard toolStats={toolStats} toolChartData={toolChartData} />

        {/* ── 工具清單 ── */}
        <Card
          title={<><AppstoreOutlined /> 工具清單 ({toolRegistry?.total_count ?? 0})</>}
          size="small"
        >
          {toolRegistry?.tools?.length ? (
            <Table
              dataSource={toolRegistry.tools}
              columns={registryColumns}
              rowKey={(record, idx) => `${record.name}-${idx}`}
              size="small"
              pagination={false}
              scroll={{ x: 730 }}
            />
          ) : (
            <Empty description="尚無工具註冊資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>

        {/* ── 每日趨勢 ── */}
        {trendData.length > 0 && (
          <Card title={<><ClockCircleOutlined /> 每日趨勢（近 14 天）</>} size="small">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="queries"
                  name="查詢數"
                  stroke="#1890ff"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="latency"
                  name="平均延遲(ms)"
                  stroke="#faad14"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* ── 路由分佈 + 學習統計 ── */}
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Card title="路由分佈" size="small">
              {routeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={routeData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={75}
                      dataKey="value"
                      nameKey="name"
                      label
                    >
                      {routeData.map((_, i) => (
                        <Cell key={`route-${i}`} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="尚無路由資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
              {traces && (
                <div style={{ textAlign: 'center', marginTop: 8 }}>
                  <Text type="secondary">共 {traces.total_count} 筆追蹤記錄</Text>
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title="持久化學習統計" size="small">
              {learnings?.stats ? (
                <Row gutter={[12, 12]}>
                  {Object.entries(learnings.stats.by_type ?? {}).map(([type, count]) => (
                    <Col xs={12} key={type}>
                      <Statistic
                        title={type}
                        value={count as number}
                        styles={{ content: { fontSize: 20 } }}
                      />
                    </Col>
                  ))}
                  <Col xs={24}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      共 {learnings.learnings.length} 條活躍學習記錄
                    </Text>
                  </Col>
                </Row>
              ) : (
                <Empty description="尚無學習資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
        </Row>

        {/* ── 主動警報 ── */}
        <AgentAlertsCard alerts={alerts} />

        {/* ── Agent 組織圖 (V-3.1) ── */}
        <AgentOrgChart />

        {/* ── Diff-aware QA 影響分析 (V-3.3) ── */}
        <QaImpactCard />

        {/* ── 即時 Swarm 轉播 (V-2.2) ── */}
        <LiveActivityFeed events={liveEvents} isConnected={isConnected} />

        {/* ── Trace Timeline 甘特圖 (V-1.2) ── */}
        {traces?.traces && traces.traces.length > 0 && (
          <AgentTraceTimeline
            traces={traces.traces.map((t) => ({
              id: t.id as number,
              question: (t.question as string) ?? '',
              total_ms: (t.total_ms as number) ?? 0,
              tools_used: (t.tools_used as string[]) ?? null,
              created_at: (t.created_at as string) ?? null,
            }))}
          />
        )}

        {/* ── 學習模式列表 ── */}
        <Card title="學習模式 Top 30" size="small">
          {patterns?.patterns?.length ? (
            <Table
              dataSource={patterns.patterns}
              columns={patternColumns}
              rowKey="pattern_key"
              size="small"
              pagination={false}
              scroll={{ x: 570 }}
            />
          ) : (
            <Empty description="尚無學習模式" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </Card>
      </Flex>
    </Spin>
  );
};

export default AgentPerformanceTab;
