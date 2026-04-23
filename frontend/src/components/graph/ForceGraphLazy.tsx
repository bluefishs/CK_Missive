/**
 * ForceGraphLazy — react-force-graph-2d 統一 lazy wrapper（ADR-0031 Phase 4 + v6.0.1 generic 擴展）
 *
 * 消除前端 8+ 處散落的 `import ForceGraph2D from 'react-force-graph-2d'`。
 * - 單一 lazy chunk（vendor size 更可預測）
 * - 內建 Spin fallback 與 ref forward
 * - forwardRef 保留父層對 ForceGraphMethods 的操作（centerAt / zoom / d3Force）
 * - **Generic 型別**：支援自訂 NodeType / LinkType，與原始 react-force-graph-2d 的型別能力等價
 *
 * @example
 * ```tsx
 * interface MyNode { id: string; name: string; type: string; }
 * interface MyLink { source: string; target: string; relation: string; }
 *
 * const fgRef = useRef<ForceGraphMethods<MyNode, MyLink>>(null);
 * <ForceGraphLazy<MyNode, MyLink>
 *   ref={fgRef}
 *   graphData={{ nodes, links }}
 *   nodeLabel={(n) => n.name}
 *   linkLabel={(l) => l.relation}
 * />
 * ```
 *
 * @version 1.1.0 — 2026-04-23 (ADR-0031 v6.0.1 generic 擴展)
 */

import React, { Suspense, forwardRef } from 'react';
import { Spin } from 'antd';
import type {
  ForceGraphMethods,
  ForceGraphProps,
  LinkObject,
  NodeObject,
} from 'react-force-graph-2d';

// 單一 lazy import — 所有 consumer 共享同一 chunk
const ForceGraph2D = React.lazy(() => import('react-force-graph-2d'));

export type {
  ForceGraphMethods,
  ForceGraphProps,
  LinkObject,
  NodeObject,
};

// Generic wrapper props — 對應 react-force-graph-2d 原生 generic 能力
export interface ForceGraphLazyProps<N extends object = Record<string, unknown>, L extends object = Record<string, unknown>>
  extends Omit<ForceGraphProps<NodeObject<N>, LinkObject<N, L>>, 'ref'> {
  /** Suspense fallback 內容（預設為置中 Spin） */
  fallback?: React.ReactNode;
  /** Spin 提示文字 */
  loadingTip?: string;
}

const defaultFallback = (tip: string) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 320,
      width: '100%',
    }}
  >
    <Spin tip={tip} />
  </div>
);

// forwardRef 需搭配 generic — 用 explicit cast 保留型別推導
const ForceGraphLazyImpl = forwardRef<ForceGraphMethods<NodeObject, LinkObject>, ForceGraphLazyProps>(
  ({ fallback, loadingTip = '載入力導圖...', ...props }, ref) => (
    <Suspense fallback={fallback ?? defaultFallback(loadingTip)}>
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <ForceGraph2D ref={ref as any} {...(props as any)} />
    </Suspense>
  ),
);

ForceGraphLazyImpl.displayName = 'ForceGraphLazy';

/**
 * Generic-aware typed wrapper.
 *
 * TypeScript 對 `forwardRef + generic` 原生不支援，採 as-cast 模式保留型別能力：
 * ```tsx
 * <ForceGraphLazy<MyNode, MyLink> ... />
 * ```
 */
export const ForceGraphLazy = ForceGraphLazyImpl as unknown as <
  N extends object = Record<string, unknown>,
  L extends object = Record<string, unknown>,
>(
  props: ForceGraphLazyProps<N, L> & {
    ref?: React.Ref<ForceGraphMethods<NodeObject<N>, LinkObject<N, L>>>;
  },
) => React.ReactElement;

export default ForceGraphLazy;
