/**
 * Skills Capability Map Tab
 *
 * Renders the skills/agents/tools/services/commands as a force-directed graph
 * using the existing KnowledgeGraph component infrastructure.
 *
 * @version 1.0.0
 * @created 2026-03-19
 */

import React, { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Spin, Space, Tag, Typography, Card, Descriptions } from 'antd';
import { CloseOutlined } from '@ant-design/icons';

import { aiApi } from '../../api/ai';
import { KnowledgeGraph } from '../../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../../components/ai/KnowledgeGraph';
import { GRAPH_NODE_CONFIG } from '../../config/graphNodeConfig';

const { Text } = Typography;

/** Legend item for the skills map */
const LEGEND_ITEMS = [
  { type: 'domain',  label: '領域',  color: '#f5222d' },
  { type: 'skill',   label: '技能',  color: '#1890ff' },
  { type: 'agent',   label: '代理',  color: '#52c41a' },
  { type: 'tool',    label: '工具',  color: '#faad14' },
  { type: 'service', label: '服務',  color: '#722ed1' },
  { type: 'command', label: '指令',  color: '#13c2c2' },
] as const;

/** Map node type to display label */
const TYPE_LABELS: Record<string, string> = {
  layer: '能力分層',
  capability: '核心能力',
  skill: '具體技能',
  future: '演進方向',
  domain: '領域',
  agent: '代理',
  tool: '工具',
  service: '服務',
  command: '指令',
};

/** Derive a maturity description from mention_count encoding */
function getMaturityLabel(mentionCount: number | null | undefined): string | null {
  if (mentionCount == null) return null;
  if (mentionCount >= 100) return '成熟 (5/5)';
  if (mentionCount >= 80) return '穩定 (4/5)';
  if (mentionCount >= 60) return '可用 (3/5)';
  if (mentionCount >= 40) return '實驗 (2/5)';
  if (mentionCount >= 20) return '規劃 (1/5)';
  return null;
}

interface SelectedSkill {
  id: string;
  label: string;
  type: string;
}

const SkillsMapTab: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [selectedSkill, setSelectedSkill] = useState<SelectedSkill | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      if (w > 0) setContainerWidth(w);
    };
    measure();
    const observer = new ResizeObserver(() => measure());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { data: graphData, isLoading, refetch } = useQuery({
    queryKey: ['skills-capability-map'],
    queryFn: async () => {
      const result = await aiApi.getSkillsMap();
      if (result && result.nodes && result.nodes.length > 0) {
        return { nodes: result.nodes, edges: result.edges } as ExternalGraphData;
      }
      return null;
    },
    staleTime: 5 * 60_000, // 5 min cache (static data)
  });

  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  const handleNodeClick = useCallback((node: { id: string; label: string; type: string }) => {
    setSelectedSkill((prev) => (prev?.id === node.id ? null : node));
  }, []);

  /** Find the full node data for the selected skill to get mention_count */
  const selectedNodeData = useMemo(() => {
    if (!selectedSkill || !graphData) return null;
    return graphData.nodes.find((n) => n.id === selectedSkill.id) ?? null;
  }, [selectedSkill, graphData]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 500 }}>
        <Spin size="large" description="載入 Skills 能力圖譜..." />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)' }}>
      {/* Legend bar */}
      <div style={{
        padding: '8px 16px',
        background: '#fafafa',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flexWrap: 'wrap',
      }}>
        <Text strong style={{ fontSize: 13, marginRight: 4 }}>節點圖例：</Text>
        <Space size={4} wrap>
          {LEGEND_ITEMS.map((item) => (
            <Tag
              key={item.type}
              color={item.color}
              style={{ margin: 0, fontSize: 12 }}
            >
              {item.label}
            </Tag>
          ))}
        </Space>
        <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
          共 {graphData?.nodes.length ?? 0} 節點 / {graphData?.edges.length ?? 0} 邊
        </Text>
      </div>

      {/* Graph canvas */}
      <div ref={containerRef} style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa', position: 'relative' }}>
        <KnowledgeGraph
          documentIds={emptyDocumentIds}
          externalGraphData={graphData ?? undefined}
          onExternalRefresh={() => refetch()}
          onNodeClickExternal={handleNodeClick}
          height={typeof window !== 'undefined' ? window.innerHeight - 240 : 600}
          width={containerWidth || undefined}
          nodeConfig={GRAPH_NODE_CONFIG}
        />

        {/* Selected skill info card */}
        {selectedSkill && (
          <Card
            size="small"
            title={selectedSkill.label}
            extra={
              <CloseOutlined
                style={{ cursor: 'pointer', fontSize: 12 }}
                onClick={() => setSelectedSkill(null)}
              />
            }
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              width: 280,
              zIndex: 10,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            }}
          >
            <Descriptions column={1} size="small" colon={false}>
              <Descriptions.Item label="類型">
                <Tag color={LEGEND_ITEMS.find((l) => l.type === selectedSkill.type)?.color ?? '#999'}>
                  {TYPE_LABELS[selectedSkill.type] ?? selectedSkill.type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="ID">
                <Text code style={{ fontSize: 12 }}>{selectedSkill.id}</Text>
              </Descriptions.Item>
              {selectedNodeData?.mention_count != null && (
                <Descriptions.Item label="成熟度">
                  {getMaturityLabel(selectedNodeData.mention_count) ?? `${selectedNodeData.mention_count}`}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        )}
      </div>
    </div>
  );
};

export default SkillsMapTab;
