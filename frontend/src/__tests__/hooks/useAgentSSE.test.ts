/**
 * useAgentSSE hook 單元測試
 *
 * 測試 CK_Missive 專用的 Agent/RAG SSE wrapper。
 * 底層 useStreamingChat 已獨立測試，這裡聚焦在：
 * - Agent/RAG 模式切換
 * - draw_diagram 後處理
 * - 錯誤分類 (RATE_LIMITED → warning, others → error)
 * - context 傳遞
 *
 * @version 1.0.0
 * @created 2026-03-14
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAgentSSE } from '../../hooks/system/useAgentSSE';

// Mock dependencies
vi.mock('../../api/aiApi', () => ({
  aiApi: {
    streamAgentQuery: vi.fn(() => ({ abort: vi.fn(), signal: {} })),
    streamRAGQuery: vi.fn(() => ({ abort: vi.fn(), signal: {} })),
  },
}));

vi.mock('../../api/ai/adminManagement', () => ({
  clearAgentConversation: vi.fn(async () => {}),
}));

// Import after mock
import { aiApi } from '../../api/aiApi';
import { clearAgentConversation } from '../../api/ai/adminManagement';

describe('useAgentSSE', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==========================================================================
  // 基本初始化
  // ==========================================================================

  it('initialises with default agent mode', () => {
    const { result } = renderHook(() => useAgentSSE());

    expect(result.current.messages).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.conversationId).toBeTruthy();
  });

  it('exposes setMessages for external state manipulation', () => {
    const { result } = renderHook(() => useAgentSSE());
    expect(typeof result.current.setMessages).toBe('function');
  });

  // ==========================================================================
  // Agent 模式
  // ==========================================================================

  it('uses streamAgentQuery in agent mode', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('測試問題');
    });

    expect(aiApi.streamAgentQuery).toHaveBeenCalledTimes(1);
    expect(aiApi.streamRAGQuery).not.toHaveBeenCalled();
  });

  it('passes question and session_id to streamAgentQuery', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('公文查詢');
    });

    const callArgs = vi.mocked(aiApi.streamAgentQuery).mock.calls[0]!;
    expect(callArgs[0]).toEqual(expect.objectContaining({
      question: '公文查詢',
      session_id: expect.any(String),
    }));
  });

  it('passes context to streamAgentQuery when provided', () => {
    const { result } = renderHook(() =>
      useAgentSSE({ agentMode: true, context: 'knowledge-graph' }),
    );

    act(() => {
      result.current.sendQuestion('實體查詢');
    });

    const callArgs = vi.mocked(aiApi.streamAgentQuery).mock.calls[0]!;
    expect(callArgs[0]).toEqual(expect.objectContaining({
      context: 'knowledge-graph',
    }));
  });

  it('omits context when not provided', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('查詢');
    });

    const callArgs = vi.mocked(aiApi.streamAgentQuery).mock.calls[0]!;
    expect(callArgs[0]).not.toHaveProperty('context');
  });

  it('enables agent steps in agent mode', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('問題');
    });

    // Assistant message should have agentSteps array
    const assistantMsg = result.current.messages[1];
    expect(assistantMsg?.agentSteps).toEqual([]);
  });

  // ==========================================================================
  // RAG 模式
  // ==========================================================================

  it('uses streamRAGQuery in RAG mode', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: false }));

    act(() => {
      result.current.sendQuestion('RAG 問題');
    });

    expect(aiApi.streamRAGQuery).toHaveBeenCalledTimes(1);
    expect(aiApi.streamAgentQuery).not.toHaveBeenCalled();
  });

  it('passes fixed top_k and similarity_threshold in RAG mode', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: false }));

    act(() => {
      result.current.sendQuestion('RAG');
    });

    const callArgs = vi.mocked(aiApi.streamRAGQuery).mock.calls[0]!;
    expect(callArgs[0]).toEqual(expect.objectContaining({
      top_k: 5,
      similarity_threshold: 0.3,
    }));
  });

  it('does not set agentSteps in RAG mode', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: false }));

    act(() => {
      result.current.sendQuestion('RAG');
    });

    const assistantMsg = result.current.messages[1];
    expect(assistantMsg?.agentSteps).toBeUndefined();
  });

  // ==========================================================================
  // 錯誤分類
  // ==========================================================================

  it('classifies RATE_LIMITED as warning in agent mode', () => {
    const onError = vi.fn();
    let capturedCallbacks: Record<string, (...args: unknown[]) => unknown> = {};

    vi.mocked(aiApi.streamAgentQuery).mockImplementation((_params, cbs) => {
      capturedCallbacks = cbs as unknown as Record<string, (...args: unknown[]) => unknown>;
      return { abort: vi.fn(), signal: {} } as unknown as AbortController;
    });

    const { result } = renderHook(() => useAgentSSE({ agentMode: true, onError }));

    act(() => {
      result.current.sendQuestion('問題');
    });

    act(() => {
      capturedCallbacks.onError!('限流中', 'RATE_LIMITED');
    });

    expect(onError).toHaveBeenCalledWith('限流中', 'warning');
  });

  it('classifies STREAM_TIMEOUT as warning in agent mode', () => {
    const onError = vi.fn();
    let capturedCallbacks: Record<string, (...args: unknown[]) => unknown> = {};

    vi.mocked(aiApi.streamAgentQuery).mockImplementation((_params, cbs) => {
      capturedCallbacks = cbs as unknown as Record<string, (...args: unknown[]) => unknown>;
      return { abort: vi.fn(), signal: {} } as unknown as AbortController;
    });

    const { result } = renderHook(() => useAgentSSE({ agentMode: true, onError }));

    act(() => {
      result.current.sendQuestion('問題');
    });

    act(() => {
      capturedCallbacks.onError!('逾時', 'STREAM_TIMEOUT');
    });

    expect(onError).toHaveBeenCalledWith('逾時', 'warning');
  });

  it('classifies generic errors as error in agent mode', () => {
    const onError = vi.fn();
    let capturedCallbacks: Record<string, (...args: unknown[]) => unknown> = {};

    vi.mocked(aiApi.streamAgentQuery).mockImplementation((_params, cbs) => {
      capturedCallbacks = cbs as unknown as Record<string, (...args: unknown[]) => unknown>;
      return { abort: vi.fn(), signal: {} } as unknown as AbortController;
    });

    const { result } = renderHook(() => useAgentSSE({ agentMode: true, onError }));

    act(() => {
      result.current.sendQuestion('問題');
    });

    act(() => {
      capturedCallbacks.onError!('伺服器錯誤', 'INTERNAL_ERROR');
    });

    expect(onError).toHaveBeenCalledWith('Agent 錯誤: 伺服器錯誤', 'error');
  });

  it('classifies EMBEDDING_ERROR in RAG mode', () => {
    const onError = vi.fn();
    let capturedCallbacks: Record<string, (...args: unknown[]) => unknown> = {};

    vi.mocked(aiApi.streamRAGQuery).mockImplementation((_params, cbs) => {
      capturedCallbacks = cbs as unknown as Record<string, (...args: unknown[]) => unknown>;
      return { abort: vi.fn(), signal: {} } as unknown as AbortController;
    });

    const { result } = renderHook(() => useAgentSSE({ agentMode: false, onError }));

    act(() => {
      result.current.sendQuestion('RAG');
    });

    act(() => {
      capturedCallbacks.onError!('embedding 失敗', 'EMBEDDING_ERROR');
    });

    expect(onError).toHaveBeenCalledWith(
      '向量服務異常，請確認 Ollama 是否正常運行。',
      'error',
    );
  });

  // ==========================================================================
  // draw_diagram 後處理
  // ==========================================================================

  it('injects mermaid code into assistant message on draw_diagram', () => {
    const onDrawDiagram = vi.fn();
    let capturedCallbacks: Record<string, (...args: unknown[]) => unknown> = {};

    vi.mocked(aiApi.streamAgentQuery).mockImplementation((_params, cbs) => {
      capturedCallbacks = cbs as unknown as Record<string, (...args: unknown[]) => unknown>;
      return { abort: vi.fn(), signal: {} } as unknown as AbortController;
    });

    const { result } = renderHook(() =>
      useAgentSSE({ agentMode: true, onDrawDiagram }),
    );

    act(() => {
      result.current.sendQuestion('畫圖');
    });

    const diagramSummary = JSON.stringify({
      mermaid: 'graph TD\n  A --> B',
      title: '測試圖',
      description: '描述',
      diagram_type: 'flowchart',
    });

    act(() => {
      capturedCallbacks.onToolResult!('draw_diagram', diagramSummary, 1, 0);
    });

    // Check mermaid injected into content
    const assistantContent = result.current.messages[1]?.content ?? '';
    expect(assistantContent).toContain('```mermaid');
    expect(assistantContent).toContain('graph TD');
    expect(onDrawDiagram).toHaveBeenCalledWith(
      expect.objectContaining({ mermaid: 'graph TD\n  A --> B' }),
    );
  });

  it('handles invalid draw_diagram JSON gracefully', () => {
    let capturedCallbacks: Record<string, (...args: unknown[]) => unknown> = {};

    vi.mocked(aiApi.streamAgentQuery).mockImplementation((_params, cbs) => {
      capturedCallbacks = cbs as unknown as Record<string, (...args: unknown[]) => unknown>;
      return { abort: vi.fn(), signal: {} } as unknown as AbortController;
    });

    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('問題');
    });

    // Should not throw
    act(() => {
      capturedCallbacks.onToolResult!('draw_diagram', 'not-json', 0, 0);
    });

    expect(result.current.messages[1]?.content).toBe('');
  });

  // ==========================================================================
  // 對話管理
  // ==========================================================================

  it('clears conversation and calls backend', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('問題');
    });

    act(() => {
      result.current.clearConversation();
    });

    expect(result.current.messages).toEqual([]);
    expect(clearAgentConversation).toHaveBeenCalled();
  });

  it('does not send duplicate when loading', () => {
    const { result } = renderHook(() => useAgentSSE({ agentMode: true }));

    act(() => {
      result.current.sendQuestion('第一個');
    });

    act(() => {
      result.current.sendQuestion('第二個');
    });

    expect(aiApi.streamAgentQuery).toHaveBeenCalledTimes(1);
  });
});
