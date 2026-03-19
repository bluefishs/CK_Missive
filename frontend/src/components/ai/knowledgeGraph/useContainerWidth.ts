/**
 * useContainerWidth - 容器寬度偵測 Hook
 *
 * 負責：
 * - ResizeObserver 自動偵測容器寬度
 * - 外部寬度覆蓋
 * - 側邊欄開關時的有效寬度計算
 * - 寬度變化後自動 zoomToFit
 *
 * @version 1.0.0
 * @created 2026-03-18
 */

import { useState, useEffect, useRef } from 'react';
import type { ForceGraphMethods } from 'react-force-graph-2d';

const SIDEBAR_WIDTH = 380;

interface UseContainerWidthParams {
  externalWidth?: number;
  sidebarVisible: boolean;
  fgRef: React.MutableRefObject<ForceGraphMethods | undefined>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fg3dRef: React.MutableRefObject<any>;
  dimension: '2d' | '3d';
  rawNodesLength: number;
}

interface UseContainerWidthReturn {
  containerRef: React.MutableRefObject<HTMLDivElement | null>;
  effectiveWidth: number;
}

export function useContainerWidth({
  externalWidth,
  sidebarVisible,
  fgRef,
  fg3dRef,
  dimension,
  rawNodesLength,
}: UseContainerWidthParams): UseContainerWidthReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  // 容器寬度偵測
  useEffect(() => {
    if (externalWidth != null) return;
    const el = containerRef.current;
    if (!el) return;

    const measure = () => {
      const w = el.clientWidth;
      if (w > 0) setContainerWidth(w);
    };

    const observer = new ResizeObserver(() => measure());
    observer.observe(el);
    window.addEventListener('resize', measure);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [externalWidth]);

  useEffect(() => {
    if (externalWidth != null && externalWidth > 0) {
      setContainerWidth(externalWidth);
    }
  }, [externalWidth]);

  const effectiveWidth = Math.max(
    (containerWidth - (sidebarVisible ? SIDEBAR_WIDTH : 0)) - 2,
    300,
  );

  // 寬度變化後自動 zoomToFit
  const prevEffectiveWidthRef = useRef(effectiveWidth);
  useEffect(() => {
    const delta = Math.abs(effectiveWidth - prevEffectiveWidthRef.current);
    prevEffectiveWidthRef.current = effectiveWidth;
    if (delta <= 10 || rawNodesLength === 0) return;
    const t = setTimeout(() => {
      fgRef.current?.zoomToFit(400, 40);
      if (dimension === '3d') fg3dRef.current?.zoomToFit(400, 40);
    }, 300);
    return () => clearTimeout(t);
  }, [effectiveWidth, rawNodesLength, dimension, fgRef, fg3dRef]);

  return { containerRef, effectiveWidth };
}
