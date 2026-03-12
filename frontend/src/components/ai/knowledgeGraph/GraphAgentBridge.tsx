/**
 * GraphAgentBridge — 圖譜 ↔ AI Agent 雙向通訊橋接層
 *
 * 三位一體整合核心：
 * 1. Agent → Graph: navigate_graph 結果 → 圖譜 fly-to + 高亮叢集
 * 2. Graph → Agent: 節點點擊 → 觸發 summarize_entity 問答
 * 3. Graph → Agent: 搜尋 → 觸發 navigate_graph 定位
 *
 * 設計原則：
 * - 使用 React Context + EventEmitter 模式（非 prop drilling）
 * - 單一事件匯流排，雙向解耦
 * - 支援多消費者（同一事件可被 Graph 和 Chat 同時監聽）
 *
 * @version 1.0.0
 * @created 2026-03-10
 */

import React, { createContext, useContext, useCallback, useRef, useMemo } from 'react';

// ============================================================================
// 事件型別
// ============================================================================

/** Agent → Graph：導航至指定叢集 */
export interface NavigateEvent {
  type: 'navigate';
  /** 要高亮的實體 ID 列表 */
  highlightIds: string[];
  /** 中心實體（fly-to 目標） */
  centerEntityName?: string;
  /** 叢集節點（展開鄰居後的完整列表） */
  clusterNodes?: Array<{
    id: number;
    name: string;
    type: string;
    mention_count?: number;
  }>;
}

/** Agent → Graph：摘要結果（可選的圖譜高亮） */
export interface SummaryResultEvent {
  type: 'summary_result';
  entityId: number;
  entityName: string;
  entityType: string;
  /** 上游實體名稱（圖譜中可高亮連線） */
  upstreamNames?: string[];
  /** 下游實體名稱 */
  downstreamNames?: string[];
}

/** Graph → Agent：用戶點擊節點，請求 Agent 生成摘要 */
export interface RequestSummaryEvent {
  type: 'request_summary';
  entityId: number;
  entityName: string;
  entityType: string;
}

/** Graph → Agent：用戶在圖譜搜尋，請求 Agent 導航 */
export interface RequestNavigateEvent {
  type: 'request_navigate';
  query: string;
  entityType?: string;
}

/** Agent → Graph：draw_diagram 結果，高亮相關節點 */
export interface DrawResultEvent {
  type: 'draw_result';
  /** Mermaid 語法 */
  mermaidCode: string;
  /** 圖表類型 */
  diagramType: 'er' | 'flowchart' | 'classDiagram' | 'dependency';
  /** 圖中涉及的實體名稱（用於圖譜高亮） */
  relatedEntities: string[];
}

export type BridgeEvent =
  | NavigateEvent
  | SummaryResultEvent
  | RequestSummaryEvent
  | RequestNavigateEvent
  | DrawResultEvent;

type BridgeEventType = BridgeEvent['type'];
type EventHandler<T extends BridgeEvent = BridgeEvent> = (event: T) => void;

// ============================================================================
// Bridge 實作
// ============================================================================

class GraphAgentEventBus {
  private listeners = new Map<BridgeEventType, Set<EventHandler>>();

  on<T extends BridgeEvent>(type: T['type'], handler: EventHandler<T>): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    const handlers = this.listeners.get(type)!;
    handlers.add(handler as EventHandler);

    // 回傳 unsubscribe 函式
    return () => {
      handlers.delete(handler as EventHandler);
    };
  }

  emit<T extends BridgeEvent>(event: T): void {
    const handlers = this.listeners.get(event.type);
    if (!handlers) return;
    for (const handler of handlers) {
      try {
        handler(event);
      } catch (e) {
        console.error(`[GraphAgentBridge] Error in ${event.type} handler:`, e);
      }
    }
  }

  clear(): void {
    this.listeners.clear();
  }
}

// ============================================================================
// React Context
// ============================================================================

export interface GraphAgentBridgeContextValue {
  /** 事件匯流排（雙向通訊） */
  bus: GraphAgentEventBus;
  /** Agent → Graph: 發送導航事件 */
  navigateToCluster: (event: Omit<NavigateEvent, 'type'>) => void;
  /** Agent → Graph: 發送摘要結果 */
  sendSummaryResult: (event: Omit<SummaryResultEvent, 'type'>) => void;
  /** Agent → Graph: 發送 draw_diagram 結果 */
  sendDrawResult: (event: Omit<DrawResultEvent, 'type'>) => void;
  /** Graph → Agent: 請求生成摘要 */
  requestSummary: (entityId: number, entityName: string, entityType: string) => void;
  /** Graph → Agent: 請求導航 */
  requestNavigate: (query: string, entityType?: string) => void;
}

const GraphAgentBridgeContext = createContext<GraphAgentBridgeContextValue | null>(null);

// ============================================================================
// Provider
// ============================================================================

export const GraphAgentBridgeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const busRef = useRef(new GraphAgentEventBus());
  const bus = busRef.current;

  const navigateToCluster = useCallback((event: Omit<NavigateEvent, 'type'>) => {
    bus.emit({ ...event, type: 'navigate' });
  }, [bus]);

  const sendSummaryResult = useCallback((event: Omit<SummaryResultEvent, 'type'>) => {
    bus.emit({ ...event, type: 'summary_result' });
  }, [bus]);

  const requestSummary = useCallback((entityId: number, entityName: string, entityType: string) => {
    bus.emit({ type: 'request_summary', entityId, entityName, entityType });
  }, [bus]);

  const requestNavigate = useCallback((query: string, entityType?: string) => {
    bus.emit({ type: 'request_navigate', query, entityType });
  }, [bus]);

  const sendDrawResult = useCallback((event: Omit<DrawResultEvent, 'type'>) => {
    bus.emit({ ...event, type: 'draw_result' });
  }, [bus]);

  const value = useMemo<GraphAgentBridgeContextValue>(() => ({
    bus,
    navigateToCluster,
    sendSummaryResult,
    sendDrawResult,
    requestSummary,
    requestNavigate,
  }), [bus, navigateToCluster, sendSummaryResult, sendDrawResult, requestSummary, requestNavigate]);

  return (
    <GraphAgentBridgeContext.Provider value={value}>
      {children}
    </GraphAgentBridgeContext.Provider>
  );
};

// ============================================================================
// Hook
// ============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export function useGraphAgentBridge(): GraphAgentBridgeContextValue {
  const ctx = useContext(GraphAgentBridgeContext);
  if (!ctx) {
    throw new Error('useGraphAgentBridge must be used within GraphAgentBridgeProvider');
  }
  return ctx;
}

/**
 * 可選式 hook（不在 Provider 內時回傳 null，不拋錯）
 * 用於 KnowledgeGraph / RAGChatPanel 等可獨立使用也可整合使用的元件
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useGraphAgentBridgeOptional(): GraphAgentBridgeContextValue | null {
  return useContext(GraphAgentBridgeContext);
}
