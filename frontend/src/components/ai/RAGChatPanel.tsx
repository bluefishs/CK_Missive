/**
 * RAG / Agentic 問答面板
 *
 * 支援兩種模式：
 * - RAG 模式：單步向量檢索 + LLM 回答
 * - Agent 模式：多步工具呼叫 + 推理過程可視化 + LLM 合成回答
 *
 * 共用 SSE 串流逐字顯示、多輪對話記憶、來源引用展開。
 *
 * @version 3.0.0
 * @created 2026-02-25
 * @updated 2026-02-26 - Agentic 模式 + 推理步驟視覺化
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  Card,
  Input,
  Button,
  Typography,
  Space,
  Tag,
  Empty,
  Tooltip,
  App,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { aiApi } from '../../api/aiApi';
import { submitAIFeedback } from '../../api/ai/adminManagement';
import { MessageBubble } from './MessageBubble';
import type { ChatMessage } from './MessageBubble';
import type { AgentStepInfo } from './AgentStepsDisplay';

const { Text } = Typography;
const { TextArea } = Input;

export interface RAGChatPanelProps {
  /** 嵌入模式：省略外層 Card 框架，改用 flex 填充父容器 */
  embedded?: boolean;
  /** 是否使用 Agentic 模式 (預設 true) */
  agentMode?: boolean;
}

export const RAGChatPanel: React.FC<RAGChatPanelProps> = ({
  embedded = false,
  agentMode = true,
}) => {
  const { message: messageApi } = App.useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 對話 ID (每次清除後重新生成)
  const conversationId = useMemo(
    () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const conversationIdRef = useRef(conversationId);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput('');

    const userMsg: ChatMessage = {
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
      agentSteps: agentMode ? [] : undefined,
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    const history = messages
      .filter(m => !m.streaming)
      .map(m => ({ role: m.role, content: m.content }));

    if (agentMode) {
      // Agentic 模式
      abortRef.current = aiApi.streamAgentQuery(
        {
          question,
          history: history.length > 0 ? history : undefined,
        },
        {
          onThinking: (step, stepIndex) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                const steps = [...(last.agentSteps || [])];
                steps.push({ type: 'thinking', step_index: stepIndex, step });
                updated[updated.length - 1] = { ...last, agentSteps: steps };
              }
              return updated;
            });
          },
          onToolCall: (tool, params, stepIndex) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                const steps = [...(last.agentSteps || [])];
                steps.push({ type: 'tool_call', step_index: stepIndex, tool, params });
                updated[updated.length - 1] = { ...last, agentSteps: steps };
              }
              return updated;
            });
          },
          onToolResult: (tool, summary, count, stepIndex) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                const steps = [...(last.agentSteps || [])];
                steps.push({ type: 'tool_result', step_index: stepIndex, tool, summary, count });
                updated[updated.length - 1] = { ...last, agentSteps: steps };
              }
              return updated;
            });
          },
          onSources: (sources, count) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, sources, retrieval_count: count };
              }
              return updated;
            });
          },
          onToken: (token) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, content: last.content + token };
              }
              return updated;
            });
          },
          onDone: (latencyMs, model, toolsUsed, iterations) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = {
                  ...last,
                  streaming: false,
                  latency_ms: latencyMs,
                  model,
                  toolsUsed,
                  iterations,
                };
              }
              return updated;
            });
            setLoading(false);
            abortRef.current = null;
          },
          onError: (error, code) => {
            if (code === 'RATE_LIMITED') {
              messageApi.warning(error);
            } else if (code === 'STREAM_TIMEOUT') {
              messageApi.warning(error);
            } else {
              messageApi.error(`Agent 錯誤: ${error}`);
            }
          },
        },
      );
    } else {
      // 傳統 RAG 模式
      abortRef.current = aiApi.streamRAGQuery(
        {
          question,
          top_k: 5,
          similarity_threshold: 0.3,
          history: history.length > 0 ? history : undefined,
        },
        {
          onSources: (sources, count) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, sources, retrieval_count: count };
              }
              return updated;
            });
          },
          onToken: (token) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, content: last.content + token };
              }
              return updated;
            });
          },
          onDone: (latencyMs, model) => {
            setMessages(prev => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = {
                  ...last,
                  streaming: false,
                  latency_ms: latencyMs,
                  model,
                };
              }
              return updated;
            });
            setLoading(false);
            abortRef.current = null;
          },
          onError: (error, code) => {
            if (code === 'RATE_LIMITED') {
              messageApi.warning(error);
            } else if (code === 'EMBEDDING_ERROR') {
              messageApi.error('向量服務異常，請確認 Ollama 是否正常運行。');
            } else {
              messageApi.error(`RAG 錯誤: ${error}`);
            }
          },
        },
      );
    }
  }, [input, loading, messages, messageApi, agentMode]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleFeedback = useCallback(async (msgIndex: number, score: 1 | -1) => {
    const msg = messages[msgIndex];
    if (!msg || msg.feedbackScore != null) return;

    // 先更新 UI
    setMessages(prev => {
      const updated = [...prev];
      updated[msgIndex] = { ...updated[msgIndex]!, feedbackScore: score };
      return updated;
    });

    // 找到對應的使用者問題（上一則訊息）
    const userMsg = msgIndex > 0 ? messages[msgIndex - 1] : undefined;

    await submitAIFeedback({
      conversation_id: conversationIdRef.current,
      message_index: msgIndex,
      feature_type: agentMode ? 'agent' : 'rag',
      score,
      question: userMsg?.content?.slice(0, 500),
      answer_preview: msg.content?.slice(0, 200),
      latency_ms: msg.latency_ms,
      model: msg.model,
    });
  }, [messages, agentMode]);

  const handleClear = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setLoading(false);
    conversationIdRef.current = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }, []);

  const chatContent = (
    <>
      <div style={{ flex: 1, overflowY: 'auto', padding: embedded ? '8px' : '16px' }}>
        {messages.length === 0 ? (
          <Empty
            image={<ThunderboltOutlined style={{ fontSize: embedded ? 36 : 48, color: '#bfbfbf' }} />}
            description={
              <Space direction="vertical" size={4}>
                <Text type="secondary" style={{ fontSize: embedded ? 12 : 14 }}>
                  {agentMode ? 'AI 智能體問答助理' : '基於公文知識庫的 AI 問答助理'}
                </Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {agentMode
                    ? '多步推理、工具呼叫、跨來源智能檢索'
                    : '支援多輪對話、串流回答、來源引用'}
                </Text>
              </Space>
            }
            style={{ marginTop: embedded ? 40 : 80 }}
          >
            <Space wrap size={4}>
              {['桃園市工務局相關公文', '最近的查估派工案件', '乾坤測繪發文紀錄'].map(q => (
                <Button key={q} size="small" onClick={() => setInput(q)}>
                  {q}
                </Button>
              ))}
            </Space>
          </Empty>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble
              key={idx}
              message={msg}
              embedded={embedded}
              onFeedback={msg.role === 'assistant' && !msg.streaming
                ? (score) => handleFeedback(idx, score)
                : undefined}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div
        style={{
          borderTop: '1px solid #f0f0f0',
          padding: embedded ? '8px 10px' : '12px 16px',
          background: '#fafafa',
          flexShrink: 0,
        }}
      >
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={embedded ? '輸入問題... (Enter 送出)' : '輸入您的問題... (Enter 送出, Shift+Enter 換行)'}
            autoSize={{ minRows: 1, maxRows: embedded ? 2 : 3 }}
            disabled={loading}
            style={{ borderRadius: '6px 0 0 6px' }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!input.trim()}
            style={{ height: 'auto', borderRadius: '0 6px 6px 0' }}
          >
            {embedded ? '' : '送出'}
          </Button>
        </Space.Compact>
      </div>
    </>
  );

  if (embedded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
        {messages.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '4px 8px 0', flexShrink: 0 }}>
            <Tooltip title="清除對話">
              <Button type="text" icon={<DeleteOutlined />} onClick={handleClear} size="small" />
            </Tooltip>
          </div>
        )}
        {chatContent}
      </div>
    );
  }

  return (
    <Card
      title={
        <Space>
          <RobotOutlined />
          <span>{agentMode ? 'AI 智能體問答' : 'RAG 公文問答'}</span>
          <Tag color={agentMode ? 'purple' : 'blue'}>{agentMode ? 'Agent' : 'SSE'}</Tag>
        </Space>
      }
      extra={
        messages.length > 0 && (
          <Tooltip title="清除對話">
            <Button type="text" icon={<DeleteOutlined />} onClick={handleClear} size="small" />
          </Tooltip>
        )
      }
      styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', height: 520 } }}
    >
      {chatContent}
    </Card>
  );
};

export default RAGChatPanel;
