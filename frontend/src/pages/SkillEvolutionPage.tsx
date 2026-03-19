/**
 * 技能演化樹 — 與平台白底設計一致的互動式視覺化
 *
 * @version 3.0.0 — 白底主題重構
 */

import React, { useState, useMemo } from 'react';
import { Card, Typography, Spin, Flex, Tag, Space, Badge } from 'antd';
import { RiseOutlined, ApartmentOutlined, NodeIndexOutlined, MergeCellsOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { AI_ENDPOINTS } from '../api/endpoints';
import { EvolutionGraph } from './skillEvolution/EvolutionGraph';
import type { SkillEvolutionData, ForceGraphData, SkillNode, CategoryInfo } from './skillEvolution';

const { Title, Text } = Typography;

const fetchSkillEvolution = async (): Promise<SkillEvolutionData> => {
  return apiClient.post<SkillEvolutionData>(AI_ENDPOINTS.GRAPH_SKILL_EVOLUTION, {});
};

/** 左側技能列表（內嵌，不另開檔案） */
const SkillList: React.FC<{
  nodes: SkillNode[];
  categories: Record<string, CategoryInfo>;
  onSelect: (id: number | null) => void;
  selected: number | null;
}> = ({ nodes, categories, onSelect, selected }) => {
  const grouped = useMemo(() => {
    const map = new Map<string, SkillNode[]>();
    for (const n of nodes) {
      const list = map.get(n.category) || [];
      list.push(n);
      map.set(n.category, list);
    }
    return map;
  }, [nodes]);

  return (
    <div style={{ width: 220, borderRight: '1px solid #f0f0f0', overflowY: 'auto', padding: '8px 0' }}>
      {Array.from(grouped.entries()).map(([cat, skills]) => {
        const info = categories[cat];
        return (
          <div key={cat} style={{ marginBottom: 8 }}>
            <Flex align="center" gap={6} style={{ padding: '4px 12px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: info?.color || '#999', display: 'inline-block' }} />
              <Text strong style={{ fontSize: 12, color: '#333' }}>{info?.label || cat}</Text>
              <Badge count={skills.length} style={{ backgroundColor: '#f0f0f0', color: '#666', fontSize: 10 }} />
            </Flex>
            {skills.map(s => (
              <div
                key={s.id}
                onClick={() => onSelect(selected === s.id ? null : s.id)}
                style={{
                  padding: '3px 12px 3px 26px',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: s.source === 'planned' ? '#bbb' : '#555',
                  background: selected === s.id ? '#e6f4ff' : 'transparent',
                  borderRight: selected === s.id ? '2px solid #1890ff' : 'none',
                }}
              >
                <Flex align="center" justify="space-between">
                  <Text ellipsis style={{ fontSize: 12, maxWidth: 140, color: s.source === 'planned' ? '#bbb' : '#333' }}>
                    {s.name}
                  </Text>
                  <Tag
                    color={s.source === 'planned' ? 'default' : s.source === 'merged' ? 'gold' : undefined}
                    style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}
                  >
                    {s.version}
                  </Tag>
                </Flex>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};

const SkillEvolutionPage: React.FC = () => {
  const [highlightNodeId, setHighlightNodeId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['skill-evolution'],
    queryFn: fetchSkillEvolution,
    staleTime: 5 * 60 * 1000,
  });

  const graphData: ForceGraphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map(n => ({ ...n })),
      links: data.edges.map(e => ({ source: e.source, target: e.target, type: e.type, label: e.label })),
    };
  }, [data]);

  if (isLoading || !data) {
    return <Flex align="center" justify="center" style={{ height: 400 }}><Spin size="large" /></Flex>;
  }

  const { stats } = data;

  return (
    <div style={{ padding: 16 }}>
      {/* 標題列 */}
      <Flex align="center" justify="space-between" style={{ marginBottom: 12 }}>
        <Space size={12}>
          <RiseOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <Title level={4} style={{ margin: 0 }}>技能演化樹</Title>
        </Space>
        <Space size={16}>
          <Flex align="center" gap={4}>
            <ApartmentOutlined style={{ color: '#52c41a' }} />
            <Text type="secondary">{stats.total} 技能</Text>
          </Flex>
          <Flex align="center" gap={4}>
            <NodeIndexOutlined style={{ color: '#1890ff' }} />
            <Text type="secondary">{stats.evolution_count} 演化</Text>
          </Flex>
          <Flex align="center" gap={4}>
            <MergeCellsOutlined style={{ color: '#fa8c16' }} />
            <Text type="secondary">{stats.merge_count} 融合</Text>
          </Flex>
        </Space>
      </Flex>

      {/* 主體 */}
      <Card
        size="small"
        styles={{ body: { padding: 0, display: 'flex', height: 'calc(100vh - 180px)', overflow: 'hidden' } }}
      >
        {/* 左側列表 */}
        <SkillList
          nodes={data.nodes}
          categories={data.categories}
          onSelect={setHighlightNodeId}
          selected={highlightNodeId}
        />

        {/* 圖譜區 */}
        <div style={{ flex: 1, position: 'relative', background: '#fafbfc' }}>
          <EvolutionGraph
            graphData={graphData}
            categories={data.categories}
            highlightNodeId={highlightNodeId}
          />

          {/* 右下圖例 */}
          <div style={{
            position: 'absolute', bottom: 12, right: 12,
            background: 'rgba(255,255,255,0.95)', border: '1px solid #e8e8e8',
            borderRadius: 6, padding: '8px 12px', fontSize: 11,
          }}>
            <Flex vertical gap={3}>
              {Object.entries(data.categories).map(([key, info]) => {
                const cnt = data.nodes.filter(n => n.category === key).length;
                if (!cnt) return null;
                return (
                  <Flex key={key} align="center" gap={6}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: info.color }} />
                    <Text style={{ fontSize: 11, color: '#555' }}>{info.label}</Text>
                    <Text style={{ fontSize: 10, color: '#999', marginLeft: 'auto' }}>{cnt}</Text>
                  </Flex>
                );
              })}
              <div style={{ borderTop: '1px solid #f0f0f0', marginTop: 4, paddingTop: 4 }}>
                <Flex align="center" gap={4}><span style={{ width: 14, height: 2, background: '#52c41a' }} /> <Text style={{ fontSize: 10 }}>演化</Text></Flex>
                <Flex align="center" gap={4}><span style={{ width: 14, height: 0, borderTop: '2px dashed #fa8c16' }} /> <Text style={{ fontSize: 10 }}>融合</Text></Flex>
                <Flex align="center" gap={4}><span style={{ width: 14, height: 0, borderTop: '2px dashed #d9d9d9' }} /> <Text style={{ fontSize: 10 }}>規劃中</Text></Flex>
              </div>
            </Flex>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default SkillEvolutionPage;
