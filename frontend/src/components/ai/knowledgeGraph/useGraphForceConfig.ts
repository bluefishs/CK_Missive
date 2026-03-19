import { useEffect } from 'react';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import { forceCollide, forceX, forceY } from 'd3-force';
import type { MergedNodeConfig } from '../../../config/graphNodeConfig';
import type { GraphViewMode } from './GraphToolbar';
import type { GraphData, D3SimNode } from './types';

interface UseGraphForceConfigParams {
  fgRef: React.RefObject<ForceGraphMethods | undefined>;
  graphData: GraphData;
  viewMode: GraphViewMode;
  mergedConfigs: Record<string, MergedNodeConfig>;
}

export function useGraphForceConfig({
  fgRef,
  graphData,
  viewMode,
  mergedConfigs,
}: UseGraphForceConfigParams) {
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const nodeCount = graphData.nodes.length;
    const isEntityView = viewMode === 'entity';

    // 建立 degree 索引
    const degreeMap: Record<string, number> = {};
    for (const link of graphData.links) {
      const src = typeof link.source === 'string' ? link.source : (link.source as { id: string }).id;
      const tgt = typeof link.target === 'string' ? link.target : (link.target as { id: string }).id;
      degreeMap[src] = (degreeMap[src] ?? 0) + 1;
      degreeMap[tgt] = (degreeMap[tgt] ?? 0) + 1;
    }

    // 向心力
    fg.d3Force('center')?.strength?.(isEntityView ? 0.03 : 0.05);
    // 連結距離
    fg.d3Force('link')?.distance?.((link: { source: string | { id?: string | number }; target: string | { id?: string | number } }) => {
      const srcId = String(typeof link.source === 'string' ? link.source : link.source?.id ?? '');
      const tgtId = String(typeof link.target === 'string' ? link.target : link.target?.id ?? '');
      const maxDeg = Math.max(degreeMap[srcId] ?? 0, degreeMap[tgtId] ?? 0);
      if (!isEntityView) return nodeCount > 200 ? 30 : nodeCount > 50 ? 50 : 80;
      if (maxDeg > 50) return 120;
      if (maxDeg > 20) return 90;
      return nodeCount > 80 ? 60 : 100;
    });
    // 排斥力
    fg.d3Force('charge')?.strength?.((node: D3SimNode) => {
      const deg = degreeMap[node.id] ?? 0;
      if (!isEntityView) return nodeCount > 200 ? -30 : nodeCount > 50 ? -60 : -100;
      if (deg > 50) return -300;
      if (deg > 20) return -150;
      return nodeCount > 80 ? -80 : -120;
    });

    // 碰撞偵測
    fg.d3Force('collide', forceCollide<D3SimNode>((node: D3SimNode) => {
      const cfg = mergedConfigs[node.type];
      const baseR = isEntityView ? Math.max(cfg?.radius ?? 5, 7) : (cfg?.radius ?? 5);
      const mentionBonus = node.mention_count ? Math.min(Math.log2(node.mention_count + 1) * 1.5, 6) : 0;
      const deg = degreeMap[node.id] ?? 0;
      const degBonus = deg > 50 ? 10 : deg > 20 ? 5 : 0;
      return baseR + mentionBonus + degBonus + (isEntityView ? 6 : 3);
    }) as never);

    // 類型分群佈局
    if (isEntityView) {
      const typeSet = [...new Set(graphData.nodes.map((n) => n.type))];
      const typeAngle: Record<string, number> = {};
      typeSet.forEach((t, i) => { typeAngle[t] = (2 * Math.PI * i) / typeSet.length; });
      const clusterR = Math.min(nodeCount * 1.2, 350);
      fg.d3Force('clusterX', forceX<D3SimNode>((node: D3SimNode) => Math.cos(typeAngle[node.type] ?? 0) * clusterR).strength(0.15) as never);
      fg.d3Force('clusterY', forceY<D3SimNode>((node: D3SimNode) => Math.sin(typeAngle[node.type] ?? 0) * clusterR).strength(0.15) as never);
    } else {
      fg.d3Force('clusterX', null);
      fg.d3Force('clusterY', null);
    }
    fg.d3ReheatSimulation();
  }, [graphData, viewMode, mergedConfigs, fgRef]);
}
