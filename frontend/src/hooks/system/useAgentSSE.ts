/**
 * useAgentSSE - Agent / RAG SSE 串流問答 Hook
 *
 * 從 RAGChatPanel 提取的可重用邏輯：
 * - 管理對話訊息狀態 (ChatMessage[])
 * - SSE 串流回調處理 (thinking/tool_call/tool_result/token/done/error)
 * - 支援 Agent 模式 + RAG 模式切換
 * - 對話清除 + abort 控制
 *
 * 移植時只需替換 API 呼叫（aiApi.streamAgentQuery / streamRAGQuery）。
 *
 * @version 1.0.0
 * @created 2026-03-11
 */

import { useState, useCallback, useRef, useMemo } from 'react';
import { aiApi } from '../../api/aiApi';
import { clearAgentConversation } from '../../api/ai/adminManagement';
import type { ChatMessage } from '../../components/ai/MessageBubble';

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

/** 產生唯一對話 ID */
function generateConversationId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export function useAgentSSE(options: UseAgentSSEOptions = {}): UseAgentSSEReturn {
  const { agentMode = true, context, onError, onToolResultPost, onDrawDiagram } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const conversationId = useMemo(() => generateConversationId(), []);
  const conversationIdRef = useRef(conversationId);

  // 共用的 message updater 工具函數
  const updateLastAssistant = useCallback(
    (updater: (msg: ChatMessage) => Partial<ChatMessage>) => {
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === 'assistant') {
          updated[updated.length - 1] = { ...last, ...updater(last) };
        }
        return updated;
      });
    },
    [],
  );

  const finishStream = useCallback(() => {
    setLoading(false);
    abortRef.current = null;
  }, []);

  const handleStreamError = useCallback(
    (msg: ChatMessage) => {
      if (msg.streaming) return { streaming: false };
      return {};
    },
    [],
  );

  // 共用的 Agent SSE 回調工廠
  const createAgentCallbacks = useCallback(() => ({
    onThinking: (step: string, stepIndex: number) => {
      updateLastAssistant(last => ({
        agentSteps: [...(last.agentSteps || []), { type: 'thinking' as const, step_index: stepIndex, step }],
      }));
    },
    onToolCall: (tool: string, params: Record<string, unknown>, stepIndex: number) => {
      updateLastAssistant(last => ({
        agentSteps: [...(last.agentSteps || []), { type: 'tool_call' as const, step_index: stepIndex, tool, params }],
      }));
    },
    onToolResult: (tool: string, summary: string, count: number, stepIndex: number) => {
      updateLastAssistant(last => ({
        agentSteps: [...(last.agentSteps || []), { type: 'tool_result' as const, step_index: stepIndex, tool, summary, count }],
      }));
      onToolResultPost?.(tool, summary);

      // draw_diagram → 注入 mermaid 內容到訊息
      if (tool === 'draw_diagram') {
        try {
          const parsed = JSON.parse(summary);
          if (parsed.mermaid) {
            updateLastAssistant(last => ({
              content: last.content + `\n\n**${parsed.title || '圖表'}**\n${parsed.description || ''}\n\n\`\`\`mermaid\n${parsed.mermaid}\n\`\`\`\n`,
            }));
            onDrawDiagram?.(parsed);
          }
        } catch { /* silent */ }
      }
    },
    onSources: (sources: ChatMessage['sources'], count: number) => {
      updateLastAssistant(() => ({ sources, retrieval_count: count }));
    },
    onToken: (token: string) => {
      updateLastAssistant(last => ({ content: last.content + token }));
    },
    onDone: (latencyMs: number, model: string, toolsUsed?: string[], iterations?: number) => {
      updateLastAssistant(() => ({ streaming: false, latency_ms: latencyMs, model, toolsUsed, iterations }));
      finishStream();
    },
    onError: (error: string, code?: string) => {
      if (code === 'RATE_LIMITED' || code === 'STREAM_TIMEOUT') {
        onError?.(error, 'warning');
      } else {
        onError?.(`Agent 錯誤: ${error}`, 'error');
      }
      updateLastAssistant(handleStreamError);
      finishStream();
    },
  }), [updateLastAssistant, finishStream, handleStreamError, onToolResultPost, onDrawDiagram, onError]);

  // 共用的 RAG SSE 回調工廠
  const createRAGCallbacks = useCallback(() => ({
    onSources: (sources: ChatMessage['sources'], count: number) => {
      updateLastAssistant(() => ({ sources, retrieval_count: count }));
    },
    onToken: (token: string) => {
      updateLastAssistant(last => ({ content: last.content + token }));
    },
    onDone: (latencyMs: number, model: string) => {
      updateLastAssistant(() => ({ streaming: false, latency_ms: latencyMs, model }));
      finishStream();
    },
    onError: (error: string, code?: string) => {
      if (code === 'RATE_LIMITED') {
        onError?.(error, 'warning');
      } else if (code === 'EMBEDDING_ERROR') {
        onError?.('向量服務異常，請確認 Ollama 是否正常運行。', 'error');
      } else {
        onError?.(`RAG 錯誤: ${error}`, 'error');
      }
      updateLastAssistant(handleStreamError);
      finishStream();
    },
  }), [updateLastAssistant, finishStream, handleStreamError, onError]);

  const sendQuestion = useCallback((question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: question, timestamp: new Date() };
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
      agentSteps: agentMode ? [] : undefined,
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    if (agentMode) {
      abortRef.current = aiApi.streamAgentQuery(
        { question, session_id: conversationIdRef.current, ...(context ? { context } : {}) },
        createAgentCallbacks(),
      );
    } else {
      abortRef.current = aiApi.streamRAGQuery(
        { question, top_k: 5, similarity_threshold: 0.3, session_id: conversationIdRef.current },
        createRAGCallbacks(),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, agentMode, createAgentCallbacks, createRAGCallbacks]);

  const clearConversation = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (agentMode && conversationIdRef.current) {
      clearAgentConversation(conversationIdRef.current).catch(() => {});
    }
    setMessages([]);
    setLoading(false);
    conversationIdRef.current = generateConversationId();
  }, [agentMode]);

  return {
    messages,
    loading,
    conversationId,
    sendQuestion,
    clearConversation,
    abortRef,
    setMessages,
  };
}
