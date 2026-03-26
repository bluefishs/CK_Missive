/**
 * 數位分身展示頁面 v2.0
 *
 * Tab 架構：對話 / 能力概覽 / 系統拓撲
 * 左側 ProfileCard + 右側 Tab 內容
 *
 * @version 2.0.0
 * @created 2026-03-23
 * @updated 2026-03-25 — Tab 化重構 + Dashboard API 整合
 */

import React, { useState } from 'react';
import { Row, Col, Typography, Badge, Tabs, Card, Alert, Spin, Tag, Space } from 'antd';
import {
  MessageOutlined, RadarChartOutlined,
  ApartmentOutlined, DashboardOutlined, UnorderedListOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS } from '../api/endpoints';
import { checkGatewayHealth, getAgentTopology } from '../api/digitalTwin';
import { DualModeChatPanel } from '../components/ai/DualModeChatPanel';
import { ProfileCard, defaultProfile } from './digitalTwin/ProfileCard';
import { CapabilityRadarTab } from './digitalTwin/CapabilityRadarTab';
import { TraceWaterfallTab } from './digitalTwin/TraceWaterfallTab';
import { DashboardTab } from './digitalTwin/DashboardTab';
import type { AgentSelfProfile } from './digitalTwin/ProfileCard';

const { Title, Text } = Typography;

// ── Gateway Health Badge ──────────────────────────────────

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
      text={data.available ? `Gateway 連線正常 (${data.latencyMs}ms)` : `Gateway 離線: ${data.message ?? '無回應'}`}
    />
  );
};

// ── Topology Tab ──────────────────────────────────────────

const TopologyTab: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dt-topology'],
    queryFn: getAgentTopology,
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Spin tip="載入拓撲圖..." style={{ display: 'block', padding: 40, textAlign: 'center' }} />;
  if (isError) return <Alert type="warning" showIcon title="拓撲資料載入失敗" />;

  const nodes = (data?.nodes ?? []) as Array<{ id: string; label: string; type: string; status: string; project: string; capabilities?: string[] }>;

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

// ── Main Page ─────────────────────────────────────────────

const DigitalTwinPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('chat');

  const { data: profile, isLoading: profileLoading, isError: profileError, refetch: refetchProfile } = useQuery<AgentSelfProfile>({
    queryKey: ['agent-self-profile'],
    queryFn: () => apiClient.post<AgentSelfProfile>(AI_ENDPOINTS.AGENT_SELF_PROFILE, {}),
    staleTime: 5 * 60_000,
    retry: 1,
  });

  const tabItems = [
    { key: 'chat', label: <span><MessageOutlined /> 對話</span>, children: <DualModeChatPanel /> },
    { key: 'capability', label: <span><RadarChartOutlined /> 能力雷達</span>, children: <CapabilityRadarTab /> },
    { key: 'trace', label: <span><UnorderedListOutlined /> 查詢軌跡</span>, children: <TraceWaterfallTab /> },
    { key: 'dashboard', label: <span><DashboardOutlined /> 儀表板</span>, children: <DashboardTab /> },
    { key: 'topology', label: <span><ApartmentOutlined /> 系統拓撲</span>, children: <TopologyTab /> },
  ];

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><DashboardOutlined /> 數位分身</Title>
          <Text type="secondary">NemoClaw 跨專案智能協作引擎 — 即時問答與能力展示</Text>
        </div>
        <GatewayHealthBadge />
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={7}>
          <ProfileCard
            profile={profile ?? defaultProfile}
            loading={profileLoading}
            error={profileError}
            onRetry={() => refetchProfile()}
          />
        </Col>
        <Col xs={24} lg={17}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </Col>
      </Row>
    </div>
  );
};

export default DigitalTwinPage;
