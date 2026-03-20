/**
 * useAgentSSE - Agent / RAG SSE 串流問答 Hook
 *
 * 從 RAGChatPanel 提取的可重用邏輯：
 * - 管理對話訊息狀態 (ChatMessage[])
 * - SSE 串流回調處理 (thinking/tool_call/tool_result/token/done/error)
 * - 支援 Agent 模式 + RAG 模式切換
 * - 對話清除 + abort 控制
 *
 * v2.0: 底層使用 useStreamingChat (DI 模式)，CK_Missive 專用邏輯作為 wrapper。
 *
 * @version 2.0.0
 * @created 2026-03-11
 * @updated 2026-03-14 - v2.0.0 依賴注入重構
 */

import { useMemo, useRef } from 'react';
import { aiApi } from '../../api/aiApi';
import { clearAgentConversation } from '../../api/ai/adminManagement';
import type { ChatMessage, RAGSourceItem } from '../../types/ai';
import {
  useStreamingChat,
  type StreamingChatAPIs,
} from './useStreamingChat';

/** draw_diagram 工具回傳的結構化資料 */
export interface DrawDiagramPayload {
  mermaid?: string;
  title?: string;
  description?: string;
  diagram_type?: 'er' | 'flowchart' | 'classDiagram' | 'dependency' | string;
  related_entities?: string[];
}

export interface UseAgentSSEOptions {
  agentMode?: boolean;
  /** 助理上下文（傳送至後端，影響 system prompt 選擇） */
  context?: string;
  /** 錯誤通知回調 */
  onError?: (message: string, severity: 'warning' | 'error') => void;
  /** 工具結果後處理（Bridge 整合等） */
  onToolResultPost?: (tool: string, summary: string) => void;
  /** draw_diagram 後處理（注入 mermaid 到訊息） */
  onDrawDiagram?: (parsed: DrawDiagramPayload) => void;
}

export interface UseAgentSSEReturn {
  messages: ChatMessage[];
  loading: boolean;
  conversationId: string;
  /** 送出問題（供使用者輸入） */
  sendQuestion: (question: string) => void;
  /** 清除對話 */
  clearConversation: () => void;
  /** abort 控制器 ref */
  abortRef: React.MutableRefObject<AbortController | null>;
  /** 手動設定訊息（用於 feedback 更新等） */
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

// ---------------------------------------------------------------------------
// API adapters: bridge CK_Missive streaming APIs → StreamingChatAPIs
// ---------------------------------------------------------------------------

/**
 * Creates a StreamingChatAPIs adapter for Agent mode.
 *
 * Wraps aiApi.streamAgentQuery and maps its callbacks to the generic interface.
 * Error classification (RATE_LIMITED vs generic) is handled here.
 */
function createAgentAPIs(
  onErrorRef: React.RefObject<UseAgentSSEOptions['onError']>,
  onDrawDiagramRef: React.RefObject<UseAgentSSEOptions['onDrawDiagram']>,
  setMessagesRef: React.RefObject<React.Dispatch<React.SetStateAction<ChatMessage[]>> | null>,
): StreamingChatAPIs<RAGSourceItem> {
  return {
    startStream: (params, callbacks) => {
      return aiApi.streamAgentQuery(
        {
          question: params.question,
          session_id: params.sessionId,
          ...(params.context ? { context: params.context } : {}),
        },
        {
          onRole: callbacks.onRole,
          onThinking: callbacks.onThinking!,
          onReact: callbacks.onReact,
          onToolCall: callbacks.onToolCall!,
          onToolResult: (tool, summary, count, stepIndex) => {
            callbacks.onToolResult!(tool, summary, count, stepIndex);
            // draw_diagram post-processing
            if (tool === 'draw_diagram') {
              try {
                const parsed = JSON.parse(summary);
                if (parsed.mermaid && setMessagesRef.current) {
                  setMessagesRef.current(prev => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === 'assistant') {
                      updated[updated.length - 1] = {
                        ...last,
                        content: last.content + `\n\n**${parsed.title || '圖表'}**\n${parsed.description || ''}\n\n\`\`\`mermaid\n${parsed.mermaid}\n\`\`\`\n`,
                      };
                    }
                    return updated;
                  });
                  onDrawDiagramRef.current?.(parsed);
                }
              } catch { /* silent */ }
            }
          },
          onSources: callbacks.onSources!,
          onSelfAwareness: (data) => {
            // 映射為 agent step + 更新 agentIdentity
            callbacks.onRole?.(data.identity, '');
            callbacks.onThinking?.(
              `${data.identity} 就緒` + (data.strengths?.length ? `（擅長: ${data.strengths.join('、')}）` : ''),
              -1,
            );
          },
          onProactiveAlert: (message) => {
            callbacks.onThinking?.(message, -2);
          },
          onToken: callbacks.onToken,
          onDone: (latencyMs, model, toolsUsed, iterations) =>
            callbacks.onDone(latencyMs, model, toolsUsed, iterations),
          onError: (error, code) => {
            if (code === 'RATE_LIMITED' || code === 'STREAM_TIMEOUT') {
              onErrorRef.current?.(error, 'warning');
            } else {
              onErrorRef.current?.(`Agent 錯誤: ${error}`, 'error');
            }
            callbacks.onError?.(error, code);
          },
        },
      );
    },
    clearConversation: (sessionId) => clearAgentConversation(sessionId),
  };
}

/**
 * Creates a StreamingChatAPIs adapter for RAG mode.
 *
 * Wraps aiApi.streamRAGQuery with fixed top_k / similarity_threshold.
 */
function createRAGAPIs(
  onErrorRef: React.RefObject<UseAgentSSEOptions['onError']>,
): StreamingChatAPIs<RAGSourceItem> {
  return {
    startStream: (params, callbacks) => {
      return aiApi.streamRAGQuery(
        {
          question: params.question,
          top_k: 5,
          similarity_threshold: 0.3,
          session_id: params.sessionId,
        },
        {
          onSources: callbacks.onSources!,
          onToken: callbacks.onToken,
          onDone: (latencyMs, model) => callbacks.onDone(latencyMs, model),
          onError: (error, code) => {
            if (code === 'RATE_LIMITED') {
              onErrorRef.current?.(error, 'warning');
            } else if (code === 'EMBEDDING_ERROR') {
              onErrorRef.current?.('向量服務異常，請確認 Ollama 是否正常運行。', 'error');
            } else {
              onErrorRef.current?.(`RAG 錯誤: ${error}`, 'error');
            }
            callbacks.onError?.(error, code);
          },
        },
      );
    },
    // RAG mode does not have server-side conversation memory to clear
  };
}

/**
 * Agent / RAG SSE 串流問答 Hook。
 *
 * 管理完整的對話生命週期：訊息狀態、SSE 串流回調處理、
 * Agent 與 RAG 模式切換、對話清除與 abort 控制。
 *
 * @param options - 配置選項（模式、上下文、回調）
 * @returns 對話狀態與控制方法
 *
 * @example
 * ```tsx
 * const { messages, sendQuestion, clearConversation, loading } = useAgentSSE({
 *   agentMode: true,
 *   context: 'knowledge-graph',
 *   onError: (msg, severity) => notification[severity]({ message: msg }),
 * });
 * ```
 */
export function useAgentSSE(options: UseAgentSSEOptions = {}): UseAgentSSEReturn {
  const { agentMode = true, context, onError, onToolResultPost, onDrawDiagram } = options;

  // Use refs for callbacks to avoid re-creating APIs on every render
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onDrawDiagramRef = useRef(onDrawDiagram);
  onDrawDiagramRef.current = onDrawDiagram;
  const setMessagesRef = useRef<React.Dispatch<React.SetStateAction<ChatMessage[]>> | null>(null);

  // Build the injected APIs based on mode (stable across renders)
  const apis = useMemo<StreamingChatAPIs<RAGSourceItem>>(
    () => agentMode
      ? createAgentAPIs(onErrorRef, onDrawDiagramRef, setMessagesRef)
      : createRAGAPIs(onErrorRef),
    [agentMode],
  );

  const chat = useStreamingChat<RAGSourceItem, ChatMessage>({
    apis,
    enableAgentSteps: agentMode,
    context,
    onToolResultPost,
  });

  // Keep setMessagesRef in sync for draw_diagram injection
  setMessagesRef.current = chat.setMessages;

  // Map to the original public API names
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
