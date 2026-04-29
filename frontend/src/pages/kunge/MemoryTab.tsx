/**
 * 坤哥 — 記憶圖譜板塊（v2.0 v5.10.2 Phase 3：嵌入完整 5 sub-tabs）
 *
 * 三層記憶心智架構：
 *   - 身份層（SOUL.md，由 IdentityTab 呈現）
 *   - 世界觀層（wiki/entities, wiki/topics 220 nodes / KG 2504 entities）
 *   - 自我觀層（wiki/memory/ diary / patterns / autobiographies）— 本 Tab 內呈現
 *
 * v2.0 變更（ADR-0031 落實）：
 *   原本只有導引卡 → 改為內嵌 MemoryDashboardPage 的 5 sub-tabs，
 *   不再讓使用者跳出 /kunge 才能看完整記憶。
 *
 * @version 2.0.0 — kunge 唯一入口落實
 */

import React, { lazy, Suspense, useState } from 'react';
import { Card, Typography, Tabs, Spin, Alert, Space, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  BookOutlined,
  BranchesOutlined,
  CrownOutlined,
  DeploymentUnitOutlined,
  HistoryOutlined,
  DatabaseOutlined,
  NodeIndexOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useMemoryStats } from '../../hooks/useMemoryData';
import { MemoryStatsRow } from '../../components/memory/MemoryStatsRow';

const { Title, Paragraph, Text } = Typography;

// 共用 MemoryDashboardPage 的 5 個子 tabs（不重複實作，保 single source of truth）
const DiaryTab = lazy(() => import('../memoryWiki/DiaryTab'));
const PatternsTab = lazy(() => import('../memoryWiki/PatternsTab'));
const ProposalsTab = lazy(() => import('../memoryWiki/ProposalsTab'));
const AutobiographyTab = lazy(() => import('../memoryWiki/AutobiographyTab'));
const SkillNebulaTab = lazy(() => import('../memoryWiki/SkillNebulaTab'));

const fallback = <Spin style={{ display: 'block', margin: '40px auto' }} />;

export const MemoryTab: React.FC = () => {
  const navigate = useNavigate();
  const { data: stats, isLoading } = useMemoryStats();
  const [activeTab, setActiveTab] = useState('diary');

  return (
    <div>
      <Card bordered={false}>
        <Title level={3} style={{ marginTop: 0 }}>
          <DatabaseOutlined /> 記憶圖譜
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 15 }}>
          我的心智由三層 wiki 組成：<Text strong>身份層</Text>（慢變，我是誰）
          · <Text strong>世界觀層</Text>（中速，我知道的世界）
          · <Text strong>自我觀層</Text>（快變，我學到的經驗）。
        </Paragraph>
        <Alert
          type="info"
          showIcon
          message="節點即世界觀"
          description="每個 Wiki 節點、每筆 KG 實體、每個結晶 pattern，都是公司時間複利的一個具象化片段。"
        />
      </Card>

      <Card bordered={false} style={{ marginTop: 16 }} title="自我觀層統計">
        <MemoryStatsRow stats={stats} loading={isLoading} />
      </Card>

      {/* v2.0：嵌入 5 sub-tabs，不再讓使用者跳出 /kunge */}
      <Card bordered={false} style={{ marginTop: 16 }}>
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
      </Card>

      {/* 進階探索（外部 Wiki / KG hub） */}
      <Card bordered={false} style={{ marginTop: 16 }} size="small">
        <Space size="middle" wrap>
          <Text type="secondary" style={{ fontSize: 13 }}>進階探索：</Text>
          <Button
            type="link"
            size="small"
            icon={<NodeIndexOutlined />}
            onClick={() => navigate('/ai/wiki')}
          >
            LLM Wiki Force-Graph 220 節點
            <ArrowRightOutlined style={{ marginLeft: 4 }} />
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DatabaseOutlined />}
            onClick={() => navigate('/ai/knowledge-graph')}
          >
            知識圖譜 Hub 2,504 entities
            <ArrowRightOutlined style={{ marginLeft: 4 }} />
          </Button>
        </Space>
      </Card>

      <Card
        bordered={false}
        style={{ marginTop: 16, textAlign: 'center', background: 'transparent' }}
      >
        <Paragraph italic type="secondary" style={{ margin: 0 }}>
          「每次互動都是公司的時間複利，捨棄記憶等於捨棄資產。」
        </Paragraph>
        <Paragraph type="secondary" style={{ margin: 0, fontSize: 12 }}>
          — 坤哥三信念 · 記憶即資產
        </Paragraph>
      </Card>
    </div>
  );
};

export default MemoryTab;
