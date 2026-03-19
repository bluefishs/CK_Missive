/**
 * Skill Evolution Page
 *
 * Interactive skill evolution tree visualization with force-directed graph.
 * Displays skill nodes grouped by category with evolution/merge/planned connections.
 *
 * @version 1.0.0
 */

import React, { useMemo, useState } from 'react';
import { Typography, Spin, Alert, Flex } from 'antd';
import { RiseOutlined, ReloadOutlined } from '@ant-design/icons';
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

/** Fetch skill evolution data */
const fetchSkillEvolution = async (): Promise<SkillEvolutionData> => {
  return apiClient.post<SkillEvolutionData>(AI_ENDPOINTS.GRAPH_SKILL_EVOLUTION, {});
};

const SkillEvolutionPage: React.FC = () => {
  const [highlightNodeId, setHighlightNodeId] = useState<number | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['skill-evolution'],
    queryFn: fetchSkillEvolution,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  /** Transform API data to force graph format */
  const graphData: ForceGraphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map(n => ({ ...n })),
      links: data.edges.map(e => ({
        source: e.source,
        target: e.target,
        type: e.type,
        label: e.label,
      })),
    };
  }, [data]);

  if (isLoading) {
    return (
      <Flex align="center" justify="center" style={{ height: 'calc(100vh - 120px)' }}>
        <Spin size="large" tip="Loading skill evolution data..." />
      </Flex>
    );
  }

  if (isError || !data) {
    return (
      <Flex vertical align="center" justify="center" gap={16} style={{ height: 'calc(100vh - 120px)', padding: 24 }}>
        <Alert
          type="error"
          message="Failed to load skill evolution data"
          description={error instanceof Error ? error.message : 'Unknown error'}
          showIcon
          action={
            <a onClick={() => refetch()}>
              <ReloadOutlined /> Retry
            </a>
          }
        />
      </Flex>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
      {/* Header */}
      <Flex
        align="center"
        gap={12}
        style={{
          padding: '10px 16px',
          background: '#0d0d1f',
          borderBottom: '1px solid #303050',
          flexShrink: 0,
        }}
      >
        <RiseOutlined style={{ fontSize: 20, color: '#50c878' }} />
        <Title level={4} style={{ margin: 0, color: '#e0e0e0' }}>
          Skill Evolution Tree
        </Title>
        <Text style={{ color: '#666', fontSize: 12, marginLeft: 8 }}>
          {data.stats.total} skills | {data.stats.evolution_count} evolutions | {data.stats.merge_count} fusions
        </Text>
      </Flex>

      {/* Body: Left panel + Graph area */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        <SkillListPanel
          nodes={data.nodes}
          categories={data.categories}
          onSkillClick={setHighlightNodeId}
        />

        <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
          <EvolutionGraph
            graphData={graphData}
            categories={data.categories}
            highlightNodeId={highlightNodeId}
          />
          <LegendPanel categories={data.categories} nodes={data.nodes} />
          <StatsPanel stats={data.stats} />
        </div>
      </div>
    </div>
  );
};

export default SkillEvolutionPage;
