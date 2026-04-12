/**
 * Wiki 圖譜 Tab — force-graph 2D 視覺化 wiki 頁面關係
 *
 * 節點: wiki 頁面 (按 entity_type 著色)
 * 邊: wiki [[links]] 跨頁引用
 * 節點大小: doc_count 加權
 *
 * @version 1.0.0
 * @created 2026-04-13
 */

import React, { useCallback, useRef, useMemo } from 'react';
import { Card, Spin, Empty, Row, Col, Statistic, Tag, Space } from 'antd';
import {
  NodeIndexOutlined,
  LinkOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';

import apiClient from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';

// ── Types ──

interface WikiNode {
  id: string;
  label: string;
  type: string;
  entity_type: string;
  confidence: string;
  doc_count: number;
  x?: number;
  y?: number;
}

interface WikiEdge {
  source: string;
  target: string;
}

interface WikiGraphResponse {
  nodes: WikiNode[];
  edges: WikiEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    by_type: Record<string, number>;
  };
}

// ── Color scheme ──

const TYPE_COLORS: Record<string, string> = {
  org: '#1890ff',        // 機關 — 藍
  project: '#52c41a',    // 案件 — 綠
  topic: '#722ed1',      // 主題 — 紫
  source: '#fa8c16',     // 來源 — 橙
  synthesis: '#eb2f96',  // 綜合 — 洋紅
  entities: '#1890ff',
  topics: '#722ed1',
  sources: '#fa8c16',
};

const CONFIDENCE_SIZE: Record<string, number> = {
  high: 8,
  medium: 5,
  low: 3,
};

// ── Component ──

const WikiGraphTab: React.FC = () => {
  const graphRef = useRef<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any

  const { data, isLoading } = useQuery<WikiGraphResponse>({
    queryKey: ['wiki-graph'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiGraphResponse }>(
        API_ENDPOINTS.WIKI.GRAPH, {}
      );
      return resp.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n) => ({
        ...n,
        color: TYPE_COLORS[n.entity_type] || TYPE_COLORS[n.type] || '#8c8c8c',
        val: (n.doc_count || 1) * 0.3 + (CONFIDENCE_SIZE[n.confidence] || 5),
      })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
      })),
    };
  }, [data]);

  const handleNodeClick = useCallback(
    (node: WikiNode) => {
      if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 500);
        graphRef.current.zoom(3, 500);
      }
    },
    [],
  );

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => { // eslint-disable-line @typescript-eslint/no-explicit-any
      const label = node.label || '';
      const fontSize = Math.max(10 / globalScale, 2);
      const radius = Math.sqrt(node.val || 5) * 1.5;

      // 圓圈
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.color || '#8c8c8c';
      ctx.fill();

      // 標籤 (縮放 > 1.5 才顯示)
      if (globalScale > 1.2) {
        ctx.font = `${fontSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = '#333';
        ctx.fillText(label.slice(0, 20), node.x, node.y + radius + 2);
      }
    },
    [],
  );

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" tip="載入 Wiki 圖譜..." />
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return <Empty description="Wiki 尚無內容，請先執行編譯 POST /wiki/compile" />;
  }

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Wiki 頁面"
              value={data.stats.total_nodes}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="頁面連結"
              value={data.stats.total_edges}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Space>
              <NodeIndexOutlined /> 類型分佈:
              {Object.entries(data.stats.by_type)
                .filter(([, v]) => v > 0)
                .map(([k, v]) => (
                  <Tag key={k} color={TYPE_COLORS[k] || 'default'}>
                    {k}: {v}
                  </Tag>
                ))}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 力導引圖 */}
      <Card
        size="small"
        styles={{ body: { padding: 0, height: 500, position: 'relative' } }}
      >
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeId="id"
          nodeCanvasObject={nodeCanvasObject}
          onNodeClick={handleNodeClick}
          linkColor={() => 'rgba(150,150,150,0.4)'}
          linkWidth={1}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={0.9}
          width={undefined}
          height={500}
          cooldownTicks={80}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.3}
        />
      </Card>
    </div>
  );
};

export default WikiGraphTab;
