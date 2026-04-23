/**
 * MemoryDashboardPage — Memory Wiki 統一儀表板
 *
 * Phase 5 Slice 3 — 整合 diary / patterns / proposals / autobiography 四個分頁，
 * 頂部以 ClickableStatCard 顯示 Memory 總覽統計。
 *
 * 對應後端 /ai/memory/* 13 端點（皆需登入；批准/回滾需 admin）。
 */
import React, { lazy, Suspense, useState } from 'react';
import { Spin, Tabs, Typography } from 'antd';
import {
  BookOutlined,
  BranchesOutlined,
  CrownOutlined,
  DeploymentUnitOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

import { useMemoryStats } from '../hooks/useMemoryData';
import { MemoryStatsRow } from '../components/memory/MemoryStatsRow';

const DiaryTab = lazy(() => import('./memoryWiki/DiaryTab'));
const PatternsTab = lazy(() => import('./memoryWiki/PatternsTab'));
const ProposalsTab = lazy(() => import('./memoryWiki/ProposalsTab'));
const AutobiographyTab = lazy(() => import('./memoryWiki/AutobiographyTab'));
const SkillNebulaTab = lazy(() => import('./memoryWiki/SkillNebulaTab'));

const MemoryDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('diary');
  const { data: stats, isLoading: loadingStats } = useMemoryStats();

  const fallback = <Spin style={{ display: 'block', margin: '40px auto' }} />;

  return (
    <div style={{ padding: '0 4px' }}>
      <Typography.Title level={4} style={{ marginBottom: 4 }}>
        記憶中樞 Memory Wiki
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
        助理自我記憶系統（內在心智）— 每日日記 / 成功模式 / 結晶提案 / 週自傳。
        與 LLM Wiki（業務領域知識）為不同世界觀，見 ADR-0031。
      </Typography.Paragraph>

      {/* Stats — 共用 MemoryStatsRow (ADR-0031 Phase 3) */}
      <div style={{ marginBottom: 16 }}>
        <MemoryStatsRow stats={stats} loading={loadingStats} colSpans={{ xs: 12, md: 6, lg: 4 }} />
      </div>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'diary',
            label: <span><BookOutlined /> 日記</span>,
            children: <Suspense fallback={fallback}><DiaryTab /></Suspense>,
          },
          {
            key: 'patterns',
            label: <span><BranchesOutlined /> 模式 / 教訓</span>,
            children: <Suspense fallback={fallback}><PatternsTab /></Suspense>,
          },
          {
            key: 'proposals',
            label: <span><CrownOutlined /> 提案 / Crystal</span>,
            children: <Suspense fallback={fallback}><ProposalsTab /></Suspense>,
          },
          {
            key: 'autobiography',
            label: <span><HistoryOutlined /> 週自傳</span>,
            children: <Suspense fallback={fallback}><AutobiographyTab /></Suspense>,
          },
          {
            key: 'nebula',
            label: <span><DeploymentUnitOutlined /> 技能星雲</span>,
            children: <Suspense fallback={fallback}><SkillNebulaTab /></Suspense>,
          },
        ]}
      />
    </div>
  );
};

export default MemoryDashboardPage;
