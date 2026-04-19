/**
 * MemoryDashboardPage — Memory Wiki 統一儀表板
 *
 * Phase 5 Slice 3 — 整合 diary / patterns / proposals / autobiography 四個分頁，
 * 頂部以 ClickableStatCard 顯示 Memory 總覽統計。
 *
 * 對應後端 /ai/memory/* 13 端點（皆需登入；批准/回滾需 admin）。
 */
import React, { lazy, Suspense, useState } from 'react';
import { Card, Col, Row, Spin, Statistic, Tabs, Typography } from 'antd';
import {
  BookOutlined,
  BranchesOutlined,
  BulbOutlined,
  CrownOutlined,
  DeploymentUnitOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

import { useMemoryStats } from '../hooks/useMemoryData';

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
        Memory Wiki
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
        助理自我記憶系統 — 每日日記 / 成功模式 / 結晶提案 / 週自傳。
      </Typography.Paragraph>

      {/* Stats */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6} lg={4}>
          <Card size="small" loading={loadingStats}>
            <Statistic
              title="日記天數"
              value={stats?.diary_days ?? 0}
              prefix={<BookOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} md={6} lg={4}>
          <Card size="small" loading={loadingStats}>
            <Statistic
              title="成功模式"
              value={stats?.patterns_total ?? 0}
              prefix={<BranchesOutlined />}
              suffix={
                <span style={{ fontSize: 12, color: '#52c41a' }}>
                  {stats?.crystallization_candidates ?? 0} 候選
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={12} md={6} lg={4}>
          <Card size="small" loading={loadingStats}>
            <Statistic
              title="失敗教訓（active）"
              value={stats?.failures_active ?? 0}
              prefix={<BulbOutlined />}
              valueStyle={{ color: (stats?.failures_active ?? 0) > 0 ? '#fa541c' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6} lg={4}>
          <Card size="small" loading={loadingStats}>
            <Statistic
              title="待決提案"
              value={stats?.proposals_pending ?? 0}
              prefix={<CrownOutlined />}
              valueStyle={{ color: (stats?.proposals_pending ?? 0) > 0 ? '#fa8c16' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6} lg={4}>
          <Card size="small" loading={loadingStats}>
            <Statistic title="已套用 Crystal" value={stats?.crystals_total ?? 0} />
          </Card>
        </Col>
        <Col xs={12} md={6} lg={4}>
          <Card size="small" loading={loadingStats}>
            <Statistic
              title="週自傳累積"
              value={stats?.autobiographies_total ?? 0}
              prefix={<HistoryOutlined />}
            />
          </Card>
        </Col>
      </Row>

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
