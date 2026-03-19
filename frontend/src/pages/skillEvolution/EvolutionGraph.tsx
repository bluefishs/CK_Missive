/**
 * Evolution Graph - Force-directed graph with custom node/link rendering
 *
 * @version 1.0.0
 */

import React, { useRef, useCallback, useMemo, useState, useEffect } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { Tooltip } from 'antd';
import { StarFilled } from '@ant-design/icons';
import type { GraphNode, GraphLink, ForceGraphData, CategoryInfo } from './types';

interface EvolutionGraphProps {
  graphData: ForceGraphData;
  categories: Record<string, CategoryInfo>;
  highlightNodeId?: number | null;
}

const NODE_BASE_SIZE = 6;

export const EvolutionGraph: React.FC<EvolutionGraphProps> = ({
  graphData,
  categories,
  highlightNodeId,
}) => {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Responsive sizing
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setDimensions({ width: Math.max(width, 200), height: Math.max(height, 200) });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Zoom to highlighted node
  useEffect(() => {
    if (highlightNodeId != null && fgRef.current) {
      const node = graphData.nodes.find(n => n.id === highlightNodeId);
      if (node?.x != null && node?.y != null) {
        fgRef.current.centerAt(node.x, node.y, 600);
        fgRef.current.zoom(3, 600);
      }
    }
  }, [highlightNodeId, graphData.nodes]);

  const getNodeColor = useCallback((node: GraphNode) => {
    return categories[node.category]?.color || '#888';
  }, [categories]);

  const getNodeRadius = useCallback((node: GraphNode) => {
    const base = NODE_BASE_SIZE + node.maturity * 2;
    return node.source === 'planned' ? base * 0.7 : base;
  }, []);

  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D) => {
    const r = getNodeRadius(node);
    const color = getNodeColor(node);
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const isHighlighted = highlightNodeId === node.id;
    const isPlanned = node.source === 'planned';
    const isMerged = node.source === 'merged';

    ctx.save();

    // Glow effect for active nodes
    if (!isPlanned) {
      ctx.shadowColor = isHighlighted ? '#fff' : color;
      ctx.shadowBlur = isHighlighted ? 20 : 8;
    }

    // Draw circle
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);

    if (isMerged) {
      ctx.fillStyle = '#f5c842';
      ctx.fill();
    } else if (isPlanned) {
      ctx.fillStyle = 'rgba(128, 128, 128, 0.3)';
      ctx.fill();
      ctx.setLineDash([2, 2]);
      ctx.strokeStyle = '#888';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.setLineDash([]);
    } else {
      ctx.fillStyle = color;
      ctx.fill();
    }

    ctx.shadowBlur = 0;

    // Category border ring
    ctx.beginPath();
    ctx.arc(x, y, r + 1.5, 0, 2 * Math.PI);
    ctx.strokeStyle = isHighlighted ? '#fff' : color;
    ctx.lineWidth = isHighlighted ? 2 : 0.8;
    if (isPlanned) {
      ctx.setLineDash([2, 2]);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Label
    const fontSize = Math.max(3, r * 0.55);
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = isPlanned ? '#888' : '#e0e0e0';
    ctx.fillText(node.name, x, y + r + 3);

    ctx.restore();
  }, [getNodeRadius, getNodeColor, highlightNodeId]);

  const paintLink = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D) => {
    const src = link.source as GraphNode;
    const tgt = link.target as GraphNode;
    if (src.x == null || tgt.x == null || src.y == null || tgt.y == null) return;

    ctx.save();
    ctx.beginPath();

    if (link.type === 'merge') {
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = 'rgba(255, 80, 80, 0.6)';
      ctx.lineWidth = 1.2;
    } else if (link.type === 'planned') {
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = 'rgba(150, 150, 150, 0.4)';
      ctx.lineWidth = 0.8;
    } else {
      // evolution
      ctx.strokeStyle = 'rgba(80, 200, 120, 0.7)';
      ctx.lineWidth = 1.5;
    }

    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Arrow head
    const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
    const arrowLen = 5;
    const tgtR = getNodeRadius(tgt as GraphNode);
    const ax = tgt.x - Math.cos(angle) * (tgtR + 3);
    const ay = tgt.y - Math.sin(angle) * (tgtR + 3);

    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(
      ax - arrowLen * Math.cos(angle - Math.PI / 6),
      ay - arrowLen * Math.sin(angle - Math.PI / 6),
    );
    ctx.lineTo(
      ax - arrowLen * Math.cos(angle + Math.PI / 6),
      ay - arrowLen * Math.sin(angle + Math.PI / 6),
    );
    ctx.closePath();
    ctx.fillStyle = link.type === 'merge'
      ? 'rgba(255, 80, 80, 0.7)'
      : link.type === 'planned'
        ? 'rgba(150, 150, 150, 0.5)'
        : 'rgba(80, 200, 120, 0.8)';
    ctx.fill();

    // Edge label
    if (link.label) {
      const mx = (src.x + tgt.x) / 2;
      const my = (src.y + tgt.y) / 2;
      ctx.font = '3px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(200, 200, 200, 0.6)';
      ctx.fillText(link.label, mx, my - 3);
    }

    ctx.restore();
  }, [getNodeRadius]);

  const handleNodeHover = useCallback((node: GraphNode | null, prevNode: GraphNode | null) => {
    setHoveredNode(node);
    if (node && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      // Approximate screen position from graph coords
      if (fgRef.current && node.x != null && node.y != null) {
        const screenCoords = fgRef.current.graph2ScreenCoords(node.x, node.y);
        setTooltipPos({ x: screenCoords.x + rect.left, y: screenCoords.y + rect.top });
      }
    }
    // Suppress unused var warning
    void prevNode;
  }, []);

  // Memoized node pointer area
  const nodePointerAreaPaint = useCallback((node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
    const r = getNodeRadius(node) + 4;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
    ctx.fill();
  }, [getNodeRadius]);

  // Tooltip content
  const tooltipContent = useMemo(() => {
    if (!hoveredNode) return null;
    const cat = categories[hoveredNode.category];
    return (
      <div style={{ maxWidth: 220 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{hoveredNode.name}</div>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 4 }}>{hoveredNode.description}</div>
        <div style={{ fontSize: 11 }}>
          <span style={{ color: cat?.color || '#888' }}>{cat?.label || hoveredNode.category}</span>
          {' | '}
          <span>{hoveredNode.version}</span>
          {' | '}
          {Array.from({ length: hoveredNode.maturity }, (_, i) => (
            <StarFilled key={i} style={{ color: '#fadb14', fontSize: 10 }} />
          ))}
        </div>
      </div>
    );
  }, [hoveredNode, categories]);

  return (
    <div ref={containerRef} style={{ flex: 1, position: 'relative', background: '#1a1a2e', minWidth: 0 }}>
      <ForceGraph2D
        ref={fgRef as never}
        graphData={graphData as never}
        width={dimensions.width}
        height={dimensions.height}
        nodeCanvasObject={paintNode as never}
        nodePointerAreaPaint={nodePointerAreaPaint as never}
        linkCanvasObject={paintLink as never}
        linkCanvasObjectMode={() => 'replace'}
        onNodeHover={handleNodeHover as never}
        d3AlphaDecay={0.04}
        d3VelocityDecay={0.3}
        warmupTicks={30}
        cooldownTicks={200}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 80)}
        backgroundColor="#1a1a2e"
      />
      {hoveredNode && tooltipContent && (
        <Tooltip
          open
          title={tooltipContent}
          placement="right"
          overlayStyle={{
            position: 'fixed',
            left: tooltipPos.x,
            top: tooltipPos.y,
            pointerEvents: 'none',
          }}
        >
          <span style={{
            position: 'fixed',
            left: tooltipPos.x,
            top: tooltipPos.y,
            width: 1,
            height: 1,
            pointerEvents: 'none',
          }} />
        </Tooltip>
      )}
    </div>
  );
};
