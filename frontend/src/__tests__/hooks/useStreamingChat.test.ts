/**
 * useStreamingChat hook 單元測試
 *
 * @version 1.0.0
 * @created 2026-03-14
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStreamingChat, type StreamingChatCallbacks, type StreamingChatAPIs } from '../../hooks/system/useStreamingChat';

// Mock AbortController
const mockAbort = vi.fn();
const mockAbortController = { abort: mockAbort, signal: {} as AbortSignal } as AbortController;

function createMockAPIs(overrides: Partial<StreamingChatAPIs> = {}): StreamingChatAPIs {
  return {
    startStream: vi.fn(() => mockAbortController),
    clearConversation: vi.fn(async () => {}),
    ...overrides,
  };
}

describe('useStreamingChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initialises with empty messages and not loading', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() => useStreamingChat({ apis }));

    expect(result.current.messages).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.conversationId).toBeTruthy();
  });

  it('generates a unique conversationId', () => {
    const apis = createMockAPIs();
    const { result: r1 } = renderHook(() => useStreamingChat({ apis }));
    const { result: r2 } = renderHook(() => useStreamingChat({ apis }));
    expect(r1.current.conversationId).not.toBe(r2.current.conversationId);
  });

  it('accepts custom session ID generator', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() =>
      useStreamingChat({ apis, generateSessionId: () => 'fixed-id-123' })
    );
    expect(result.current.conversationId).toBe('fixed-id-123');
  });

  it('sends a message and transitions to loading state', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() => useStreamingChat({ apis, enableAgentSteps: true }));

    act(() => {
      result.current.sendMessage('測試問題');
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]!.role).toBe('user');
    expect(result.current.messages[0]!.content).toBe('測試問題');
    expect(result.current.messages[1]!.role).toBe('assistant');
    expect(result.current.messages[1]!.streaming).toBe(true);
    expect(result.current.messages[1]!.agentSteps).toEqual([]);
  });

  it('ignores empty messages', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('');
    });

    expect(result.current.messages).toHaveLength(0);
    expect(apis.startStream).not.toHaveBeenCalled();
  });

  it('ignores messages while loading', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('第一個問題');
    });

    act(() => {
      result.current.sendMessage('第二個問題');
    });

    // Only first message should be sent
    expect(apis.startStream).toHaveBeenCalledTimes(1);
  });

  it('passes context to startStream', () => {
    const apis = createMockAPIs();
    renderHook(() => useStreamingChat({ apis, context: 'knowledge-graph' }));

    // We need to trigger a send to see context being passed
    const { result } = renderHook(() => useStreamingChat({ apis, context: 'knowledge-graph' }));
    act(() => {
      result.current.sendMessage('test');
    });

    expect(apis.startStream).toHaveBeenCalledWith(
      expect.objectContaining({ context: 'knowledge-graph' }),
      expect.any(Object),
    );
  });

  it('handles onToken callback to accumulate content', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onToken('你');
      capturedCallbacks!.onToken('好');
    });

    expect(result.current.messages[1]!.content).toBe('你好');
  });

  it('handles onThinking callback', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis, enableAgentSteps: true }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onThinking!('分析意圖中...', 0);
    });

    const steps = result.current.messages[1]!.agentSteps!;
    expect(steps).toHaveLength(1);
    expect(steps[0]!.type).toBe('thinking');
    expect(steps[0]!.step).toBe('分析意圖中...');
  });

  it('handles onReact callback with confidence and action', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis, enableAgentSteps: true }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onReact!('結果不足，嘗試擴展搜尋', 1, 0.35, 'continue');
    });

    const steps = result.current.messages[1]!.agentSteps!;
    expect(steps).toHaveLength(1);
    expect(steps[0]!.type).toBe('react');
    expect(steps[0]!.confidence).toBe(0.35);
    expect(steps[0]!.action).toBe('continue');
  });

  it('handles onToolCall and onToolResult callbacks', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis, enableAgentSteps: true }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onToolCall!('search_documents', { keywords: ['公文'] }, 0);
      capturedCallbacks!.onToolResult!('search_documents', '找到 5 筆結果', 5, 1);
    });

    const steps = result.current.messages[1]!.agentSteps!;
    expect(steps).toHaveLength(2);
    expect(steps[0]!.type).toBe('tool_call');
    expect(steps[0]!.tool).toBe('search_documents');
    expect(steps[1]!.type).toBe('tool_result');
    expect(steps[1]!.count).toBe(5);
  });

  it('handles onDone callback to finish streaming', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onDone(1200, 'groq-llama', ['search_documents'], 2);
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.messages[1]!.streaming).toBe(false);
    expect(result.current.messages[1]!.latency_ms).toBe(1200);
    expect(result.current.messages[1]!.model).toBe('groq-llama');
  });

  it('handles onError callback', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const onError = vi.fn();
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis, onError }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onError!('API 超時', 'timeout');
    });

    expect(onError).toHaveBeenCalledWith('API 超時', 'error');
    expect(result.current.loading).toBe(false);
  });

  it('clears conversation history', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.messages).toEqual([]);
    expect(apis.clearConversation).toHaveBeenCalled();
  });

  it('calls onToolResultPost after tool result', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const onToolResultPost = vi.fn();
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis, onToolResultPost, enableAgentSteps: true }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onToolResult!('search_documents', '找到 3 筆', 3, 0);
    });

    expect(onToolResultPost).toHaveBeenCalledWith('search_documents', '找到 3 筆');
  });

  it('handles onSources callback', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_, cbs) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('問題');
    });

    const mockSources = [
      { id: 1, doc_number: 'TEST-001', subject: '測試', similarity: 0.9 },
    ];

    act(() => {
      capturedCallbacks!.onSources!(mockSources as never, 1);
    });

    expect(result.current.messages[1]!.sources).toEqual(mockSources);
    expect(result.current.messages[1]!.retrieval_count).toBe(1);
  });

  it('handles onRole callback to set agentIdentity', () => {
    let capturedCallbacks: StreamingChatCallbacks | null = null;
    const apis = createMockAPIs({
      startStream: vi.fn((_: unknown, cbs: StreamingChatCallbacks) => {
        capturedCallbacks = cbs;
        return mockAbortController;
      }),
    });

    const { result } = renderHook(() => useStreamingChat({ apis }));

    act(() => {
      result.current.sendMessage('問題');
    });

    act(() => {
      capturedCallbacks!.onRole!('乾坤圖譜分析員', 'knowledge-graph');
    });

    expect(result.current.messages[1]!.agentIdentity).toBe('乾坤圖譜分析員');
  });

  it('does not set agentSteps when enableAgentSteps is false', () => {
    const apis = createMockAPIs();
    const { result } = renderHook(() => useStreamingChat({ apis, enableAgentSteps: false }));

    act(() => {
      result.current.sendMessage('問題');
    });

    expect(result.current.messages[1]!.agentSteps).toBeUndefined();
  });
});
