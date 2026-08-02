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
  RadarChartOutlined,
  ApartmentOutlined, ExperimentOutlined,
  CloudServerOutlined, UnorderedListOutlined,
  ScheduleOutlined, DashboardOutlined,
  BarChartOutlined, DatabaseOutlined, HeartOutlined,
  ThunderboltOutlined, SwapOutlined,
  ControlOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS, DIGITAL_TWIN_ENDPOINTS } from '../api/endpoints';
import { createTabItem } from '../components/common/DetailPage/utils';
import type { AgentSelfProfile, DashboardSnapshot } from './digitalTwin/ProfileCard';
import { defaultProfile } from './digitalTwin/ProfileCard';
import { GatewayHealthBadge } from './digitalTwin/GatewayHealthBadge';
import { TopologyTab } from './digitalTwin/TopologyTab';

// Lazy-load heavy sub-tabs
// 2026-06-02 kunge tab 整併：RAGChatPanel 移除（ops「對話」與主 /kunge/chat 純重複）。
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
const MorningReportOpsTab = React.lazy(() =>
  import('./digitalTwin/MorningReportOpsTab').then(m => ({ default: m.MorningReportOpsTab }))
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
  // 2026-06-02 kunge tab 整併：移除 ops「對話」(與主 /kunge/chat 之 RAGChatPanel 純重複)。
  // 2026-08-02 分組（owner：資訊過多、營運核心雜亂）：11 個扁平 tab 收斂為
  // 外層三組「營運／系統／AI 診斷」，預設停在營運，首屏即是每天要看的東西。
  const [activeGroup, setActiveGroup] = useState('ops-core');
  const [activeTab, setActiveTab] = useState('morning-report');
  const [systemTab, setSystemTab] = useState('dashboard');
  const [aiTab, setAiTab] = useState('reflection');
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

  // ── 第一層：三組（營運 / 系統 / AI 診斷）──
  // 分組準則＝「這個資訊是誰每天要看的」：
  //   營運    ＝ 每天都要看的業務狀態（晨報推播、派工進度）
  //   系統    ＝ 出事時才查的機器狀態（儀表板、服務、管線、數據）
  //   AI 診斷 ＝ 只有在懷疑 agent 行為時才看（自省、追蹤、健康進化、拓撲、效能、DualMode）
  const groupItems = useMemo(() => {
    const opsCore = [
      createTabItem('morning-report', { icon: <FileTextOutlined />, text: '晨報與推播' },
        suspense(<MorningReportOpsTab />, '載入晨報與推播...')
      ),
      createTabItem('dispatch', { icon: <ScheduleOutlined />, text: '派工進度' },
        suspense(<DispatchProgressTab />, '載入派工進度...')
      ),
    ];

    const system = [
      createTabItem('dashboard', { icon: <DashboardOutlined />, text: '儀表板' },
        suspense(<DashboardTab />, '載入儀表板...')
      ),
    ];
    if (isAdmin) {
      system.push(
        createTabItem('status', { icon: <HeartOutlined />, text: '服務狀態' },
          suspense(<ServiceStatusTab />)
        ),
        createTabItem('pipeline', { icon: <DatabaseOutlined />, text: '資料管線' },
          suspense(<DataPipelineTab />)
        ),
        createTabItem('analytics', { icon: <BarChartOutlined />, text: '數據分析' },
          suspense(<DataAnalyticsTab />)
        ),
      );
    }

    // ADR-0031 Phase 5：`進化` → `健康進化`（Agent 健康視角，對比坤哥「結晶進化」）
    const ai = [
      createTabItem('reflection', { icon: <RadarChartOutlined />, text: '自省' },
        suspense(<CapabilityRadarTab />, '載入能力分析...')
      ),
      createTabItem('trace', { icon: <UnorderedListOutlined />, text: '追蹤' },
        suspense(<TraceWaterfallTab />, '載入追蹤...')
      ),
      createTabItem('evolution', { icon: <ExperimentOutlined />, text: '健康進化' },
        suspense(<EvolutionTab />, '載入 Agent 健康進化...')
      ),
      createTabItem('topology', { icon: <ApartmentOutlined />, text: '拓撲' },
        <TopologyTab />
      ),
    ];
    if (isAdmin) {
      ai.push(
        createTabItem('agent-perf', { icon: <ThunderboltOutlined />, text: 'Agent 效能' },
          suspense(<AgentPerformanceTab />)
        ),
        createTabItem('dual-mode', { icon: <SwapOutlined />, text: 'DualMode 比較' },
          suspense(<DualModeChatPanel />, '載入雙模式...')
        ),
      );
    }

    return [
      {
        key: 'ops-core',
        label: <span><ControlOutlined /> 營運</span>,
        children: <Tabs activeKey={activeTab} onChange={setActiveTab} items={opsCore} />,
      },
      {
        key: 'system',
        label: <span><CloudServerOutlined /> 系統</span>,
        children: <Tabs activeKey={systemTab} onChange={setSystemTab} items={system} />,
      },
      {
        key: 'ai',
        label: <span><RadarChartOutlined /> AI 診斷</span>,
        children: <Tabs activeKey={aiTab} onChange={setAiTab} items={ai} />,
      },
    ];
  }, [isAdmin, activeTab, systemTab, aiTab]);

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
          {/* 2026-08-02：原本的晨報小卡已移除 —— 同一份資訊不放兩處，
              完整版（含派送狀態、月配額、快照趨勢）在「營運 › 晨報與推播」。 */}
        </Col>
        <Col xs={24} lg={18}>
          <Tabs
            type="card"
            activeKey={activeGroup}
            onChange={setActiveGroup}
            items={groupItems}
          />
        </Col>
      </Row>
    </div>
  );
};

export default UnifiedAgentPage;
