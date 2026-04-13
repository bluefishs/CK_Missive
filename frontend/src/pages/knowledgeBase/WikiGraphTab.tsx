/**
 * Wiki 圖譜 Tab — force-graph 2D 視覺化 wiki 頁面關係
 *
 * 對齊 KnowledgeGraphPage/GraphCanvas 機制:
 * - ResizeObserver 動態計算寬高 (全版面)
 * - calc(100vh - offset) 最大化顯示
 * - zoomToFit 初始自動縮放
 * - 碰撞力 + log 半徑 + 半透明避免遮蔽
 * - 節點 hover tooltip + click zoom
 *
 * @version 2.0.0 — 對齊 GraphCanvas 產品級機制
 * @created 2026-04-13
 */

import React, { useCallback, useEffect, useRef, useMemo, useState } from 'react';
import { Spin, Empty, Row, Col, Statistic, Tag, Space, Tooltip, Button } from 'antd';
import {
  LinkOutlined,
  FileTextOutlined,
  AimOutlined,
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
  color?: string;
  _radius?: number;
  val?: number;
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
  org: '#1890ff',
  project: '#52c41a',
  dispatch: '#fa8c16',
  topic: '#722ed1',
  source: '#13c2c2',
  synthesis: '#eb2f96',
  entities: '#1890ff',
  topics: '#722ed1',
  sources: '#13c2c2',
};

const TYPE_LABELS: Record<string, string> = {
  org: '機關',
  project: '案件',
  dispatch: '派工單',
  topic: '主題',
  entities: '實體',
};

// ── Node sizing: log scale, clamped ──

const NODE_R_MIN = 3;
const NODE_R_MAX = 14;

function calcRadius(docCount: number): number {
  if (docCount <= 0) return NODE_R_MIN;
  const t = Math.log10(docCount + 1) / 3;
  return NODE_R_MIN + (NODE_R_MAX - NODE_R_MIN) * Math.min(t, 1);
}

// ── Component ──

const WikiGraphTab: React.FC = () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<WikiNode | null>(null);

  // ── ResizeObserver: 動態計算寬高 (對齊 GraphCanvas) ──
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width: Math.floor(width), height: Math.floor(height) });
        }
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── Data ──
  const { data, isLoading } = useQuery<WikiGraphResponse>({
    queryKey: ['wiki-graph'],
    queryFn: async () => {
      const resp = await apiClient.post<{ success: boolean; data: WikiGraphResponse }>(
        API_ENDPOINTS.WIKI.GRAPH, {}
      );
      return resp.data;
    },
    staleTime: 5 * 60_000,
  });

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n) => ({
        ...n,
        color: TYPE_COLORS[n.entity_type] || TYPE_COLORS[n.type] || '#8c8c8c',
        _radius: calcRadius(n.doc_count),
        val: calcRadius(n.doc_count) * 2,
      })),
      links: data.edges.map((e) => ({ source: e.source, target: e.target })),
    };
  }, [data]);

  // ── Forces: collide + charge ──
  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;
    const fg = graphRef.current;
    import('d3-force').then((d3) => {
      fg.d3Force('collide',
        d3.forceCollide()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .radius((node: any) => (node._radius || NODE_R_MIN) + 8)
          .strength(0.7)
          .iterations(2)
      );
      fg.d3Force('charge')?.strength(-100);
      fg.d3ReheatSimulation();
    }).catch(() => {});
  }, [graphData]);

  // ── zoomToFit on engine stop (對齊 GraphCanvas) ──
  const handleEngineStop = useCallback(() => {
    graphRef.current?.zoomToFit(400, 40);
  }, []);

  const handleZoomToFit = useCallback(() => {
    graphRef.current?.zoomToFit(300, 40);
  }, []);

  const handleNodeClick = useCallback((node: WikiNode) => {
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 500);
      graphRef.current.zoom(2.5, 500);
    }
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node || null);
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? 'pointer' : 'default';
    }
  }, []);

  // ── Canvas rendering ──
  const nodeCanvasObject = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label: string = node.label || '';
      const radius: number = node._radius || NODE_R_MIN;
      const baseColor: string = node.color || '#8c8c8c';
      const isHovered = hoveredNode?.id === node.id;

      // 圓圈 (半透明)
      ctx.globalAlpha = isHovered ? 1 : 0.65;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = baseColor;
      ctx.fill();

      // 邊框
      ctx.globalAlpha = 1;
      ctx.strokeStyle = isHovered ? '#000' : baseColor;
      ctx.lineWidth = isHovered ? 2 / globalScale : 0.8 / globalScale;
      ctx.stroke();

      // doc_count (節點內白字)
      if (node.doc_count > 0 && radius >= 5 && globalScale > 0.6) {
        const ns = Math.max(6 / globalScale, 1.5);
        ctx.font = `bold ${ns}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        ctx.fillText(
          node.doc_count > 999 ? `${(node.doc_count / 1000).toFixed(1)}k` : String(node.doc_count),
          node.x, node.y,
        );
      }

      // 標籤 — 縮放級別自適應
      if (globalScale > 0.5) {
        const fs = Math.min(Math.max(8 / globalScale, 2), 5);
        ctx.font = `${fs}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = isHovered ? '#000' : '#666';
        const maxLen = globalScale > 2 ? 30 : globalScale > 1 ? 16 : 8;
        const txt = label.length > maxLen ? label.slice(0, maxLen) + '…' : label;
        ctx.fillText(txt, node.x, node.y + radius + 1.5);
      }
    },
    [hoveredNode],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodePointerArea = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const r = (node._radius || NODE_R_MIN) + 3;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fill();
  }, []);

  // ── Loading / Empty ──
  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  }
  if (!data || data.nodes.length === 0) {
    return <Empty description="Wiki 尚無內容，請先執行編譯" />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 220px)', minHeight: 400 }}>
      {/* 頂部統計列 */}
      <Row gutter={8} style={{ marginBottom: 8, flex: '0 0 auto' }}>
        <Col flex="auto">
          <Space size="middle">
            <Statistic title="頁面" value={data.stats.total_nodes} prefix={<FileTextOutlined />} valueStyle={{ fontSize: 16 }} />
            <Statistic title="連結" value={data.stats.total_edges} prefix={<LinkOutlined />} valueStyle={{ fontSize: 16 }} />
            {Object.entries(data.stats.by_type)
              .filter(([, v]) => v > 0)
              .map(([k, v]) => (
                <Tag key={k} color={TYPE_COLORS[k] || 'default'}>
                  {TYPE_LABELS[k] || k}: {v}
                </Tag>
              ))}
          </Space>
        </Col>
        <Col flex="0 0 auto">
          <Space>
            <Tooltip title="自動縮放適配">
              <Button size="small" icon={<AimOutlined />} onClick={handleZoomToFit} />
            </Tooltip>
          </Space>
        </Col>
      </Row>

      {/* Hover tooltip */}
      {hoveredNode && (
        <div style={{
          position: 'absolute', right: 16, top: 80, zIndex: 10,
          background: '#fff', border: '1px solid #d9d9d9', borderRadius: 6,
          padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          maxWidth: 300, pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{hoveredNode.label}</div>
          <Tag color={TYPE_COLORS[hoveredNode.entity_type] || 'default'}>
            {TYPE_LABELS[hoveredNode.entity_type] || hoveredNode.entity_type}
          </Tag>
          {hoveredNode.doc_count > 0 && <Tag>{hoveredNode.doc_count} 件</Tag>}
        </div>
      )}

      {/* 圖譜容器 — flex:1 填滿剩餘空間 */}
      <div
        ref={containerRef}
        style={{ flex: 1, minHeight: 0, border: '1px solid #f0f0f0', borderRadius: 6, overflow: 'hidden', position: 'relative' }}
      >
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeId="id"
          width={dimensions.width}
          height={dimensions.height}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={nodePointerArea}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onEngineStop={handleEngineStop}
          linkColor={() => 'rgba(150,150,150,0.3)'}
          linkWidth={0.6}
          linkDirectionalArrowLength={2.5}
          linkDirectionalArrowRelPos={0.9}
          cooldownTicks={150}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.2}
          enablePanInteraction={true}
          enableZoomInteraction={true}
        />
      </div>
    </div>
  );
};

export default WikiGraphTab;
