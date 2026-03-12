/**
 * GraphAgentBridge 單元測試
 * GraphAgentBridge Unit Tests
 *
 * 測試事件匯流排 (EventBus) 核心功能與事件型別判別
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/components/ai/knowledgeGraph/__tests__/GraphAgentBridge.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// We need to extract the class for direct testing.
// The class is not exported, so we test it indirectly via the Provider/hook,
// or we import the module and access the bus through the context.
// Strategy: import the Provider and hook, use renderHook to get context methods,
// and also test the bus instance directly through the context value.

// For direct EventBus testing, we re-create the class logic inline since
// GraphAgentEventBus is not exported. Instead, we test through the Provider.

// Actually, let's check if we can access the bus through the provider context.
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import {
  GraphAgentBridgeProvider,
  useGraphAgentBridge,
  useGraphAgentBridgeOptional,
} from '../GraphAgentBridge';
import type {
  NavigateEvent,
  SummaryResultEvent,
  DrawResultEvent,
  RequestSummaryEvent,
  RequestNavigateEvent,
} from '../GraphAgentBridge';

// ============================================================================
// Helper: create a wrapper with the Provider
// ============================================================================

function createWrapper() {
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(GraphAgentBridgeProvider, null, children);
  Wrapper.displayName = 'GraphAgentBridgeWrapper';
  return Wrapper;
}

// ============================================================================
// GraphAgentEventBus class tests (via Provider context)
// ============================================================================

describe('GraphAgentEventBus - 事件匯流排核心', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('on() subscribes a handler and returns an unsubscribe function', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    let unsubscribe: () => void;

    act(() => {
      unsubscribe = result.current.bus.on('navigate', handler);
    });

    expect(typeof unsubscribe!).toBe('function');
  });

  it('emit() calls all registered handlers for the event type', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();

    act(() => {
      result.current.bus.on('navigate', handler);
    });

    const event: NavigateEvent = {
      type: 'navigate',
      highlightIds: ['1', '2'],
      centerEntityName: 'TestEntity',
    };

    act(() => {
      result.current.bus.emit(event);
    });

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith(event);
  });

  it('emit() does not call handlers for different event types', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const navigateHandler = vi.fn();
    const summaryHandler = vi.fn();

    act(() => {
      result.current.bus.on('navigate', navigateHandler);
      result.current.bus.on('summary_result', summaryHandler);
    });

    const event: NavigateEvent = {
      type: 'navigate',
      highlightIds: ['1'],
    };

    act(() => {
      result.current.bus.emit(event);
    });

    expect(navigateHandler).toHaveBeenCalledTimes(1);
    expect(summaryHandler).not.toHaveBeenCalled();
  });

  it('unsubscribe function removes the handler', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    let unsubscribe: () => void;

    act(() => {
      unsubscribe = result.current.bus.on('navigate', handler);
    });

    act(() => {
      unsubscribe!();
    });

    act(() => {
      result.current.bus.emit({
        type: 'navigate',
        highlightIds: ['1'],
      });
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it('clear() removes all handlers', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const navigateHandler = vi.fn();
    const summaryHandler = vi.fn();

    act(() => {
      result.current.bus.on('navigate', navigateHandler);
      result.current.bus.on('summary_result', summaryHandler);
    });

    act(() => {
      result.current.bus.clear();
    });

    act(() => {
      result.current.bus.emit({ type: 'navigate', highlightIds: [] });
      result.current.bus.emit({
        type: 'summary_result',
        entityId: 1,
        entityName: 'Test',
        entityType: 'org',
      });
    });

    expect(navigateHandler).not.toHaveBeenCalled();
    expect(summaryHandler).not.toHaveBeenCalled();
  });

  it('handler errors are caught and do not crash other handlers', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const errorHandler = vi.fn(() => {
      throw new Error('Handler exploded');
    });
    const safeHandler = vi.fn();
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    act(() => {
      result.current.bus.on('navigate', errorHandler);
      result.current.bus.on('navigate', safeHandler);
    });

    act(() => {
      result.current.bus.emit({ type: 'navigate', highlightIds: ['1'] });
    });

    expect(errorHandler).toHaveBeenCalledTimes(1);
    expect(safeHandler).toHaveBeenCalledTimes(1);
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining('[GraphAgentBridge]'),
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });

  it('multiple handlers can be registered for the same event type', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler1 = vi.fn();
    const handler2 = vi.fn();
    const handler3 = vi.fn();

    act(() => {
      result.current.bus.on('request_summary', handler1);
      result.current.bus.on('request_summary', handler2);
      result.current.bus.on('request_summary', handler3);
    });

    const event: RequestSummaryEvent = {
      type: 'request_summary',
      entityId: 42,
      entityName: 'TestEntity',
      entityType: 'org',
    };

    act(() => {
      result.current.bus.emit(event);
    });

    expect(handler1).toHaveBeenCalledTimes(1);
    expect(handler2).toHaveBeenCalledTimes(1);
    expect(handler3).toHaveBeenCalledTimes(1);
    expect(handler1).toHaveBeenCalledWith(event);
  });

  it('emit() with no registered handlers does not throw', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    expect(() => {
      act(() => {
        result.current.bus.emit({ type: 'navigate', highlightIds: [] });
      });
    }).not.toThrow();
  });
});

// ============================================================================
// Event type discrimination tests
// ============================================================================

describe('Event type discrimination - 事件型別判別', () => {
  it('NavigateEvent carries highlightIds and centerEntityName', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('navigate', handler);
    });

    const event: NavigateEvent = {
      type: 'navigate',
      highlightIds: ['entity-1', 'entity-2', 'entity-3'],
      centerEntityName: 'CenterNode',
      clusterNodes: [
        { id: 1, name: 'Node1', type: 'org', mention_count: 5 },
        { id: 2, name: 'Node2', type: 'person' },
      ],
    };

    act(() => {
      result.current.bus.emit(event);
    });

    const received = handler.mock.calls[0][0] as NavigateEvent;
    expect(received.type).toBe('navigate');
    expect(received.highlightIds).toEqual(['entity-1', 'entity-2', 'entity-3']);
    expect(received.centerEntityName).toBe('CenterNode');
    expect(received.clusterNodes).toHaveLength(2);
    expect(received.clusterNodes?.[0]?.mention_count).toBe(5);
  });

  it('SummaryResultEvent carries upstream and downstream names', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('summary_result', handler);
    });

    const event: SummaryResultEvent = {
      type: 'summary_result',
      entityId: 10,
      entityName: 'TestOrg',
      entityType: 'organization',
      upstreamNames: ['ParentOrg', 'GrandParentOrg'],
      downstreamNames: ['ChildOrg'],
    };

    act(() => {
      result.current.bus.emit(event);
    });

    const received = handler.mock.calls[0][0] as SummaryResultEvent;
    expect(received.type).toBe('summary_result');
    expect(received.entityId).toBe(10);
    expect(received.entityName).toBe('TestOrg');
    expect(received.upstreamNames).toEqual(['ParentOrg', 'GrandParentOrg']);
    expect(received.downstreamNames).toEqual(['ChildOrg']);
  });

  it('DrawResultEvent carries mermaidCode and relatedEntities', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('draw_result', handler);
    });

    const event: DrawResultEvent = {
      type: 'draw_result',
      mermaidCode: 'graph TD\n  A-->B',
      diagramType: 'flowchart',
      relatedEntities: ['EntityA', 'EntityB'],
    };

    act(() => {
      result.current.bus.emit(event);
    });

    const received = handler.mock.calls[0][0] as DrawResultEvent;
    expect(received.type).toBe('draw_result');
    expect(received.mermaidCode).toContain('graph TD');
    expect(received.diagramType).toBe('flowchart');
    expect(received.relatedEntities).toEqual(['EntityA', 'EntityB']);
  });

  it('RequestSummaryEvent carries entity details', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('request_summary', handler);
    });

    const event: RequestSummaryEvent = {
      type: 'request_summary',
      entityId: 99,
      entityName: 'BridgeProject',
      entityType: 'project',
    };

    act(() => {
      result.current.bus.emit(event);
    });

    const received = handler.mock.calls[0][0] as RequestSummaryEvent;
    expect(received.type).toBe('request_summary');
    expect(received.entityId).toBe(99);
    expect(received.entityName).toBe('BridgeProject');
    expect(received.entityType).toBe('project');
  });

  it('RequestNavigateEvent carries query string and optional entityType', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('request_navigate', handler);
    });

    const event: RequestNavigateEvent = {
      type: 'request_navigate',
      query: 'find bridge projects',
      entityType: 'project',
    };

    act(() => {
      result.current.bus.emit(event);
    });

    const received = handler.mock.calls[0][0] as RequestNavigateEvent;
    expect(received.type).toBe('request_navigate');
    expect(received.query).toBe('find bridge projects');
    expect(received.entityType).toBe('project');
  });

  it('RequestNavigateEvent works without optional entityType', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('request_navigate', handler);
    });

    act(() => {
      result.current.bus.emit({
        type: 'request_navigate',
        query: 'search query',
      });
    });

    const received = handler.mock.calls[0][0] as RequestNavigateEvent;
    expect(received.entityType).toBeUndefined();
  });
});

// ============================================================================
// Context value methods tests
// ============================================================================

describe('Context methods - 便捷方法', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('navigateToCluster() emits a navigate event', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('navigate', handler);
    });

    act(() => {
      result.current.navigateToCluster({
        highlightIds: ['a', 'b'],
        centerEntityName: 'CenterEntity',
      });
    });

    expect(handler).toHaveBeenCalledTimes(1);
    const received = handler.mock.calls[0][0] as NavigateEvent;
    expect(received.type).toBe('navigate');
    expect(received.highlightIds).toEqual(['a', 'b']);
    expect(received.centerEntityName).toBe('CenterEntity');
  });

  it('sendSummaryResult() emits a summary_result event', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('summary_result', handler);
    });

    act(() => {
      result.current.sendSummaryResult({
        entityId: 5,
        entityName: 'OrgA',
        entityType: 'org',
        upstreamNames: ['Parent'],
        downstreamNames: ['Child1', 'Child2'],
      });
    });

    expect(handler).toHaveBeenCalledTimes(1);
    const received = handler.mock.calls[0][0] as SummaryResultEvent;
    expect(received.type).toBe('summary_result');
    expect(received.entityId).toBe(5);
    expect(received.upstreamNames).toEqual(['Parent']);
    expect(received.downstreamNames).toEqual(['Child1', 'Child2']);
  });

  it('sendDrawResult() emits a draw_result event', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('draw_result', handler);
    });

    act(() => {
      result.current.sendDrawResult({
        mermaidCode: 'erDiagram\n  A ||--o{ B : has',
        diagramType: 'er',
        relatedEntities: ['A', 'B'],
      });
    });

    expect(handler).toHaveBeenCalledTimes(1);
    const received = handler.mock.calls[0][0] as DrawResultEvent;
    expect(received.type).toBe('draw_result');
    expect(received.mermaidCode).toContain('erDiagram');
    expect(received.diagramType).toBe('er');
    expect(received.relatedEntities).toEqual(['A', 'B']);
  });

  it('requestSummary() emits a request_summary event with entity details', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('request_summary', handler);
    });

    act(() => {
      result.current.requestSummary(42, 'TestEntity', 'person');
    });

    expect(handler).toHaveBeenCalledTimes(1);
    const received = handler.mock.calls[0][0] as RequestSummaryEvent;
    expect(received.type).toBe('request_summary');
    expect(received.entityId).toBe(42);
    expect(received.entityName).toBe('TestEntity');
    expect(received.entityType).toBe('person');
  });

  it('requestNavigate() emits a request_navigate event with query', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('request_navigate', handler);
    });

    act(() => {
      result.current.requestNavigate('find related entities', 'org');
    });

    expect(handler).toHaveBeenCalledTimes(1);
    const received = handler.mock.calls[0][0] as RequestNavigateEvent;
    expect(received.type).toBe('request_navigate');
    expect(received.query).toBe('find related entities');
    expect(received.entityType).toBe('org');
  });

  it('requestNavigate() works without entityType parameter', () => {
    const { result } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const handler = vi.fn();
    act(() => {
      result.current.bus.on('request_navigate', handler);
    });

    act(() => {
      result.current.requestNavigate('simple query');
    });

    const received = handler.mock.calls[0][0] as RequestNavigateEvent;
    expect(received.entityType).toBeUndefined();
  });
});

// ============================================================================
// Hook edge cases
// ============================================================================

describe('useGraphAgentBridge hook - 邊界情況', () => {
  it('throws error when used outside Provider', () => {
    // Suppress console.error from React for expected error
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useGraphAgentBridge());
    }).toThrow('useGraphAgentBridge must be used within GraphAgentBridgeProvider');

    consoleErrorSpy.mockRestore();
  });

  it('useGraphAgentBridgeOptional returns null when used outside Provider', () => {
    const { result } = renderHook(() => useGraphAgentBridgeOptional());

    expect(result.current).toBeNull();
  });

  it('useGraphAgentBridgeOptional returns context value when used inside Provider', () => {
    const { result } = renderHook(() => useGraphAgentBridgeOptional(), {
      wrapper: createWrapper(),
    });

    expect(result.current).not.toBeNull();
    expect(result.current!.bus).toBeDefined();
    expect(typeof result.current!.navigateToCluster).toBe('function');
    expect(typeof result.current!.sendSummaryResult).toBe('function');
    expect(typeof result.current!.sendDrawResult).toBe('function');
    expect(typeof result.current!.requestSummary).toBe('function');
    expect(typeof result.current!.requestNavigate).toBe('function');
  });
});

// ============================================================================
// Bus instance stability
// ============================================================================

describe('Bus instance stability - 匯流排實例穩定性', () => {
  it('bus instance remains the same across re-renders', () => {
    const { result, rerender } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const bus1 = result.current.bus;
    rerender();
    const bus2 = result.current.bus;

    expect(bus1).toBe(bus2);
  });

  it('context methods remain stable across re-renders (memoized)', () => {
    const { result, rerender } = renderHook(() => useGraphAgentBridge(), {
      wrapper: createWrapper(),
    });

    const methods1 = {
      navigateToCluster: result.current.navigateToCluster,
      sendSummaryResult: result.current.sendSummaryResult,
      sendDrawResult: result.current.sendDrawResult,
      requestSummary: result.current.requestSummary,
      requestNavigate: result.current.requestNavigate,
    };

    rerender();

    expect(result.current.navigateToCluster).toBe(methods1.navigateToCluster);
    expect(result.current.sendSummaryResult).toBe(methods1.sendSummaryResult);
    expect(result.current.sendDrawResult).toBe(methods1.sendDrawResult);
    expect(result.current.requestSummary).toBe(methods1.requestSummary);
    expect(result.current.requestNavigate).toBe(methods1.requestNavigate);
  });
});
