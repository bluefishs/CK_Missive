/**
 * useGraphTransform - 圖譜資料轉換 Hook
 *
 * 負責：
 * - 將 rawNodes/rawEdges 轉為 force-graph GraphData
 * - 類型過濾 + entity 模式孤立節點過濾
 * - neighborMap 鄰居查詢表
 * - nodeByLabel 標籤查詢表
 *
 * @version 1.0.0
 * @created 2026-03-18
 */

import { useMemo } from 'react';
import type { GraphNode, GraphEdge } from '../../../types/ai';
import type { GraphNodeTypeConfig } from '../../../config/graphNodeConfig';
import type { ForceNode, GraphData } from './types';

interface MergedConfig extends GraphNodeTypeConfig {
  visible: boolean;
}

interface UseGraphTransformParams {
  rawNodes: GraphNode[];
  rawEdges: GraphEdge[];
  visibleTypes: Set<string>;
  mergedConfigs: Record<string, MergedConfig>;
  viewMode: 'entity' | 'full';
  effectiveGetNodeConfig: (type: string) => GraphNodeTypeConfig;
}

interface UseGraphTransformReturn {
  graphData: GraphData;
  neighborMap: Map<string, Set<string>>;
  nodeByLabel: Map<string, ForceNode>;
}

export function useGraphTransform({
  rawNodes,
  rawEdges,
  visibleTypes,
  mergedConfigs,
  viewMode,
  effectiveGetNodeConfig,
}: UseGraphTransformParams): UseGraphTransformReturn {
  // 轉換為 force-graph 格式
  const graphData = useMemo((): GraphData => {
    const isEntityMode = viewMode === 'entity';

    const typeFiltered = rawNodes.filter((n) => {
      if (!visibleTypes.has(n.type)) return false;
      const cfg = mergedConfigs[n.type];
      if (cfg && !cfg.visible) return false;
      return true;
    });
    const typeFilteredIds = new Set(typeFiltered.map((n) => n.id));

    const links = rawEdges
      .filter((e) => typeFilteredIds.has(e.source) && typeFilteredIds.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
        type: e.type,
        weight: e.weight ?? undefined,
      }));

    const connectedIds = new Set<string>();
    for (const link of links) {
      connectedIds.add(link.source);
      connectedIds.add(link.target);
    }

    const nodes: ForceNode[] = typeFiltered
      .filter((n) => !isEntityMode || connectedIds.has(n.id))
      .map((n) => ({
        id: n.id,
        label: n.label,
        fullLabel: n.fullLabel ?? undefined,
        type: n.type,
        color: mergedConfigs[n.type]?.color ?? effectiveGetNodeConfig(n.type).color,
        category: n.category,
        doc_number: n.doc_number,
        status: n.status,
        mention_count: n.mention_count ?? undefined,
      }));

    return { nodes, links };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawNodes, rawEdges, visibleTypes, mergedConfigs, viewMode]);

  // 鄰居 lookup
  const neighborMap = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const link of graphData.links) {
      const src = typeof link.source === 'string' ? link.source : (link.source as { id: string }).id;
      const tgt = typeof link.target === 'string' ? link.target : (link.target as { id: string }).id;
      if (!map.has(src)) map.set(src, new Set());
      if (!map.has(tgt)) map.set(tgt, new Set());
      map.get(src)!.add(tgt);
      map.get(tgt)!.add(src);
    }
    return map;
  }, [graphData.links]);

  const nodeByLabel = useMemo(() => {
    const map = new Map<string, ForceNode>();
    for (const n of graphData.nodes) {
      map.set(n.label, n);
    }
    return map;
  }, [graphData.nodes]);

  return { graphData, neighborMap, nodeByLabel };
}
