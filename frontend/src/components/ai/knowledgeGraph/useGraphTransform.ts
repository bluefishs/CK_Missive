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
import { SOURCE_PROJECT_COLORS } from '../../../config/graphNodeConfig';
import type { ForceNode, GraphData } from './types';

export type ColorByMode = 'type' | 'source_project';

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
  colorBy?: ColorByMode;
  visibleSourceProjects?: Set<string>;
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
  colorBy = 'type',
  visibleSourceProjects,
}: UseGraphTransformParams): UseGraphTransformReturn {
  // 轉換為 force-graph 格式
  const graphData = useMemo((): GraphData => {
    const isEntityMode = viewMode === 'entity';

    const typeFiltered = rawNodes.filter((n) => {
      if (!visibleTypes.has(n.type)) return false;
      const cfg = mergedConfigs[n.type];
      if (cfg && !cfg.visible) return false;
      if (visibleSourceProjects && visibleSourceProjects.size > 0) {
        const proj = n.source_project ?? 'ck-missive';
        if (!visibleSourceProjects.has(proj)) return false;
      }
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
      .map((n) => {
        const typeColor = mergedConfigs[n.type]?.color ?? effectiveGetNodeConfig(n.type).color;
        const projectColor = n.source_project
          ? SOURCE_PROJECT_COLORS[n.source_project] ?? typeColor
          : typeColor;
        return {
          id: n.id,
          label: n.label,
          fullLabel: n.fullLabel ?? undefined,
          type: n.type,
          color: colorBy === 'source_project' ? projectColor : typeColor,
          category: n.category,
          doc_number: n.doc_number,
          status: n.status,
          mention_count: n.mention_count ?? undefined,
          source_project: n.source_project ?? undefined,
        };
      });

    // 2026-09-07 owner 回報 console：`<line> attribute x1: Expected length, "NaN"`。
    // 正常登入下重現不出來 —— 同一份 console 上方有一則 401，兩者是同一件事：
    // **API 回 401 ⇒ 節點抓不到、邊卻還在 ⇒ 連線指向不存在的節點 ⇒ 座標 undefined ⇒ NaN**。
    // 力導向圖不會為此報錯，它只會畫出 NaN 座標的線，於是錯誤看起來像繪圖套件壞了。
    //
    // 兩道防線（都便宜）：
    //   ① 節點 id 去重 —— 重複 id 會讓 force-graph 綁到另一個物件
    //   ② 連線只保留「兩端都在最終節點集合裡」的 —— 上面的過濾用的是 typeFiltered，
    //      而節點在 entity 模式下還會再被篩一次，兩者不同步時就會漏
    const finalIds = new Set<string>();
    const dedupedNodes: ForceNode[] = [];
    for (const n of nodes) {
      if (!n.id || finalIds.has(n.id)) continue;
      finalIds.add(n.id);
      dedupedNodes.push(n);
    }
    const safeLinks = links.filter((l) => finalIds.has(l.source) && finalIds.has(l.target));

    return { nodes: dedupedNodes, links: safeLinks };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawNodes, rawEdges, visibleTypes, mergedConfigs, viewMode, colorBy, visibleSourceProjects]);

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
