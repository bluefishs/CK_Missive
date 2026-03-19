/**
 * Force-Graph 渲染回調 Hook
 *
 * 封裝所有 Canvas 繪製邏輯：節點繪製、邊色彩/寬度、箭頭、邊標籤
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import { useCallback } from 'react';
import { getNodeConfig } from '../../../config/graphNodeConfig';
import type { ForceNode, ForceLink, ForceGraphNodeObject, ForceGraphLinkObject } from './types';
import { EDGE_COLORS, DEFAULT_EDGE_COLOR, truncate, getNodeId } from './types';

export interface UseForceGraphCallbacksParams {
  mergedConfigs: Record<string, { color: string; radius: number; visible: boolean }>;
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  searchMatchIds: Set<string> | null;
  neighborMap: Map<string, Set<string>>;
  /** 實體模式下永遠顯示標籤 */
  entityMode?: boolean;
}

export function useForceGraphCallbacks({
  mergedConfigs,
  selectedNodeId,
  hoveredNodeId,
  searchMatchIds,
  neighborMap,
  entityMode = false,
}: UseForceGraphCallbacksParams) {
  // 高亮判斷
  const isHighlighted = useCallback((nodeId: string): boolean => {
    if (searchMatchIds) return searchMatchIds.has(nodeId);
    if (selectedNodeId) {
      return nodeId === selectedNodeId || (neighborMap.get(selectedNodeId)?.has(nodeId) ?? false);
    }
    if (hoveredNodeId) {
      return nodeId === hoveredNodeId || (neighborMap.get(hoveredNodeId)?.has(nodeId) ?? false);
    }
    // 無任何選取/搜尋/hover 時，所有節點正常顯示（不淡化）
    return !entityMode;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId, neighborMap, entityMode]);

  const isLinkHighlighted = useCallback((link: ForceLink): boolean => {
    const srcId = getNodeId(link.source);
    const tgtId = getNodeId(link.target);
    if (searchMatchIds) return searchMatchIds.has(srcId) || searchMatchIds.has(tgtId);
    if (selectedNodeId) return srcId === selectedNodeId || tgtId === selectedNodeId;
    if (hoveredNodeId) return srcId === hoveredNodeId || tgtId === hoveredNodeId;
    return !entityMode;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId, entityMode]);

  // Canvas 繪製節點
  const paintNode = useCallback((node: ForceGraphNodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const cfg = mergedConfigs[node.type] ?? getNodeConfig(node.type);
    const degree = neighborMap.get(node.id)?.size ?? 0;
    const baseR = entityMode ? Math.max(cfg.radius, 7) : cfg.radius;
    const mentionBonus = node.mention_count ? Math.min(Math.log2(node.mention_count + 1) * 1.5, 6) : 0;
    // 高 degree 節點（樞紐）稍大以突顯
    const degreeBonus = degree > 50 ? 4 : degree > 20 ? 2 : 0;
    const r = baseR + mentionBonus + degreeBonus;
    const highlighted = isHighlighted(node.id);
    const isSelected = selectedNodeId === node.id;
    const isSearchMatch = searchMatchIds?.has(node.id);

    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = highlighted ? node.color : 'rgba(200,200,200,0.3)';
    ctx.fill();

    if (isSelected) {
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 2.5 / globalScale;
    } else if (isSearchMatch) {
      ctx.strokeStyle = '#ff4d4f';
      ctx.lineWidth = 2 / globalScale;
    } else {
      ctx.strokeStyle = highlighted ? 'rgba(255,255,255,0.9)' : 'rgba(200,200,200,0.2)';
      ctx.lineWidth = 1 / globalScale;
    }
    ctx.stroke();

    // 高 degree 樞紐節點：外圈光暈標示（讓使用者識別超級樞紐）
    if (highlighted && degree > 20) {
      ctx.beginPath();
      ctx.arc(x, y, r + 3 / globalScale, 0, 2 * Math.PI);
      ctx.strokeStyle = degree > 50 ? 'rgba(250,140,22,0.5)' : 'rgba(24,144,255,0.35)';
      ctx.lineWidth = 1.5 / globalScale;
      ctx.setLineDash([3 / globalScale, 2 / globalScale]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 標籤分層顯示策略：
    // L1（永遠顯示）：被選取、搜尋命中、hover
    // L2（實體模式）：mention_count 前 20%（≥3）或 1-hop 鄰居
    // L3（縮放顯示）：globalScale > 0.5 時顯示其餘
    const isHovered = hoveredNodeId === node.id;
    const isNeighbor = selectedNodeId ? (neighborMap.get(selectedNodeId)?.has(node.id) ?? false)
      : hoveredNodeId ? (neighborMap.get(hoveredNodeId)?.has(node.id) ?? false) : false;
    const isImportant = (node.mention_count ?? 0) >= 3;
    const showLabel = isSelected || isSearchMatch || isHovered
      || (entityMode && (isNeighbor || isImportant))
      || globalScale > 0.5;

    if (showLabel) {
      // hover / selected 的節點放大標籤以便閱讀
      const emphLabel = isHovered || isSelected || isSearchMatch;
      const fontSize = emphLabel
        ? Math.max(12 / globalScale, 3)
        : Math.max(10 / globalScale, 2);
      ctx.font = `${emphLabel ? 'bold ' : ''}${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      // hover / selected 加底色背景，提高可讀性；有 fullLabel 時顯示完整名稱
      if (emphLabel) {
        const text = node.fullLabel && (isHovered || isSelected)
          ? truncate(node.fullLabel, 40)
          : truncate(node.label, 16);
        const textWidth = ctx.measureText(text).width;
        const pad = 2 / globalScale;
        const bgY = y + r + 1 / globalScale;
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillRect(x - textWidth / 2 - pad, bgY - pad / 2, textWidth + pad * 2, fontSize + pad);
        ctx.fillStyle = '#222';
        ctx.fillText(text, x, bgY);
      } else {
        ctx.fillStyle = highlighted ? '#333' : 'rgba(180,180,180,0.5)';
        ctx.fillText(truncate(node.label, 14), x, y + r + 2 / globalScale);
      }
    }
  }, [isHighlighted, selectedNodeId, hoveredNodeId, searchMatchIds, mergedConfigs, entityMode, neighborMap]);

  // 節點指標區域繪製
  const nodePointerAreaPaint = useCallback((node: ForceGraphNodeObject, color: string, ctx: CanvasRenderingContext2D) => {
    const baseR = mergedConfigs[node.type]?.radius ?? getNodeConfig(node.type).radius;
    const r = Math.max(baseR + 4, 12);
    ctx.beginPath();
    ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }, [mergedConfigs]);

  // 邊色彩
  const linkColor = useCallback((link: ForceGraphLinkObject) => {
    if (!isLinkHighlighted(link)) return 'rgba(220,220,220,0.2)';
    return EDGE_COLORS[link.type] || DEFAULT_EDGE_COLOR;
  }, [isLinkHighlighted]);

  // 邊寬度
  const linkWidth = useCallback((link: ForceGraphLinkObject) => {
    const base = isLinkHighlighted(link) ? 1.5 : 0.5;
    const w = link.weight ?? 1;
    return base * Math.min(w, 5);
  }, [isLinkHighlighted]);

  // 箭頭色彩
  const linkDirectionalArrowColor = useCallback((link: ForceGraphLinkObject) => {
    if (!isLinkHighlighted(link)) return 'rgba(220,220,220,0.2)';
    const c = EDGE_COLORS[link.type];
    return c ? c + 'AA' : 'rgba(120,120,120,0.5)';
  }, [isLinkHighlighted]);

  // 邊標籤繪製 — 降低門檻至 0.8，且 hover 關聯的邊一律顯示
  const linkCanvasObject = useCallback((link: ForceGraphLinkObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
    if (!isLinkHighlighted(link)) return;
    // hover/selected 關聯的邊一律顯示標籤，其餘須縮放 > 0.8
    const srcId = getNodeId(link.source);
    const tgtId = getNodeId(link.target);
    const isActiveEdge = srcId === selectedNodeId || tgtId === selectedNodeId
      || srcId === hoveredNodeId || tgtId === hoveredNodeId;
    if (!isActiveEdge && globalScale < 0.8) return;

    const src = link.source as ForceNode | undefined;
    const tgt = link.target as ForceNode | undefined;
    if (!src?.x || !tgt?.x) return;
    const midX = (src.x + tgt.x) / 2;
    const midY = ((src.y ?? 0) + (tgt.y ?? 0)) / 2;
    const labelText = link.label || link.type || '';
    if (!labelText) return;

    const fontSize = Math.max(8 / globalScale, 1.5);
    ctx.font = `${fontSize}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // 加底色背景提高可讀性
    if (isActiveEdge) {
      const textWidth = ctx.measureText(labelText).width;
      const pad = 2 / globalScale;
      ctx.fillStyle = 'rgba(255,255,255,0.8)';
      ctx.fillRect(midX - textWidth / 2 - pad, midY - fontSize / 2 - pad - 3 / globalScale, textWidth + pad * 2, fontSize + pad * 2);
    }
    ctx.fillStyle = EDGE_COLORS[link.type] || 'rgba(100,100,100,0.7)';
    ctx.fillText(labelText, midX, midY - 3 / globalScale);
  }, [isLinkHighlighted, selectedNodeId, hoveredNodeId]);

  return {
    isHighlighted,
    paintNode,
    nodePointerAreaPaint,
    linkColor,
    linkWidth,
    linkDirectionalArrowColor,
    linkCanvasObject,
  };
}
