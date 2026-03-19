/**
 * Evolution Graph v3 — 白底主題 + 結構化佈局
 *
 * @version 3.0.0
 */

import React, { useRef, useCallback, useMemo, useState, useEffect } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import type { GraphNode, GraphLink, ForceGraphData, CategoryInfo } from './types';

interface EvolutionGraphProps {
  graphData: ForceGraphData;
  categories: Record<string, CategoryInfo>;
  highlightNodeId?: number | null;
}

export const EvolutionGraph: React.FC<EvolutionGraphProps> = ({
  graphData,
  categories,
  highlightNodeId,
}) => {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });
  const [hoverId, setHoverId] = useState<number | null>(null);

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

  // Force config: spread nodes apart
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force('charge')?.strength(-400);
    fg.d3Force('link')?.distance((link: { source: GraphNode; target: GraphNode }) => {
      const s = typeof link.source === 'object' ? link.source : null;
      const t = typeof link.target === 'object' ? link.target : null;
      return 50 + ((s?.size ?? 10) + (t?.size ?? 10)) * 1.2;
    });
    fg.d3Force('center')?.strength(0.04);
  }, [graphData]);

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

  const getColor = useCallback((cat: string) => categories[cat]?.color || '#999', [categories]);

  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D) => {
    const x = node.x ?? 0, y = node.y ?? 0;
    const isPlanned = node.source === 'planned';
    const isMerged = node.source === 'merged';
    const isActive = activeId === node.id;
    const dimmed = connSet != null && !connSet.has(node.id);
    const r = 4 + node.maturity * 1.8 + (node.size > 15 ? (node.size - 15) * 0.4 : 0);
    const color = getColor(node.category);

    ctx.save();
    ctx.globalAlpha = dimmed ? 0.2 : 1;

    // Shadow for active
    if (isActive) {
      ctx.shadowColor = color;
      ctx.shadowBlur = 15;
    }

    // Circle
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    if (isPlanned) {
      ctx.fillStyle = '#f5f5f5';
      ctx.fill();
      ctx.setLineDash([2, 2]);
      ctx.strokeStyle = '#ccc';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (isMerged) {
      ctx.fillStyle = '#fffbe6';
      ctx.fill();
      ctx.strokeStyle = '#faad14';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    } else {
      ctx.fillStyle = color;
      ctx.fill();
      // White border for contrast on light bg
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    ctx.shadowBlur = 0;

    // Label
    const showLabel = node.size >= 12 || isActive || (connSet != null && connSet.has(node.id));
    if (showLabel && !dimmed) {
      const fs = isActive ? 8 : Math.max(5, r * 0.5);
      ctx.font = `${isActive ? 'bold ' : ''}${fs}px "Microsoft JhengHei", sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const ly = y + r + 3;
      const tw = ctx.measureText(node.name).width;

      // White background for text readability
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.fillRect(x - tw / 2 - 2, ly - 1, tw + 4, fs + 2);

      ctx.fillStyle = isPlanned ? '#bbb' : '#333';
      ctx.fillText(node.name, x, ly);

      // Hover info
      if (isActive && node.description) {
        const dfs = fs - 1;
        ctx.font = `${dfs}px "Microsoft JhengHei", sans-serif`;
        ctx.fillStyle = '#888';
        const desc = node.description.length > 25 ? node.description.slice(0, 25) + '…' : node.description;
        const dtw = ctx.measureText(desc).width;
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillRect(x - dtw / 2 - 2, ly + fs + 2, dtw + 4, dfs + 2);
        ctx.fillStyle = '#888';
        ctx.fillText(desc, x, ly + fs + 3);

        // Stars
        const stars = '★'.repeat(node.maturity) + '☆'.repeat(5 - node.maturity);
        ctx.fillStyle = '#faad14';
        ctx.font = `${dfs}px sans-serif`;
        ctx.fillText(stars, x, ly + fs + dfs + 5);
      }
    }

    // Version inside node for large ones
    if (node.size >= 18 && !dimmed && !isPlanned) {
      ctx.font = 'bold 4px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#fff';
      ctx.fillText(node.version, x, y);
    }

    ctx.restore();
  }, [activeId, connSet, getColor]);

  const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D) => {
    const s = link.source as GraphNode, t = link.target as GraphNode;
    if (s.x == null || t.x == null || s.y == null || t.y == null) return;
    const connected = connSet == null || (connSet.has(s.id) && connSet.has(t.id));

    ctx.save();
    ctx.globalAlpha = connected ? 1 : 0.08;
    ctx.beginPath();

    if (link.type === 'merge') {
      ctx.setLineDash([5, 3]);
      ctx.strokeStyle = '#fa8c16';
      ctx.lineWidth = 1.5;
    } else if (link.type === 'planned') {
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = '#d9d9d9';
      ctx.lineWidth = 1;
    } else {
      ctx.strokeStyle = '#52c41a';
      ctx.lineWidth = 1.8;
    }

    ctx.moveTo(s.x, s.y);
    ctx.lineTo(t.x, t.y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Arrow
    if (connected) {
      const a = Math.atan2(t.y - s.y, t.x - s.x);
      const tr = 4 + (t as GraphNode).maturity * 1.8;
      const ax = t.x - Math.cos(a) * (tr + 4);
      const ay = t.y - Math.sin(a) * (tr + 4);
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(ax - 5 * Math.cos(a - 0.4), ay - 5 * Math.sin(a - 0.4));
      ctx.lineTo(ax - 5 * Math.cos(a + 0.4), ay - 5 * Math.sin(a + 0.4));
      ctx.closePath();
      ctx.fillStyle = link.type === 'merge' ? '#fa8c16' : link.type === 'planned' ? '#d9d9d9' : '#52c41a';
      ctx.fill();
    }

    ctx.restore();
  }, [connSet]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', background: '#fafbfc' }}>
      <ForceGraph2D
        ref={fgRef as never}
        graphData={graphData as never}
        width={dims.w}
        height={dims.h}
        nodeCanvasObject={paintNode as never}
        nodePointerAreaPaint={((node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, 8 + node.maturity * 2, 0, Math.PI * 2);
          ctx.fill();
        }) as never}
        linkCanvasObject={paintLink as never}
        linkCanvasObjectMode={() => 'replace'}
        onNodeHover={((n: GraphNode | null) => setHoverId(n?.id ?? null)) as never}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.25}
        warmupTicks={100}
        cooldownTicks={300}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 50)}
        backgroundColor="#fafbfc"
        enableNodeDrag
      />
    </div>
  );
};
