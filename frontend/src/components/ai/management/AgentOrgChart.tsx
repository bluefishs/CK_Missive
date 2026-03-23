/**
 * AgentOrgChart — Agent 組織圖 (V-3.1)
 *
 * 使用 React Flow 渲染 CK-AaaP 平台的 Agent 拓撲：
 * - NemoClaw (Leader) → OpenClaw (Engine) → Domain Agents (Plugins/Roles)
 * - KG federation data flow edges
 * - 即時狀態色碼 (active/degraded/offline/unknown)
 *
 * @version 1.0.0
 * @created 2026-03-23
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Badge, Card, Empty, Spin, Tag, Typography } from 'antd';
import { ApartmentOutlined, ReloadOutlined } from '@ant-design/icons';
import type { AgentNode as AgentNodeData, AgentEdge as AgentEdgeData } from '../../../types/ai';
import { getAgentTopology } from '../../../api/digitalTwin';

const { Text } = Typography;

// ── Node type → 視覺配置 ──

const NODE_STYLES: Record<string, { bg: string; border: string; badge: string }> = {
  leader: { bg: '#fff2e8', border: '#fa8c16', badge: 'warning' },
  engine: { bg: '#e6f4ff', border: '#1677ff', badge: 'processing' },
  role: { bg: '#f6ffed', border: '#52c41a', badge: 'success' },
  plugin: { bg: '#f9f0ff', border: '#722ed1', badge: 'default' },
};

const STATUS_BADGE: Record<string, 'success' | 'processing' | 'error' | 'default' | 'warning'> = {
  active: 'success',
  degraded: 'warning',
  offline: 'error',
  unknown: 'default',
};

// ── dagre-like manual layout (避免額外依賴) ──

function layoutNodes(apiNodes: AgentNodeData[]): Node[] {
  // Simple top-down layered layout
  const layers: Record<string, number> = {
    leader: 0,
    engine: 1,
    role: 2,
    plugin: 2,
  };

  const grouped: Record<number, AgentNodeData[]> = {};
  for (const n of apiNodes) {
    const layer = layers[n.type] ?? 2;
    if (!grouped[layer]) grouped[layer] = [];
    grouped[layer].push(n);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result: Node<any>[] = [];
  const nodeWidth = 220;
  const nodeHeight = 100;
  const layerGap = 140;

  for (const [layerStr, nodes] of Object.entries(grouped)) {
    const layer = Number(layerStr);
    const totalWidth = nodes.length * nodeWidth + (nodes.length - 1) * 40;
    const startX = -totalWidth / 2 + nodeWidth / 2;

    nodes.forEach((n, i) => {
      const nodeStyle = NODE_STYLES[n.type] ?? NODE_STYLES['plugin'];
      result.push({
        id: n.id,
        position: { x: startX + i * (nodeWidth + 40), y: layer * layerGap },
        data: { ...n },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
        style: {
          background: nodeStyle!.bg,
          border: `2px solid ${nodeStyle!.border}`,
          borderRadius: 10,
          padding: '8px 12px',
          width: nodeWidth,
          minHeight: nodeHeight,
          fontSize: 12,
        },
      });
    });
  }

  return result;
}

function layoutEdges(apiEdges: AgentEdgeData[]): Edge[] {
  return apiEdges.map((e, i) => ({
    id: `edge-${i}`,
    source: e.source,
    target: e.target,
    label: e.label,
    type: 'smoothstep',
    animated: e.type === 'delegation',
    style: {
      stroke: e.type === 'data_flow' ? '#52c41a' : '#1677ff',
      strokeWidth: e.type === 'data_flow' ? 1.5 : 2,
      strokeDasharray: e.type === 'data_flow' ? '6 3' : undefined,
    },
    labelStyle: { fontSize: 10, fill: '#666' },
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
  }));
}

// ── Custom node render (via default node but with rich label) ──

function AgentNodeLabel({ data }: { data: Record<string, unknown> }) {
  const nodeType = String(data['type'] ?? 'plugin');
  const status = String(data['status'] ?? 'unknown');
  const label = String(data['label'] ?? '');
  const project = String(data['project'] ?? '');
  const description = String(data['description'] ?? '');

  const statusBadge = STATUS_BADGE[status] ?? 'default';
  const nodeStyle = NODE_STYLES[nodeType] ?? NODE_STYLES['plugin']!;

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ marginBottom: 4 }}>
        <Badge status={statusBadge} />
        <Text strong style={{ fontSize: 13, marginLeft: 4 }}>{label}</Text>
      </div>
      <div style={{ marginBottom: 4 }}>
        <Tag color={nodeStyle.border} style={{ fontSize: 10, lineHeight: '18px' }}>
          {project}
        </Tag>
      </div>
      <Text type="secondary" style={{ fontSize: 10, display: 'block', lineHeight: '14px' }}>
        {description}
      </Text>
    </div>
  );
}

// ── Main Component ──

export const AgentOrgChart: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [meta, setMeta] = useState<{ total_nodes: number; total_edges: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadTopology = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAgentTopology();
      const flowNodes = layoutNodes(data.nodes);
      // Inject custom label via nodeTypes or default label override
      const labeledNodes = flowNodes.map((n) => ({
        ...n,
        data: { ...n.data, label: <AgentNodeLabel data={n.data} /> },
      }));
      setNodes(labeledNodes);
      setEdges(layoutEdges(data.edges));
      setMeta(data.meta);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  const legend = useMemo(
    () => (
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {Object.entries(NODE_STYLES).map(([type, s]) => (
          <Tag key={type} color={s.border} style={{ fontSize: 10 }}>
            {type === 'leader' ? '監控塔' : type === 'engine' ? '推理引擎' : type === 'role' ? '角色' : '插件'}
          </Tag>
        ))}
        <Tag color="blue" style={{ fontSize: 10 }}>── delegation</Tag>
        <Tag color="green" style={{ fontSize: 10 }}>- - data flow</Tag>
      </div>
    ),
    [],
  );

  if (error) {
    return (
      <Card>
        <Empty description={`無法載入 Agent 組織圖: ${error}`} />
      </Card>
    );
  }

  return (
    <Card
      title={
        <span>
          <ApartmentOutlined /> Agent 組織圖
          {meta && (
            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
              {meta.total_nodes} 節點 · {meta.total_edges} 連線
            </Text>
          )}
        </span>
      }
      extra={
        <a onClick={loadTopology} style={{ fontSize: 12 }}>
          <ReloadOutlined /> 重新整理
        </a>
      }
      size="small"
    >
      {legend}
      <Spin spinning={loading}>
        <div style={{ height: 480, marginTop: 8, border: '1px solid #f0f0f0', borderRadius: 8 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.3}
            maxZoom={1.5}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} size={1} color="#f5f5f5" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </Spin>
    </Card>
  );
};

export default AgentOrgChart;
