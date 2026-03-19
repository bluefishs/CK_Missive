/**
 * Evolution Graph v4 — Clustered layout + HTML tooltip + category rings
 * @version 4.0.0
 */
import React, { useRef, useCallback, useMemo, useState, useEffect } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { forceCollide } from 'd3-force';
import { Card, Tag, Space, Rate } from 'antd';
import type { GraphNode, GraphLink, ForceGraphData, CategoryInfo } from './types';

const SOURCE_COLORS: Record<string, string> = { active: '#52c41a', planned: '#1677ff', merged: '#faad14' };

interface EvolutionGraphProps {
  graphData: ForceGraphData;
  categories: Record<string, CategoryInfo>;
  highlightNodeId?: number | null;
}

const nodeRadius = (n: GraphNode) =>
  4 + n.maturity * 1.8 + (n.size > 15 ? (n.size - 15) * 0.4 : 0);

export const EvolutionGraph: React.FC<EvolutionGraphProps> = ({ graphData, categories, highlightNodeId }) => {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });
  const [hoverId, setHoverId] = useState<number | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      const e = entries[0];
      if (e) setDims({ w: Math.max(e.contentRect.width, 300), h: Math.max(e.contentRect.height, 300) });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const catKeys = Object.keys(categories);
    const clusterCenters: Record<string, { x: number; y: number }> = {};
    const r = 200;
    catKeys.forEach((cat, i) => {
      const angle = (2 * Math.PI * i) / catKeys.length - Math.PI / 2;
      clusterCenters[cat] = { x: r * Math.cos(angle), y: r * Math.sin(angle) };
    });
    fg.d3Force('charge')?.strength(-350);
    fg.d3Force('link')?.distance((link: { source: GraphNode; target: GraphNode }) => {
      const s = typeof link.source === 'object' ? link.source : null;
      const t = typeof link.target === 'object' ? link.target : null;
      return s?.category === t?.category ? 35 : 100;
    });
    fg.d3Force('collide', forceCollide<GraphNode>()
      .radius((n: GraphNode) => nodeRadius(n) + 4).iterations(2) as never);
    for (const node of graphData.nodes) {
      const center = clusterCenters[node.category];
      if (center && node.x == null) {
        node.x = center.x + (Math.random() - 0.5) * 60;
        node.y = center.y + (Math.random() - 0.5) * 60;
      }
    }
    fg.d3Force('center')?.strength(0.02);
  }, [graphData, categories]);

  useEffect(() => {
    if (highlightNodeId != null && fgRef.current) {
      const node = graphData.nodes.find(n => n.id === highlightNodeId);
      if (node?.x != null && node?.y != null) {
        fgRef.current.centerAt(node.x, node.y, 500);
        fgRef.current.zoom(2.5, 500);
      }
    }
  }, [highlightNodeId, graphData.nodes]);

  const activeId = highlightNodeId ?? hoverId;
  const connSet = useMemo(() => {
    if (activeId == null) return null;
    const s = new Set<number>([activeId]);
    for (const l of graphData.links) {
      const src = typeof l.source === 'object' ? l.source.id : l.source;
      const tgt = typeof l.target === 'object' ? l.target.id : l.target;
      if (src === activeId) s.add(tgt as number);
      if (tgt === activeId) s.add(src as number);
    }
    return s;
  }, [activeId, graphData.links]);

  const hoveredNode = useMemo(
    () => (hoverId != null ? graphData.nodes.find(n => n.id === hoverId) ?? null : null),
    [hoverId, graphData.nodes],
  );
  const getColor = useCallback((cat: string) => categories[cat]?.color || '#999', [categories]);

  const categoryBounds = useMemo(() => {
    const grouped: Record<string, GraphNode[]> = {};
    for (const node of graphData.nodes) {
      if (node.x == null || node.y == null) continue;
      (grouped[node.category] ??= []).push(node);
    }
    const result: Array<{ cat: string; cx: number; cy: number; r: number; color: string }> = [];
    for (const [cat, nodes] of Object.entries(grouped)) {
      if (nodes.length < 2) continue;
      const cx = nodes.reduce((s, n) => s + (n.x ?? 0), 0) / nodes.length;
      const cy = nodes.reduce((s, n) => s + (n.y ?? 0), 0) / nodes.length;
      let maxDist = 0;
      for (const n of nodes) {
        const d = Math.hypot((n.x ?? 0) - cx, (n.y ?? 0) - cy);
        if (d > maxDist) maxDist = d;
      }
      result.push({ cat, cx, cy, r: maxDist + 30, color: categories[cat]?.color || '#999' });
    }
    return result;
  }, [graphData.nodes, categories]);

  const paintBefore = useCallback((ctx: CanvasRenderingContext2D) => {
    for (const { cat, cx, cy, r, color } of categoryBounds) {
      ctx.save();
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = color + '0D'; ctx.fill();
      ctx.setLineDash([6, 4]); ctx.strokeStyle = color + '33'; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = 'bold 7px "Microsoft JhengHei", sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
      ctx.fillStyle = color + '99';
      ctx.fillText(categories[cat]?.label || cat, cx, cy - r + 12);
      ctx.restore();
    }
  }, [categoryBounds, categories]);

  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D) => {
    const x = node.x ?? 0, y = node.y ?? 0;
    const isPlanned = node.source === 'planned', isMerged = node.source === 'merged';
    const isActive = activeId === node.id;
    const dimmed = connSet != null && !connSet.has(node.id);
    const r = nodeRadius(node), color = getColor(node.category);
    ctx.save(); ctx.globalAlpha = dimmed ? 0.2 : 1;
    if (isActive) { ctx.shadowColor = color; ctx.shadowBlur = 15; }
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
    if (isPlanned) {
      ctx.fillStyle = '#f5f5f5'; ctx.fill();
      ctx.setLineDash([2, 2]); ctx.strokeStyle = '#ccc'; ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([]);
    } else if (isMerged) {
      ctx.fillStyle = '#fffbe6'; ctx.fill(); ctx.strokeStyle = '#faad14'; ctx.lineWidth = 1.5; ctx.stroke();
    } else {
      ctx.fillStyle = color; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke();
    }
    ctx.shadowBlur = 0;
    const showLabel = node.size >= 12 || isActive || (connSet != null && connSet.has(node.id));
    if (showLabel && !dimmed) {
      const fs = isActive ? 8 : Math.max(5, r * 0.5);
      ctx.font = `${isActive ? 'bold ' : ''}${fs}px "Microsoft JhengHei", sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      const ly = y + r + 3, tw = ctx.measureText(node.name).width;
      ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.fillRect(x - tw / 2 - 2, ly - 1, tw + 4, fs + 2);
      ctx.fillStyle = isPlanned ? '#bbb' : '#333'; ctx.fillText(node.name, x, ly);
    }
    if (node.size >= 18 && !dimmed && !isPlanned) {
      ctx.font = 'bold 4px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = '#fff'; ctx.fillText(node.version, x, y);
    }
    ctx.restore();
  }, [activeId, connSet, getColor]);

  const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D) => {
    const s = link.source as GraphNode, t = link.target as GraphNode;
    if (s.x == null || t.x == null || s.y == null || t.y == null) return;
    const connected = connSet == null || (connSet.has(s.id) && connSet.has(t.id));
    ctx.save(); ctx.globalAlpha = connected ? 1 : 0.08; ctx.beginPath();
    if (link.type === 'merge') {
      ctx.setLineDash([5, 3]); ctx.strokeStyle = '#fa8c16'; ctx.lineWidth = 1.5;
    } else if (link.type === 'planned') {
      ctx.setLineDash([3, 4]); ctx.strokeStyle = '#d9d9d9'; ctx.lineWidth = 1;
    } else { ctx.strokeStyle = '#52c41a'; ctx.lineWidth = 1.8; }
    ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke(); ctx.setLineDash([]);
    if (connected) {
      const a = Math.atan2(t.y - s.y, t.x - s.x), tr = nodeRadius(t);
      const ax = t.x - Math.cos(a) * (tr + 4), ay = t.y - Math.sin(a) * (tr + 4);
      ctx.beginPath(); ctx.moveTo(ax, ay);
      ctx.lineTo(ax - 5 * Math.cos(a - 0.4), ay - 5 * Math.sin(a - 0.4));
      ctx.lineTo(ax - 5 * Math.cos(a + 0.4), ay - 5 * Math.sin(a + 0.4));
      ctx.closePath();
      ctx.fillStyle = link.type === 'merge' ? '#fa8c16' : link.type === 'planned' ? '#d9d9d9' : '#52c41a';
      ctx.fill();
    }
    ctx.restore();
  }, [connSet]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }, []);

  return (
    <div ref={containerRef}
      style={{ width: '100%', height: '100%', background: '#fafbfc', position: 'relative' }}
      onMouseMove={handleMouseMove}>
      <ForceGraph2D
        ref={fgRef as never} graphData={graphData as never} width={dims.w} height={dims.h}
        nodeCanvasObject={paintNode as never}
        nodePointerAreaPaint={((node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.fillStyle = color; ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, 8 + node.maturity * 2, 0, Math.PI * 2); ctx.fill();
        }) as never}
        linkCanvasObject={paintLink as never} linkCanvasObjectMode={() => 'replace'}
        onNodeHover={((n: GraphNode | null) => setHoverId(n?.id ?? null)) as never}
        onRenderFramePre={paintBefore as never}
        d3AlphaDecay={0.02} d3VelocityDecay={0.25} warmupTicks={100} cooldownTicks={300}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 50)} backgroundColor="#fafbfc" enableNodeDrag
      />
      {hoveredNode && (
        <Card size="small" style={{
          position: 'absolute', left: Math.min(mousePos.x + 12, dims.w - 270),
          top: Math.max(mousePos.y - 10, 4), maxWidth: 250, pointerEvents: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)', zIndex: 10,
        }} styles={{ body: { padding: '10px 12px' } }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>{hoveredNode.name}</span>
            <Space size={4} wrap>
              <Tag color={getColor(hoveredNode.category)}>
                {categories[hoveredNode.category]?.label || hoveredNode.category}
              </Tag>
              <Tag>{hoveredNode.version}</Tag>
              <Tag color={SOURCE_COLORS[hoveredNode.source] || '#999'}>{hoveredNode.source}</Tag>
            </Space>
            <Rate disabled value={hoveredNode.maturity} count={5} style={{ fontSize: 14 }} />
            {hoveredNode.description && (
              <span style={{ fontSize: 12, color: '#666' }}>{hoveredNode.description}</span>
            )}
          </Space>
        </Card>
      )}
    </div>
  );
};
