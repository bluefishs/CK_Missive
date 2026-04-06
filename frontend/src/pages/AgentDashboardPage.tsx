/**
 * Agent Dashboard - 智能體中心統一頁面
 *
 * 合併 Chat UI 與 Digital Twin 為單一自覺型 Agent 頁面。
 * 左側：Agent 自我檔案卡片 (self-profile)
 * 右側：4 Tab（對話 / 自省 / 進化 / 拓撲）
 *
 * 重用 digitalTwin/ 子元件，不重複實作。
 *
 * @version 1.0.0
 * @created 2026-04-05
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Row, Col, Typography, Badge, Tabs, Card, Alert, Spin, Skeleton, Tag,
  Space, Progress, Statistic, Divider,
} from 'antd';
import {
  MessageOutlined, RadarChartOutlined,
  ApartmentOutlined, ExperimentOutlined,
  RobotOutlined, ThunderboltOutlined, BookOutlined,
  TrophyOutlined, CloudServerOutlined,
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS, DIGITAL_TWIN_ENDPOINTS } from '../api/endpoints';
import { checkGatewayHealth, getAgentTopology } from '../api/digitalTwin';
import type { AgentSelfProfile } from './digitalTwin/ProfileCard';
import { defaultProfile } from './digitalTwin/ProfileCard';
import { createTabItem } from '../components/common/DetailPage/utils';

// Lazy-load heavy sub-tabs
const RAGChatPanel = React.lazy(() =>
  import('../components/ai/RAGChatPanel').then(m => ({ default: m.RAGChatPanel }))
);
const CapabilityRadarTab = React.lazy(() =>
  import('./digitalTwin/CapabilityRadarTab').then(m => ({ default: m.CapabilityRadarTab }))
);
const EvolutionTab = React.lazy(() =>
  import('./digitalTwin/EvolutionTab').then(m => ({ default: m.EvolutionTab }))
);

const { Title, Text } = Typography;

// ── Compact Self-Profile Sidebar ─────────────────────────────

interface AgentSidebarProps {
  profile: AgentSelfProfile;
  loading: boolean;
  error: boolean;
  dashboardData: DashboardSnapshot | null;
  dashboardLoading: boolean;
}

interface DashboardSnapshot {
  profile: { total_queries: number; avg_score: number; learnings_count: number } | null;
  capability: { strengths: string[]; weaknesses: string[] } | null;
  daily: { today_queries: number; avg_latency_ms: number; tool_distribution: Record<string, number> } | null;
  quality: { avg_score: number; total_evaluated: number } | null;
  recent_traces: Array<{ query: string; latency_ms: number; tool_count: number; created_at: string }> | null;
  health: { available: boolean; systems_count: number } | null;
}

const AgentSidebarInner: React.FC<AgentSidebarProps> = ({
  profile, loading, error, dashboardData, dashboardLoading,
}) => {
  if (loading) {
    return (
      <Card styles={{ body: { padding: '20px 16px' } }}>
        <Skeleton active avatar={{ shape: 'circle', size: 52 }} paragraph={{ rows: 6 }} />
      </Card>
    );
  }
  if (error) {
    return (
      <Card>
        <Alert type="warning" showIcon message="智能體檔案載入失敗" />
      </Card>
    );
  }

  const scorePercent = Math.min(100, Math.round((profile.avg_score ?? 0) * 20));
  const daily = dashboardData?.daily;
  const capability = dashboardData?.capability;
  const learningsCount = profile.learnings_count ?? 0;
  // Graduation rate estimate: learnings with high confidence
  const graduationRate = learningsCount > 0 ? Math.min(100, Math.round((learningsCount / Math.max(learningsCount + 5, 1)) * 100)) : 0;

  return (
    <Card styles={{ body: { padding: '20px 16px' } }}>
      {/* Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <div style={{
          width: 52, height: 52, borderRadius: '50%',
          background: 'linear-gradient(135deg, #722ed1 0%, #13c2c2 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <RobotOutlined style={{ fontSize: 26, color: '#fff' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Title level={5} style={{ margin: 0 }}>{profile.identity || '乾坤智能體'}</Title>
          <Text type="secondary" style={{ fontSize: 11 }}>v5.5.0 | gemma4-8b-q4</Text>
        </div>
        <Badge status="success" text="" />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* 30-day Stats */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}>
          <ThunderboltOutlined /> 30 日統計
        </Text>
        <Row gutter={8} style={{ marginTop: 8 }}>
          <Col span={12}>
            <Statistic
              title={<span style={{ fontSize: 11 }}>查詢次數</span>}
              value={profile.total_queries ?? 0}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title={<span style={{ fontSize: 11 }}>平均延遲</span>}
              value={daily?.avg_latency_ms ?? 0}
              suffix="ms"
              valueStyle={{ fontSize: 20 }}
              loading={dashboardLoading}
            />
          </Col>
        </Row>
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Quality Score */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}>
          <TrophyOutlined /> 品質評分
        </Text>
        <Progress
          percent={scorePercent}
          strokeColor={scorePercent >= 80 ? '#52c41a' : scorePercent >= 60 ? '#faad14' : '#ff4d4f'}
          format={() => `${(profile.avg_score ?? 0).toFixed(1)}/5`}
          style={{ marginTop: 8 }}
        />
      </div>

      {/* Learning Graduation */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}>
          <BookOutlined /> 學習畢業率
        </Text>
        <Progress
          percent={graduationRate}
          strokeColor="#722ed1"
          format={() => `${learningsCount} 條`}
          style={{ marginTop: 8 }}
        />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Strengths / Weaknesses */}
      {capability && (
        <div>
          {(capability.strengths ?? []).length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <Text style={{ fontSize: 11, color: '#8c8c8c' }}>擅長領域</Text>
              <div style={{ marginTop: 4 }}>
                <Space wrap size={[4, 4]}>
                  {capability.strengths.slice(0, 5).map(s => (
                    <Tag key={s} color="green" style={{ fontSize: 11 }}>{s}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          )}
          {(capability.weaknesses ?? []).length > 0 && (
            <div>
              <Text style={{ fontSize: 11, color: '#8c8c8c' }}>待加強</Text>
              <div style={{ marginTop: 4 }}>
                <Space wrap size={[4, 4]}>
                  {capability.weaknesses.slice(0, 5).map(w => (
                    <Tag key={w} color="orange" style={{ fontSize: 11 }}>{w}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          )}
        </div>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* Top Domains */}
      {profile.top_domains?.length > 0 && (
        <div>
          <Text style={{ fontSize: 11, color: '#8c8c8c' }}>熱門領域</Text>
          <div style={{ marginTop: 4 }}>
            <Space wrap size={[4, 4]}>
              {profile.top_domains.slice(0, 4).map(d => (
                <Tag key={d.domain} style={{ fontSize: 11 }}>
                  {d.domain} ({d.count})
                </Tag>
              ))}
            </Space>
          </div>
        </div>
      )}
    </Card>
  );
};

const AgentSidebar = React.memo(AgentSidebarInner);

// ── Topology Tab (inline, re-uses digitalTwin API) ───────────

const TopologyTab: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dt-topology'],
    queryFn: getAgentTopology,
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin tip="載入拓撲圖..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError) return <Alert type="warning" showIcon message="拓撲資料載入失敗" />;

  const nodes = (data?.nodes ?? []) as Array<{
    id: string; label: string; type: string; status: string;
    project: string; capabilities?: string[];
  }>;

  const typeColors: Record<string, string> = {
    leader: '#722ed1', engine: '#1890ff', role: '#52c41a', plugin: '#faad14',
  };
  const statusColors: Record<string, 'success' | 'error' | 'default' | 'processing'> = {
    active: 'success', unknown: 'default', error: 'error', busy: 'processing',
  };

  return (
    <Row gutter={[12, 12]}>
      {nodes.map(node => (
        <Col xs={24} sm={12} md={8} key={node.id}>
          <Card size="small" style={{ borderLeft: `3px solid ${typeColors[node.type] ?? '#d9d9d9'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <Text strong style={{ fontSize: 13 }}>{node.label}</Text>
              <Badge status={statusColors[node.status] ?? 'default'} text={node.status} />
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{node.project}</Text>
            {node.capabilities && (
              <div style={{ marginTop: 6 }}>
                <Space wrap size={[2, 2]}>
                  {node.capabilities.slice(0, 4).map(c => <Tag key={c} style={{ fontSize: 10 }}>{c}</Tag>)}
                </Space>
              </div>
            )}
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// ── Gateway Health Badge ─────────────────────────────────────

const GatewayHealthBadge: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['dt-gateway-health'],
    queryFn: checkGatewayHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  if (isLoading) return <Badge status="processing" text="檢測中..." />;
  if (!data) return <Badge status="default" text="未知" />;
  return (
    <Badge
      status={data.available ? 'success' : 'error'}
      text={data.available ? `連線正常 (${data.latencyMs}ms)` : '離線'}
    />
  );
};

// ── Main Page ────────────────────────────────────────────────

const AgentDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const queryClient = useQueryClient();

  // Prefetch self-profile on mount to warm cache
  useEffect(() => {
    queryClient.prefetchQuery({
      queryKey: ['agent-self-profile'],
      queryFn: () => apiClient.post<AgentSelfProfile>(AI_ENDPOINTS.AGENT_SELF_PROFILE, {}),
      staleTime: 5 * 60_000,
    });
  }, [queryClient]);

  // Self-profile
  const { data: profile, isLoading: profileLoading, isError: profileError } = useQuery<AgentSelfProfile>({
    queryKey: ['agent-self-profile'],
    queryFn: () => apiClient.post<AgentSelfProfile>(AI_ENDPOINTS.AGENT_SELF_PROFILE, {}),
    staleTime: 5 * 60_000,
    retry: 1,
  });

  // Dashboard snapshot (for sidebar stats)
  const { data: dashboardData, isLoading: dashboardLoading } = useQuery<DashboardSnapshot>({
    queryKey: ['dt-dashboard'],
    queryFn: () => apiClient.post(DIGITAL_TWIN_ENDPOINTS.DASHBOARD, {}),
    staleTime: 5 * 60_000,
  });

  // Memoize tab items to prevent re-creation on every render
  const tabItems = useMemo(() => [
    createTabItem('chat', { icon: <MessageOutlined />, text: '對話' },
      <React.Suspense fallback={<Spin tip="載入對話..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />}>
        <RAGChatPanel embedded agentMode />
      </React.Suspense>
    ),
    createTabItem('reflection', { icon: <RadarChartOutlined />, text: '自省' },
      <React.Suspense fallback={<Spin tip="載入能力分析..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />}>
        <CapabilityRadarTab />
      </React.Suspense>
    ),
    createTabItem('evolution', { icon: <ExperimentOutlined />, text: '進化' },
      <React.Suspense fallback={<Spin tip="載入進化歷程..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />}>
        <EvolutionTab />
      </React.Suspense>
    ),
    createTabItem('topology', { icon: <ApartmentOutlined />, text: '拓撲' },
      <TopologyTab />
    ),
  ], []);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <CloudServerOutlined /> 智能體中心
          </Title>
          <Text type="secondary">
            乾坤智能體 — 自覺型 Agent 問答、自省與進化
          </Text>
        </div>
        <GatewayHealthBadge />
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={6}>
          <AgentSidebar
            profile={profile ?? defaultProfile}
            loading={profileLoading}
            error={profileError}
            dashboardData={dashboardData ?? null}
            dashboardLoading={dashboardLoading}
          />
        </Col>
        <Col xs={24} lg={18}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </Col>
      </Row>
    </div>
  );
};

export default AgentDashboardPage;
