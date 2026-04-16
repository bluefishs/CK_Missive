/**
 * useDigitalTwinSSE - 數位分身串流 Hook
 *
 * 透過本地 Agent 推理，使用與 useAgentSSE 相同的
 * useStreamingChat 底層，但注入 Digital Twin adapter。
 *
 * 架構:
 *   useDigitalTwinSSE (本 hook)
 *     → useStreamingChat (通用 DI hook from @ck-shared)
 *       → StreamingChatAPIs<RAGSourceItem> (Digital Twin adapter)
 *         → streamDigitalTwin() (api/digitalTwin.ts)
 *
 * @version 2.0.0
 * @created 2026-03-22
 * @updated 2026-04-17 — v2.0 移除 NemoClaw 引用 (ADR-0014/0015)
 */

import { useMemo, useRef } from 'react';
import { streamDigitalTwin } from '../../api/digitalTwin';
import type { ChatMessage, RAGSourceItem } from '../../types/ai';
import {
  useStreamingChat,
  type StreamingChatAPIs,
} from './useStreamingChat';

export interface UseDigitalTwinSSEOptions {
  /** 目標 Agent ID (預設 'auto' — Leader Agent 自動路由) */
  agentId?: string;
  /** 錯誤通知回調 */
  onError?: (message: string, severity: 'warning' | 'error') => void;
  /** 狀態更新回調 */
  onStatus?: (status: string, detail?: string) => void;
}

export interface UseDigitalTwinSSEReturn {
  messages: ChatMessage[];
  loading: boolean;
  conversationId: string;
  sendQuestion: (question: string) => void;
  clearConversation: () => void;
  abortRef: React.MutableRefObject<AbortController | null>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

// ---------------------------------------------------------------------------
// Digital Twin StreamingChatAPIs adapter
// ---------------------------------------------------------------------------

function createDigitalTwinAPIs(
  agentId: string,
  onErrorRef: React.RefObject<UseDigitalTwinSSEOptions['onError']>,
  onStatusRef: React.RefObject<UseDigitalTwinSSEOptions['onStatus']>,
): StreamingChatAPIs<RAGSourceItem> {
  return {
    startStream: (params, callbacks) => {
      return streamDigitalTwin(
        {
          question: params.question,
          session_id: params.sessionId,
          context: params.context
            ? { context: params.context, agent_id: agentId }
            : { agent_id: agentId },
        },
        {
          onToken: callbacks.onToken,
          onDone: (latencyMs) => {
            callbacks.onDone(latencyMs, 'digital-twin');
          },
          onError: (error) => {
            onErrorRef.current?.(error, 'error');
            callbacks.onError?.(error, 'GATEWAY_ERROR');
          },
          onStatus: (status, detail) => {
            onStatusRef.current?.(status, detail);
            // Map status to thinking step for UI
            if (detail) {
              callbacks.onThinking?.(detail, -1);
            }
          },
        },
      );
    },
    // Session memory via Redis — no explicit clear needed from frontend
    // (sessions expire via TTL in Redis DB 4)
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * 數位分身串流問答 Hook。
 *
 * 與 useAgentSSE 平行使用，透過本地 AgentOrchestrator 推理。
 *
 * @example
 * ```tsx
 * const twin = useDigitalTwinSSE({
 *   onError: (msg) => message.error(msg),
 * });
 * twin.sendQuestion('查詢承包商跨專案關係');
 * ```
 */
export function useDigitalTwinSSE(
  options: UseDigitalTwinSSEOptions = {},
): UseDigitalTwinSSEReturn {
  const { agentId = 'auto', onError, onStatus } = options;

  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onStatusRef = useRef(onStatus);
  onStatusRef.current = onStatus;

  const apis = useMemo<StreamingChatAPIs<RAGSourceItem>>(
    () => createDigitalTwinAPIs(agentId, onErrorRef, onStatusRef),
    [agentId],
  );

  const chat = useStreamingChat<RAGSourceItem, ChatMessage>({
    apis,
    enableAgentSteps: true,  // 顯示工具呼叫和推理步驟
  });

  return {
    messages: chat.messages,
    loading: chat.loading,
    conversationId: chat.conversationId,
    sendQuestion: chat.sendMessage,
    clearConversation: chat.clearHistory,
    abortRef: chat.abortRef,
    setMessages: chat.setMessages,
  };
}
