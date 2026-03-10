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
import type { ForceNode, ForceLink } from './types';
import { EDGE_COLORS, DEFAULT_EDGE_COLOR, truncate, getNodeId } from './types';

export interface UseForceGraphCallbacksParams {
  mergedConfigs: Record<string, { color: string; radius: number; visible: boolean }>;
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  searchMatchIds: Set<string> | null;
  neighborMap: Map<string, Set<string>>;
}

export function useForceGraphCallbacks({
  mergedConfigs,
  selectedNodeId,
  hoveredNodeId,
  searchMatchIds,
  neighborMap,
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
    return true;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId, neighborMap]);

  const isLinkHighlighted = useCallback((link: ForceLink): boolean => {
    const srcId = getNodeId(link.source);
    const tgtId = getNodeId(link.target);
    if (searchMatchIds) return searchMatchIds.has(srcId) || searchMatchIds.has(tgtId);
    if (selectedNodeId) return srcId === selectedNodeId || tgtId === selectedNodeId;
    if (hoveredNodeId) return srcId === hoveredNodeId || tgtId === hoveredNodeId;
    return true;
  }, [searchMatchIds, selectedNodeId, hoveredNodeId]);

  // Canvas 繪製節點
  const paintNode = useCallback((node: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const cfg = mergedConfigs[node.type] ?? getNodeConfig(node.type);
    const baseR = cfg.radius;
    const mentionBonus = node.mention_count ? Math.min(Math.log2(node.mention_count + 1) * 1.5, 6) : 0;
    const r = baseR + mentionBonus;
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

    // 標籤 — hover/selected/搜尋匹配時一律顯示，否則依縮放層級
    const isHovered = hoveredNodeId === node.id;
    const showLabel = isSelected || isSearchMatch || isHovered || globalScale > 0.4;

    if (showLabel) {
      // hover / selected 的節點放大標籤以便閱讀
      const emphLabel = isHovered || isSelected || isSearchMatch;
      const fontSize = emphLabel
        ? Math.max(12 / globalScale, 3)
        : Math.max(10 / globalScale, 2);
      ctx.font = `${emphLabel ? 'bold ' : ''}${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      // hover / selected 加底色背景，提高可讀性
      if (emphLabel) {
        const text = truncate(node.label, 16);
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
  }, [isHighlighted, selectedNodeId, hoveredNodeId, searchMatchIds, mergedConfigs]);

  // 節點指標區域繪製
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodePointerAreaPaint = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const baseR = mergedConfigs[node.type]?.radius ?? getNodeConfig(node.type).radius;
    const r = Math.max(baseR + 4, 12);
    ctx.beginPath();
    ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }, [mergedConfigs]);

  // 邊色彩
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkColor = useCallback((link: any) => {
    if (!isLinkHighlighted(link)) return 'rgba(220,220,220,0.2)';
    return EDGE_COLORS[link.type] || DEFAULT_EDGE_COLOR;
  }, [isLinkHighlighted]);

  // 邊寬度
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkWidth = useCallback((link: any) => {
    const base = isLinkHighlighted(link) ? 1.5 : 0.5;
    const w = link.weight ?? 1;
    return base * Math.min(w, 5);
  }, [isLinkHighlighted]);

  // 箭頭色彩
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkDirectionalArrowColor = useCallback((link: any) => {
    if (!isLinkHighlighted(link)) return 'rgba(220,220,220,0.2)';
    const c = EDGE_COLORS[link.type];
    return c ? c + 'AA' : 'rgba(120,120,120,0.5)';
  }, [isLinkHighlighted]);

  // 邊標籤繪製 — 降低門檻至 0.8，且 hover 關聯的邊一律顯示
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    if (!isLinkHighlighted(link)) return;
    // hover/selected 關聯的邊一律顯示標籤，其餘須縮放 > 0.8
    const srcId = getNodeId(link.source);
    const tgtId = getNodeId(link.target);
    const isActiveEdge = srcId === selectedNodeId || tgtId === selectedNodeId
      || srcId === hoveredNodeId || tgtId === hoveredNodeId;
    if (!isActiveEdge && globalScale < 0.8) return;

    const src = link.source;
    const tgt = link.target;
    if (!src?.x || !tgt?.x) return;
    const midX = (src.x + tgt.x) / 2;
    const midY = (src.y + tgt.y) / 2;
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
