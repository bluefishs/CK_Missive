/**
 * 技能演化樹 — 互動式視覺化
 *
 * 展示乾坤智能體的技能節點、演化路徑、融合關係。
 * 深色主題 + force-directed graph + 分類篩選面板。
 *
 * @version 2.0.0
 */

import React, { useState } from 'react';
import { Typography, Spin, Flex } from 'antd';
import { RiseOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS } from '../api/endpoints';
import {
  SkillListPanel,
  EvolutionGraph,
  StatsPanel,
  LegendPanel,
} from './skillEvolution';
import type { SkillEvolutionData, ForceGraphData } from './skillEvolution';

const { Title, Text } = Typography;

const fetchSkillEvolution = async (): Promise<SkillEvolutionData> => {
  return apiClient.post<SkillEvolutionData>(AI_ENDPOINTS.GRAPH_SKILL_EVOLUTION, {});
};

const SkillEvolutionPage: React.FC = () => {
  const [highlightNodeId, setHighlightNodeId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['skill-evolution'],
    queryFn: fetchSkillEvolution,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const graphData: ForceGraphData = data
    ? {
        nodes: data.nodes.map(n => ({ ...n })),
        links: data.edges.map(e => ({
          source: e.source,
          target: e.target,
          type: e.type,
          label: e.label,
        })),
      }
    : { nodes: [], links: [] };

  if (isLoading || !data) {
    return (
      <Flex align="center" justify="center" style={{ height: 'calc(100vh - 120px)', background: '#0d0d1f' }}>
        <Spin size="large" />
      </Flex>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', background: '#0d0d1f', overflow: 'hidden' }}>
      {/* 頂部標題列 */}
      <Flex
        align="center"
        gap={12}
        style={{
          padding: '8px 16px',
          background: 'rgba(13,13,31,0.95)',
          borderBottom: '1px solid #252545',
          flexShrink: 0,
        }}
      >
        <RiseOutlined style={{ fontSize: 18, color: '#50c878' }} />
        <Title level={5} style={{ margin: 0, color: '#e0e0e0', fontSize: 15 }}>
          技能演化樹
        </Title>
        <Text style={{ color: '#555', fontSize: 12 }}>
          {data.stats.total} 技能 · {data.stats.active} 啟用 · {data.stats.evolution_count} 演化 · {data.stats.merge_count} 融合
        </Text>
      </Flex>

      {/* 主體：左面板 + 圖譜區 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* 左側技能列表 */}
        <SkillListPanel
          nodes={data.nodes}
          categories={data.categories}
          onSkillClick={setHighlightNodeId}
        />

        {/* 圖譜區域（滿版） */}
        <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
          <EvolutionGraph
            graphData={graphData}
            categories={data.categories}
            highlightNodeId={highlightNodeId}
          />

          {/* 左下角圖例 (疊加在圖譜上) */}
          <LegendPanel categories={data.categories} nodes={data.nodes} />

          {/* 右下角統計 (疊加在圖譜上) */}
          <StatsPanel stats={data.stats} />
        </div>
      </div>
    </div>
  );
};

export default SkillEvolutionPage;
