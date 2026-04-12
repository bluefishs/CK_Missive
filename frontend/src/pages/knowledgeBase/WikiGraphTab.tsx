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

import React, { useCallback, useEffect, useRef, useMemo } from 'react';
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

// 節點半徑: log 縮放 + 上下限，避免大節點遮蔽小節點
const NODE_RADIUS_MIN = 4;
const NODE_RADIUS_MAX = 16;

function calcRadius(docCount: number): number {
  if (docCount <= 0) return NODE_RADIUS_MIN;
  // log10(1)=0, log10(10)=1, log10(100)=2, log10(1000)=3
  const t = Math.log10(docCount + 1) / 3; // 正規化到 0~1 (假設 max ~1000)
  return NODE_RADIUS_MIN + (NODE_RADIUS_MAX - NODE_RADIUS_MIN) * Math.min(t, 1);
}

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
        _radius: calcRadius(n.doc_count),
        // val 仍用於 force-graph 的 charge 計算，但用 log 縮放
        val: calcRadius(n.doc_count) * 2,
      })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
      })),
    };
  }, [data]);

  // 碰撞力 — 避免節點重疊
  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;
    const fg = graphRef.current;
    import('d3-force').then((d3) => {
      fg.d3Force('collide',
        d3.forceCollide()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .radius((node: any) => (node._radius || NODE_RADIUS_MIN) + 10)
          .strength(0.8)
      );
      // 加大節點間距
      fg.d3Force('charge')?.strength(-120);
      fg.d3ReheatSimulation();
    }).catch(() => {/* d3-force 已由 react-force-graph 內含 */});
  }, [graphData]);

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
      const radius = node._radius || NODE_RADIUS_MIN;
      const baseColor = node.color || '#8c8c8c';

      // 半透明填充 — 重疊時仍可看到下層
      ctx.globalAlpha = 0.7;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = baseColor;
      ctx.fill();

      // 邊框 — 區分節點邊界
      ctx.globalAlpha = 1;
      ctx.strokeStyle = baseColor;
      ctx.lineWidth = 1.2 / globalScale;
      ctx.stroke();

      // doc_count 數字 (節點內)
      if (node.doc_count > 0 && globalScale > 0.8) {
        const numSize = Math.max(7 / globalScale, 2);
        ctx.font = `bold ${numSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        ctx.fillText(
          node.doc_count > 999 ? `${Math.round(node.doc_count / 100) / 10}k` : String(node.doc_count),
          node.x, node.y,
        );
      }

      // 標籤 (節點下方，任何縮放都顯示但大小自適應)
      const fontSize = Math.min(Math.max(9 / globalScale, 2.5), 6);
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#555';
      const truncLen = globalScale > 1.5 ? 25 : globalScale > 0.8 ? 12 : 6;
      const displayLabel = label.length > truncLen ? label.slice(0, truncLen) + '...' : label;
      ctx.fillText(displayLabel, node.x, node.y + radius + 2);
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
          nodePointerAreaPaint={(node: any, color, ctx) => { // eslint-disable-line @typescript-eslint/no-explicit-any
            const r = node._radius || NODE_RADIUS_MIN;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI);
            ctx.fill();
          }}
          onNodeClick={handleNodeClick}
          linkColor={() => 'rgba(150,150,150,0.35)'}
          linkWidth={0.8}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={0.9}
          width={undefined}
          height={500}
          cooldownTicks={120}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.25}
        />
      </Card>
    </div>
  );
};

export default WikiGraphTab;
