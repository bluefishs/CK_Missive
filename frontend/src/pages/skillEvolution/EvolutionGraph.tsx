/**
 * Evolution Graph - 結構化技能演化樹視覺化
 *
 * 使用 force-directed + 徑向分層佈局：
 * - 主幹（乾坤智能體）在中心
 * - 六大層級環繞主幹
 * - 子技能分布在外圈
 * - 標籤只在大節點或 hover 時顯示
 *
 * @version 2.0.0
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
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);

  // Responsive sizing
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setDimensions({ width: Math.max(width, 300), height: Math.max(height, 300) });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Configure forces for structured layout
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    // Increase repulsion to spread nodes out
    fg.d3Force('charge')?.strength(-300);
    // Increase link distance based on hierarchy
    fg.d3Force('link')?.distance((link: { source: GraphNode; target: GraphNode }) => {
      const src = (typeof link.source === 'object') ? link.source : null;
      const tgt = (typeof link.target === 'object') ? link.target : null;
      const srcSize = src?.size ?? 10;
      const tgtSize = tgt?.size ?? 10;
      // Larger nodes = farther apart
      return 40 + (srcSize + tgtSize) * 1.5;
    });
    // Center force
    fg.d3Force('center')?.strength(0.05);
  }, [graphData]);

  // Zoom to highlighted node
  useEffect(() => {
    if (highlightNodeId != null && fgRef.current) {
      const node = graphData.nodes.find(n => n.id === highlightNodeId);
      if (node?.x != null && node?.y != null) {
        fgRef.current.centerAt(node.x, node.y, 600);
        fgRef.current.zoom(2.5, 600);
      }
    }
  }, [highlightNodeId, graphData.nodes]);

  // Connected nodes for highlight tracing
  const connectedSet = useMemo(() => {
    const active = highlightNodeId ?? hoveredNodeId;
    if (active == null) return null;
    const set = new Set<number>([active]);
    for (const link of graphData.links) {
      const s = typeof link.source === 'object' ? link.source.id : link.source;
      const t = typeof link.target === 'object' ? link.target.id : link.target;
      if (s === active) set.add(t as number);
      if (t === active) set.add(s as number);
    }
    return set;
  }, [highlightNodeId, hoveredNodeId, graphData.links]);

  const getColor = useCallback((cat: string) => categories[cat]?.color || '#666', [categories]);

  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D) => {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const isPlanned = node.source === 'planned';
    const isMerged = node.source === 'merged';
    const isHovered = hoveredNodeId === node.id || highlightNodeId === node.id;
    const isConnected = connectedSet ? connectedSet.has(node.id) : true;
    const dimmed = connectedSet != null && !isConnected;

    // Size: maturity-based with minimum
    const r = 4 + node.maturity * 2 + (node.size > 15 ? (node.size - 15) * 0.5 : 0);
    const color = getColor(node.category);
    const alpha = dimmed ? 0.15 : 1;

    ctx.save();
    ctx.globalAlpha = alpha;

    // Glow for hovered/highlighted
    if (isHovered && !isPlanned) {
      ctx.shadowColor = color;
      ctx.shadowBlur = 20;
    }

    // Circle
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);

    if (isPlanned) {
      ctx.fillStyle = 'rgba(80, 80, 100, 0.4)';
      ctx.fill();
      ctx.setLineDash([2, 2]);
      ctx.strokeStyle = dimmed ? 'rgba(100,100,100,0.2)' : 'rgba(150,150,150,0.6)';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (isMerged) {
      ctx.fillStyle = '#f5c842';
      ctx.fill();
      ctx.strokeStyle = '#e6b800';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    } else {
      ctx.fillStyle = color;
      ctx.fill();
    }

    ctx.shadowBlur = 0;

    // Version badge for larger nodes
    if (node.size >= 14 && !dimmed) {
      const vText = node.version;
      ctx.font = 'bold 5px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(0,0,0,0.7)';
      ctx.fillText(vText, x, y);
    }

    // Label: only show for large nodes (>12), hovered, or highlighted
    const showLabel = node.size >= 12 || isHovered || isConnected;
    if (showLabel && !dimmed) {
      const fontSize = isHovered ? 7 : Math.max(4, Math.min(6, r * 0.5));
      ctx.font = `${isHovered ? 'bold ' : ''}${fontSize}px "Microsoft JhengHei", sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      const labelY = y + r + 3;
      const text = node.name;
      const tw = ctx.measureText(text).width;

      // Background for readability
      if (isHovered || node.size >= 18) {
        ctx.fillStyle = 'rgba(10, 10, 30, 0.75)';
        ctx.fillRect(x - tw / 2 - 2, labelY - 1, tw + 4, fontSize + 3);
      }

      ctx.fillStyle = isPlanned ? '#888' : (isHovered ? '#fff' : '#ccc');
      ctx.fillText(text, x, labelY);

      // Description on hover
      if (isHovered && node.description) {
        ctx.font = `${fontSize - 1}px "Microsoft JhengHei", sans-serif`;
        ctx.fillStyle = '#999';
        const desc = node.description.length > 30 ? node.description.slice(0, 30) + '...' : node.description;
        ctx.fillText(desc, x, labelY + fontSize + 3);

        // Maturity stars
        const stars = '★'.repeat(node.maturity) + '☆'.repeat(5 - node.maturity);
        ctx.fillStyle = '#fadb14';
        ctx.fillText(stars, x, labelY + fontSize * 2 + 4);
      }
    }

    ctx.restore();
  }, [hoveredNodeId, highlightNodeId, connectedSet, getColor]);

  const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D) => {
    const src = link.source as GraphNode;
    const tgt = link.target as GraphNode;
    if (src.x == null || tgt.x == null || src.y == null || tgt.y == null) return;

    const isConnectedLink = connectedSet != null && (
      connectedSet.has(src.id) && connectedSet.has(tgt.id)
    );
    const dimmed = connectedSet != null && !isConnectedLink;

    ctx.save();
    ctx.globalAlpha = dimmed ? 0.08 : 1;
    ctx.beginPath();

    if (link.type === 'merge') {
      ctx.setLineDash([5, 3]);
      ctx.strokeStyle = dimmed ? 'rgba(255,80,80,0.1)' : 'rgba(255, 80, 80, 0.6)';
      ctx.lineWidth = 1.5;
    } else if (link.type === 'planned') {
      ctx.setLineDash([3, 5]);
      ctx.strokeStyle = 'rgba(150, 150, 150, 0.3)';
      ctx.lineWidth = 0.8;
    } else {
      ctx.strokeStyle = dimmed ? 'rgba(80,200,120,0.1)' : 'rgba(80, 200, 120, 0.6)';
      ctx.lineWidth = 1.8;
    }

    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Arrow
    if (!dimmed) {
      const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
      const tgtR = 4 + (tgt as GraphNode).maturity * 2;
      const ax = tgt.x - Math.cos(angle) * (tgtR + 4);
      const ay = tgt.y - Math.sin(angle) * (tgtR + 4);
      const al = 6;

      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(ax - al * Math.cos(angle - 0.4), ay - al * Math.sin(angle - 0.4));
      ctx.lineTo(ax - al * Math.cos(angle + 0.4), ay - al * Math.sin(angle + 0.4));
      ctx.closePath();
      ctx.fillStyle = link.type === 'merge' ? 'rgba(255,80,80,0.7)' :
        link.type === 'planned' ? 'rgba(150,150,150,0.4)' : 'rgba(80,200,120,0.7)';
      ctx.fill();
    }

    ctx.restore();
  }, [connectedSet]);

  const handleNodeHover = useCallback((node: GraphNode | null) => {
    setHoveredNodeId(node?.id ?? null);
  }, []);

  const nodePointerArea = useCallback((node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
    const r = 6 + node.maturity * 2 + 4;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
    ctx.fill();
  }, []);

  return (
    <div ref={containerRef} style={{ flex: 1, position: 'relative', background: '#0d0d1f', minWidth: 0 }}>
      <ForceGraph2D
        ref={fgRef as never}
        graphData={graphData as never}
        width={dimensions.width}
        height={dimensions.height}
        nodeCanvasObject={paintNode as never}
        nodePointerAreaPaint={nodePointerArea as never}
        linkCanvasObject={paintLink as never}
        linkCanvasObjectMode={() => 'replace'}
        onNodeHover={handleNodeHover as never}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.25}
        warmupTicks={80}
        cooldownTicks={300}
        onEngineStop={() => fgRef.current?.zoomToFit(500, 60)}
        backgroundColor="#0d0d1f"
        enableNodeDrag={true}
      />
    </div>
  );
};
