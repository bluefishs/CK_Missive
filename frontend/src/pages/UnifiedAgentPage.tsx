/**
 * UnifiedAgentPage — 乾坤智能體統一頁面
 *
 * 雙模式：
 * - mode="user" → /agent/dashboard — 使用者模式 (7 Tab)
 * - mode="admin" → /admin/ai-assistant — 管理模式 (12 Tab)
 *
 * @version 1.0.0
 * @created 2026-04-09
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Row, Col, Typography, Tabs, Spin } from 'antd';
import {
  MessageOutlined, RadarChartOutlined,
  ApartmentOutlined, ExperimentOutlined,
  CloudServerOutlined, UnorderedListOutlined,
  ScheduleOutlined, DashboardOutlined,
  BarChartOutlined, DatabaseOutlined, HeartOutlined,
  ThunderboltOutlined, SwapOutlined,
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS, DIGITAL_TWIN_ENDPOINTS } from '../api/endpoints';
import { createTabItem } from '../components/common/DetailPage/utils';
import type { AgentSelfProfile, DashboardSnapshot } from './digitalTwin/ProfileCard';
import { defaultProfile } from './digitalTwin/ProfileCard';
import { GatewayHealthBadge } from './digitalTwin/GatewayHealthBadge';
import { MorningReportCard } from './digitalTwin/MorningReportCard';
import { TopologyTab } from './digitalTwin/TopologyTab';

// Lazy-load heavy sub-tabs
const RAGChatPanel = React.lazy(() =>
  import('../components/ai/RAGChatPanel').then(m => ({ default: m.RAGChatPanel }))
);
const DualModeChatPanel = React.lazy(() =>
  import('../components/ai/DualModeChatPanel').then(m => ({ default: m.DualModeChatPanel }))
);
const CapabilityRadarTab = React.lazy(() =>
  import('./digitalTwin/CapabilityRadarTab').then(m => ({ default: m.CapabilityRadarTab }))
);
const EvolutionTab = React.lazy(() =>
  import('./digitalTwin/EvolutionTab').then(m => ({ default: m.EvolutionTab }))
);
const TraceWaterfallTab = React.lazy(() =>
  import('./digitalTwin/TraceWaterfallTab').then(m => ({ default: m.TraceWaterfallTab }))
);
const DashboardTab = React.lazy(() =>
  import('./digitalTwin/DashboardTab').then(m => ({ default: m.DashboardTab }))
);
const DispatchProgressTab = React.lazy(() =>
  import('./digitalTwin/DispatchProgressTab').then(m => ({ default: m.DispatchProgressTab }))
);
const ProfileCard = React.lazy(() =>
  import('./digitalTwin/ProfileCard').then(m => ({ default: m.ProfileCard }))
);

// Admin-only tabs (lazy)
const AgentPerformanceTab = React.lazy(() =>
  import('../components/ai/management').then(m => ({ default: m.AgentPerformanceTab }))
);
const DataAnalyticsTab = React.lazy(() =>
  import('../components/ai/management').then(m => ({ default: m.DataAnalyticsTab }))
);
const DataPipelineTab = React.lazy(() =>
  import('../components/ai/management').then(m => ({ default: m.DataPipelineTab }))
);
const ServiceStatusTab = React.lazy(() =>
  import('../components/ai/management').then(m => ({ default: m.ServiceStatusTab }))
);

const { Title, Text } = Typography;

const suspense = (node: React.ReactNode, tip = '載入中...') => (
  <React.Suspense fallback={<Spin tip={tip} style={{ display: 'block', padding: 40, textAlign: 'center' }} />}>
    {node}
  </React.Suspense>
);

export interface UnifiedAgentPageProps {
  mode: 'user' | 'admin';
}

const UnifiedAgentPage: React.FC<UnifiedAgentPageProps> = ({ mode }) => {
  const isAdmin = mode === 'admin';
  const [activeTab, setActiveTab] = useState('chat');
  const queryClient = useQueryClient();

  // Prefetch self-profile
  useEffect(() => {
    queryClient.prefetchQuery({
      queryKey: ['agent-self-profile'],
      queryFn: () => apiClient.post<AgentSelfProfile>(AI_ENDPOINTS.AGENT_SELF_PROFILE, {}),
      staleTime: 5 * 60_000,
    });
  }, [queryClient]);

  const { data: profile, isLoading: profileLoading, isError: profileError, refetch } = useQuery<AgentSelfProfile>({
    queryKey: ['agent-self-profile'],
    queryFn: () => apiClient.post<AgentSelfProfile>(AI_ENDPOINTS.AGENT_SELF_PROFILE, {}),
    staleTime: 5 * 60_000,
    retry: 1,
  });

  const { data: dashboardData, isLoading: dashboardLoading } = useQuery<DashboardSnapshot>({
    queryKey: ['dt-dashboard'],
    queryFn: () => apiClient.post(DIGITAL_TWIN_ENDPOINTS.DASHBOARD, {}),
    staleTime: 5 * 60_000,
  });

  const tabItems = useMemo(() => {
    const items = [
      // ── 核心 Tab（兩模式共用）──
      createTabItem('chat', { icon: <MessageOutlined />, text: '對話' },
        suspense(<RAGChatPanel embedded agentMode />, '載入對話...')
      ),
      createTabItem('reflection', { icon: <RadarChartOutlined />, text: '自省' },
        suspense(<CapabilityRadarTab />, '載入能力分析...')
      ),
      createTabItem('trace', { icon: <UnorderedListOutlined />, text: '追蹤' },
        suspense(<TraceWaterfallTab />, '載入追蹤...')
      ),
      createTabItem('dispatch', { icon: <ScheduleOutlined />, text: '派工' },
        suspense(<DispatchProgressTab />, '載入派工進度...')
      ),
      createTabItem('dashboard', { icon: <DashboardOutlined />, text: '儀表板' },
        suspense(<DashboardTab />, '載入儀表板...')
      ),
      // ── 進階 Tab（兩模式共用但使用者模式可選顯示）──
      createTabItem('evolution', { icon: <ExperimentOutlined />, text: '進化' },
        suspense(<EvolutionTab />, '載入進化歷程...')
      ),
      createTabItem('topology', { icon: <ApartmentOutlined />, text: '拓撲' },
        <TopologyTab />
      ),
    ];

    // ── 管理專用 Tab ──
    if (isAdmin) {
      items.push(
        createTabItem('agent-perf', { icon: <ThunderboltOutlined />, text: 'Agent 效能' },
          suspense(<AgentPerformanceTab />)
        ),
        createTabItem('analytics', { icon: <BarChartOutlined />, text: '數據分析' },
          suspense(<DataAnalyticsTab />)
        ),
        createTabItem('pipeline', { icon: <DatabaseOutlined />, text: '資料管線' },
          suspense(<DataPipelineTab />)
        ),
        createTabItem('status', { icon: <HeartOutlined />, text: '服務狀態' },
          suspense(<ServiceStatusTab />)
        ),
        createTabItem('dual-mode', { icon: <SwapOutlined />, text: 'DualMode 比較' },
          suspense(<DualModeChatPanel />, '載入雙模式...')
        ),
      );
    }

    return items;
  }, [isAdmin]);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <CloudServerOutlined /> 乾坤智能體{isAdmin ? ' — 管理模式' : ''}
          </Title>
          <Text type="secondary">
            {isAdmin
              ? '問答、自省、進化、效能監控、資料管線與服務狀態'
              : '自覺型 AI 助理 — 問答、自省、進化與系統監控'}
          </Text>
        </div>
        <GatewayHealthBadge />
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={6}>
          <React.Suspense fallback={<Spin style={{ display: 'block', padding: 20 }} />}>
            <ProfileCard
              compact={!isAdmin}
              profile={profile ?? defaultProfile}
              loading={profileLoading}
              error={profileError}
              onRetry={() => refetch()}
              dashboardData={dashboardData ?? null}
              dashboardLoading={dashboardLoading}
            />
          </React.Suspense>
          {isAdmin && <MorningReportCard />}
        </Col>
        <Col xs={24} lg={18}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </Col>
      </Row>
    </div>
  );
};

export default UnifiedAgentPage;
