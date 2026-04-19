/**
 * SkillNebulaTab — 技能星雲 force-graph 2D
 *
 * Phase 5 Slice 4 — 視覺化 pattern「星雲」：
 *  - 節點 = pattern（tool_sequence / hit_count / success_rate / domain 顏色 / crystal 光環）
 *  - 邊 = 共用 tool 的 pattern 互連（weight 越高越粗）
 *
 * 靈感：Muse（muse.cheyuwu.com）星雲 — 每顆節點是一種技能，
 * 結晶過的 pattern 有金色外圈（代表沉澱為永久能力）。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, Col, Empty, Row, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import { AimOutlined, CrownOutlined, LinkOutlined, NodeIndexOutlined } from '@ant-design/icons';
import ForceGraph2D from 'react-force-graph-2d';

import { useNebulaGraph } from '../../hooks/useMemoryData';
import type { NebulaEdge, NebulaNode } from '../../types/memory';

// ── Node sizing（log scale，對齊 WikiGraphTab） ──

const NODE_R_MIN = 4;
const NODE_R_MAX = 16;

function calcRadius(hit: number): number {
  if (hit <= 0) return NODE_R_MIN;
  const t = Math.log10(hit + 1) / 2;
  return NODE_R_MIN + (NODE_R_MAX - NODE_R_MIN) * Math.min(t, 1);
}

// 由節點派生出 force-graph 需要的 val/_radius
interface GraphNode extends NebulaNode {
  _radius?: number;
}

const DOMAIN_LABELS: Record<string, string> = {
  doc: '公文',
  dispatch: '派工',
  graph: '圖譜',
  analysis: '分析',
  pm: 'PM',
  erp: 'ERP',
  mixed: '混合',
};

const SkillNebulaTab: React.FC = () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hovered, setHovered] = useState<GraphNode | null>(null);

  const { data, isLoading } = useNebulaGraph({ days: 30 });

  // ── ResizeObserver ──
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

  // ── graphData（映射 radius/val） ──
  const graphData = useMemo(() => {
    if (!data) return { nodes: [] as GraphNode[], links: [] as NebulaEdge[] };
    return {
      nodes: data.nodes.map<GraphNode>((n) => ({
        ...n,
        _radius: calcRadius(n.hit_count),
        val: calcRadius(n.hit_count) * 2,
      })),
      links: data.edges.map((e) => ({
        source: typeof e.source === 'string' ? e.source : e.source.id,
        target: typeof e.target === 'string' ? e.target : e.target.id,
        label: e.label,
        weight: e.weight ?? 1,
      })),
    };
  }, [data]);

  // ── d3-force 碰撞 + charge ──
  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;
    const fg = graphRef.current;
    import('d3-force').then((d3) => {
      fg.d3Force(
        'collide',
        d3.forceCollide()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .radius((node: any) => (node._radius || NODE_R_MIN) + 6)
          .strength(0.7)
          .iterations(2),
      );
      fg.d3Force('charge')?.strength(-120);
      fg.d3ReheatSimulation();
    }).catch(() => {});
  }, [graphData]);

  const handleEngineStop = useCallback(() => {
    graphRef.current?.zoomToFit(400, 40);
  }, []);

  const handleZoomToFit = useCallback(() => {
    graphRef.current?.zoomToFit(300, 40);
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeHover = useCallback((node: any) => {
    setHovered(node || null);
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? 'pointer' : 'default';
    }
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback((node: any) => {
    if (!graphRef.current) return;
    graphRef.current.centerAt(node.x, node.y, 500);
    graphRef.current.zoom(2.5, 500);
  }, []);

  // ── Canvas render ──
  const nodeCanvasObject = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const radius: number = node._radius || NODE_R_MIN;
      const baseColor: string = node.color || '#8c8c8c';
      const isHovered = hovered?.id === node.id;
      const label: string = node.label || '';
      const rate: number = node.success_rate ?? 0;

      // 結晶外圈（金色光環）
      if (node.is_crystal) {
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI);
        ctx.strokeStyle = '#faad14';
        ctx.lineWidth = Math.max(1.2 / globalScale, 0.6);
        ctx.stroke();
      }

      // 主體（半透明）
      ctx.globalAlpha = isHovered ? 1 : 0.7;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = baseColor;
      ctx.fill();

      // 邊框
      ctx.globalAlpha = 1;
      ctx.strokeStyle = isHovered ? '#000' : baseColor;
      ctx.lineWidth = isHovered ? 2 / globalScale : 0.8 / globalScale;
      ctx.stroke();

      // 中間 hit_count（白字）
      if (node.hit_count > 0 && radius >= 6 && globalScale > 0.6) {
        const ns = Math.max(6 / globalScale, 1.8);
        ctx.font = `bold ${ns}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        ctx.fillText(String(node.hit_count), node.x, node.y);
      }

      // 底下 label（工具名縮寫）
      if (globalScale > 0.7) {
        const fs = Math.min(Math.max(7 / globalScale, 2.2), 5);
        ctx.font = `${fs}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = isHovered ? '#000' : '#555';
        const maxLen = globalScale > 2 ? 24 : globalScale > 1 ? 14 : 8;
        const txt = label.length > maxLen ? `${label.slice(0, maxLen)}…` : label;
        ctx.fillText(txt, node.x, node.y + radius + 2);

        // success_rate（懸浮時顯示）
        if (isHovered) {
          ctx.fillStyle = rate >= 0.9 ? '#52c41a' : rate >= 0.7 ? '#fa8c16' : '#f5222d';
          ctx.fillText(`${(rate * 100).toFixed(0)}%`, node.x, node.y + radius + 2 + fs + 1);
        }
      }
    },
    [hovered],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodePointerArea = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const r = (node._radius || NODE_R_MIN) + 3;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fill();
  }, []);

  // ── Loading / empty ──
  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" tip="載入星雲中" /></div>;
  }
  if (!data || data.nodes.length === 0) {
    return (
      <Empty
        description="尚無 pattern（Pattern Extractor 04:00 自動產生後重新整理）"
        style={{ marginTop: 80 }}
      />
    );
  }

  const crystalCount = data.stats?.crystal_count ?? 0;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 280px)',
        minHeight: 420,
        overflow: 'hidden',
      }}
    >
      {/* Header 統計 */}
      <Row gutter={8} style={{ marginBottom: 6, flex: '0 0 auto' }}>
        <Col flex="auto">
          <Space size="small" wrap>
            <Tag icon={<NodeIndexOutlined />} color="blue">
              {data.stats?.total_nodes ?? 0} 個 pattern
            </Tag>
            <Tag icon={<LinkOutlined />} color="geekblue">
              {data.stats?.total_edges ?? 0} 共用 tool
            </Tag>
            <Tag icon={<CrownOutlined />} color="gold">
              {crystalCount} 個結晶候選
            </Tag>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              金色外圈 = 結晶候選 ·
              節點大小 = hit count（log 縮放）·
              顏色 = domain
            </Typography.Text>
          </Space>
        </Col>
        <Col flex="0 0 auto">
          <Tooltip title="自動縮放">
            <Button size="small" icon={<AimOutlined />} onClick={handleZoomToFit} />
          </Tooltip>
        </Col>
      </Row>

      {/* Hover tooltip 卡片 */}
      {hovered && (
        <Card
          size="small"
          style={{
            position: 'absolute', right: 24, top: 120, zIndex: 10,
            maxWidth: 320, boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            pointerEvents: 'none',
          }}
        >
          <Typography.Text strong>
            {hovered.is_crystal && <CrownOutlined style={{ color: '#faad14', marginRight: 4 }} />}
            Pattern {hovered.id.slice(0, 12)}…
          </Typography.Text>
          <div style={{ marginTop: 4 }}>
            <Tag color="blue">{hovered.hit_count} hit</Tag>
            <Tag color={hovered.success_rate >= 0.9 ? 'green' : 'orange'}>
              {(hovered.success_rate * 100).toFixed(1)}%
            </Tag>
            {hovered.domains.map((d) => (
              <Tag key={d} color="purple">{DOMAIN_LABELS[d] ?? d}</Tag>
            ))}
          </div>
          <div style={{ marginTop: 6, fontSize: 12, color: '#666' }}>
            <strong>tools:</strong> {hovered.tools.join(' → ')}
          </div>
        </Card>
      )}

      {/* 圖譜容器 */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          minHeight: 0,
          border: '1px solid #f0f0f0',
          borderRadius: 6,
          overflow: 'hidden',
          position: 'relative',
          background: 'linear-gradient(135deg, #0a0e1a 0%, #1a1f3a 100%)',
        }}
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
          linkColor={() => 'rgba(180,180,220,0.25)'}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          linkWidth={(l: any) => Math.min(3, Math.log2((l.weight ?? 1) + 1))}
          cooldownTicks={180}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.25}
          enablePanInteraction
          enableZoomInteraction
        />
      </div>
    </div>
  );
};

export default SkillNebulaTab;
