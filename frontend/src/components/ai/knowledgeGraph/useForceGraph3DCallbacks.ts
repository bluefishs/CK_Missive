/**
 * Force-Graph 3D 渲染回調 Hook
 *
 * 3D 版本使用 Three.js Sprite 渲染節點標籤，
 * 節點顏色/大小/高亮邏輯與 2D 版共用。
 *
 * @version 1.0.0
 * @created 2026-03-10
 */

import { useCallback } from 'react';
import * as THREE from 'three';
import SpriteText from 'three-spritetext';
import { getNodeConfig } from '../../../config/graphNodeConfig';
import type { ForceNode, ForceLink } from './types';
import { EDGE_COLORS, DEFAULT_EDGE_COLOR, truncate, getNodeId } from './types';

export interface UseForceGraph3DCallbacksParams {
  mergedConfigs: Record<string, { color: string; radius: number; visible: boolean }>;
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  searchMatchIds: Set<string> | null;
  neighborMap: Map<string, Set<string>>;
}

export function useForceGraph3DCallbacks({
  mergedConfigs,
  selectedNodeId,
  hoveredNodeId,
  searchMatchIds,
  neighborMap,
}: UseForceGraph3DCallbacksParams) {
  // 高亮判斷（與 2D 版共用邏輯）
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

  // 3D 節點物件 — 球體 + 文字標籤（效能優化版）
  const nodeThreeObject = useCallback((node: ForceNode) => {
    const cfg = mergedConfigs[node.type] ?? getNodeConfig(node.type);
    const highlighted = isHighlighted(node.id);
    const isSelected = selectedNodeId === node.id;
    const isSearchMatch = searchMatchIds?.has(node.id);

    // 根據 mention_count 調整大小
    const mentionBonus = node.mention_count ? Math.min(Math.log2(node.mention_count + 1) * 1.5, 6) : 0;
    const radius = cfg.radius + mentionBonus;

    // 降低幾何精度：高亮節點 12/8 segments，其餘 8/6（大幅減少三角面數）
    const segments = highlighted ? 12 : 8;
    const rings = highlighted ? 8 : 6;
    const geometry = new THREE.SphereGeometry(radius, segments, rings);
    const color = highlighted ? node.color : '#c8c8c8';
    const opacity = highlighted ? 0.9 : 0.3;
    const material = new THREE.MeshLambertMaterial({
      color,
      transparent: true,
      opacity,
    });
    const sphere = new THREE.Mesh(geometry, material);

    // 外框光暈 (selected / search match)
    if (isSelected || isSearchMatch) {
      const glowGeom = new THREE.SphereGeometry(radius * 1.3, 8, 6);
      const glowColor = isSelected ? '#333333' : '#ff4d4f';
      const glowMat = new THREE.MeshBasicMaterial({
        color: glowColor,
        transparent: true,
        opacity: 0.25,
      });
      const glow = new THREE.Mesh(glowGeom, glowMat);
      sphere.add(glow);
    }

    // 文字標籤 — 僅高亮/選中/搜尋命中節點顯示（大幅降低 SpriteText 數量）
    if (highlighted || isSelected || isSearchMatch) {
      const sprite = new SpriteText(truncate(node.label, 14));
      sprite.color = highlighted ? '#222' : '#aaa';
      sprite.textHeight = isSelected || isSearchMatch ? 4 : 3;
      sprite.position.y = -(radius + 3);
      sprite.backgroundColor = isSelected ? 'rgba(255,255,255,0.85)' : 'transparent';
      sprite.padding = isSelected ? 1 : 0;
      sprite.borderRadius = 2;
      sphere.add(sprite);
    }

    return sphere;
  }, [mergedConfigs, isHighlighted, selectedNodeId, searchMatchIds]);

  // 邊色彩
  const linkColor = useCallback((link: ForceLink) => {
    if (!isLinkHighlighted(link)) return 'rgba(220,220,220,0.15)';
    return EDGE_COLORS[link.type] || DEFAULT_EDGE_COLOR;
  }, [isLinkHighlighted]);

  // 邊寬度
  const linkWidth = useCallback((link: ForceLink) => {
    const base = isLinkHighlighted(link) ? 1.5 : 0.3;
    const w = (link.weight ?? 1);
    return base * Math.min(w, 5);
  }, [isLinkHighlighted]);

  // 邊標籤（3D 使用 SpriteText）
  const linkThreeObject = useCallback((link: ForceLink) => {
    if (!isLinkHighlighted(link)) return new THREE.Object3D();
    const label = (link as { label?: string }).label || (link as { type?: string }).type || '';
    if (!label) return new THREE.Object3D();

    const sprite = new SpriteText(label);
    sprite.color = EDGE_COLORS[link.type] || '#888';
    sprite.textHeight = 2;
    sprite.backgroundColor = 'rgba(255,255,255,0.6)';
    sprite.padding = 0.5;
    sprite.borderRadius = 1;
    return sprite;
  }, [isLinkHighlighted]);

  // 邊標籤位置更新（放在邊的中點）
  const linkPositionUpdate = useCallback(
    (sprite: THREE.Object3D, coords: { start: { x: number; y: number; z: number }; end: { x: number; y: number; z: number } }) => {
      if (!coords.start || !coords.end) return false;
      sprite.position.x = (coords.start.x + coords.end.x) / 2;
      sprite.position.y = (coords.start.y + coords.end.y) / 2;
      sprite.position.z = (coords.start.z + coords.end.z) / 2;
      return true;
    },
    [],
  );

  // 箭頭色彩
  const linkDirectionalArrowColor = useCallback((link: ForceLink) => {
    if (!isLinkHighlighted(link)) return 'rgba(220,220,220,0.15)';
    const c = EDGE_COLORS[link.type];
    return c ? c + 'AA' : 'rgba(120,120,120,0.5)';
  }, [isLinkHighlighted]);

  return {
    isHighlighted,
    nodeThreeObject,
    linkColor,
    linkWidth,
    linkThreeObject,
    linkPositionUpdate,
    linkDirectionalArrowColor,
  };
}
