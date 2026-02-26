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

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Typography,
  Space,
  Tag,
  List,
  Collapse,
  Empty,
  Tooltip,
  App,
  Steps,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  LoadingOutlined,
  SearchOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { aiApi } from '../../api/aiApi';
import type { RAGSourceItem } from '../../types/ai';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

/** 推理步驟 */
interface AgentStepInfo {
  type: 'thinking' | 'tool_call' | 'tool_result';
  step_index: number;
  step?: string;
  tool?: string;
  params?: Record<string, unknown>;
  summary?: string;
  count?: number;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: RAGSourceItem[];
  latency_ms?: number;
  model?: string;
  retrieval_count?: number;
  streaming?: boolean;
  // Agentic 模式
  agentSteps?: AgentStepInfo[];
  toolsUsed?: string[];
  iterations?: number;
}

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
          onError: (error) => {
            messageApi.error(`Agent 錯誤: ${error}`);
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
          onError: (error) => {
            messageApi.error(`RAG 錯誤: ${error}`);
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

  const handleClear = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setLoading(false);
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
            <MessageBubble key={idx} message={msg} embedded={embedded} />
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

// ============================================================================
// Agent 推理步驟
// ============================================================================

const TOOL_ICONS: Record<string, React.ReactNode> = {
  search_documents: <SearchOutlined />,
  search_dispatch_orders: <FileTextOutlined />,
  search_entities: <NodeIndexOutlined />,
  get_entity_detail: <DatabaseOutlined />,
  find_similar: <CopyOutlined />,
  get_statistics: <BarChartOutlined />,
};

const TOOL_LABELS: Record<string, string> = {
  search_documents: '搜尋公文',
  search_dispatch_orders: '搜尋派工單',
  search_entities: '搜尋實體',
  get_entity_detail: '實體詳情',
  find_similar: '相似公文',
  get_statistics: '統計資訊',
};

const AgentStepsDisplay: React.FC<{ steps: AgentStepInfo[]; streaming: boolean }> = ({
  steps,
  streaming,
}) => {
  if (!steps || steps.length === 0) return null;

  // Sort by step_index for correct ordering
  const sorted = [...steps].sort((a, b) => a.step_index - b.step_index);

  const stepsItems = sorted.map((s, idx) => {
    if (s.type === 'thinking') {
      return {
        title: <Text style={{ fontSize: 11 }}><BulbOutlined /> {s.step}</Text>,
        status: 'finish' as const,
      };
    }
    if (s.type === 'tool_call') {
      const icon = TOOL_ICONS[s.tool || ''] || <ToolOutlined />;
      const label = TOOL_LABELS[s.tool || ''] || s.tool;
      // Check if there's a matching tool_result after this
      const hasResult = sorted.slice(idx + 1).some(
        next => next.type === 'tool_result' && next.tool === s.tool
      );
      return {
        title: (
          <Text style={{ fontSize: 11 }}>
            {icon} 呼叫 {label}
          </Text>
        ),
        status: hasResult ? ('finish' as const) : ('process' as const),
      };
    }
    if (s.type === 'tool_result') {
      return {
        title: (
          <Text style={{ fontSize: 11 }}>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />{' '}
            {s.summary}
          </Text>
        ),
        status: 'finish' as const,
      };
    }
    return { title: '', status: 'wait' as const };
  });

  // If still streaming, add a loading step
  if (streaming) {
    stepsItems.push({
      title: <Text style={{ fontSize: 11 }}><LoadingOutlined /> 處理中...</Text>,
      status: 'process' as const,
    });
  }

  return (
    <div style={{ marginBottom: 8, padding: '4px 0' }}>
      <Steps
        size="small"
        direction="vertical"
        current={stepsItems.length - 1}
        items={stepsItems}
        style={{ fontSize: 11 }}
      />
    </div>
  );
};

// ============================================================================
// 訊息氣泡
// ============================================================================

const MessageBubble: React.FC<{ message: ChatMessage; embedded?: boolean }> = ({
  message,
  embedded = false,
}) => {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 12,
      }}
    >
      <div style={{ maxWidth: embedded ? '95%' : '85%' }}>
        <Space size={4} style={{ marginBottom: 4 }}>
          {!isUser && <RobotOutlined style={{ color: '#722ed1' }} />}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {isUser ? '您' : 'AI 助理'}
            {' '}
            {message.timestamp.toLocaleTimeString('zh-TW', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Text>
          {isUser && <UserOutlined style={{ color: '#52c41a' }} />}
        </Space>

        <div
          style={{
            background: isUser ? '#e6f7ff' : '#fff',
            border: `1px solid ${isUser ? '#91d5ff' : '#f0f0f0'}`,
            borderRadius: 8,
            padding: '10px 14px',
          }}
        >
          {/* Agent 推理步驟 (在回答前顯示) */}
          {!isUser && message.agentSteps && message.agentSteps.length > 0 && (
            <Collapse
              ghost
              size="small"
              defaultActiveKey={message.streaming ? ['steps'] : []}
              style={{ marginBottom: message.content ? 8 : 0 }}
              items={[
                {
                  key: 'steps',
                  label: (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      <ThunderboltOutlined /> 推理過程 ({message.agentSteps.length} 步)
                    </Text>
                  ),
                  children: (
                    <AgentStepsDisplay
                      steps={message.agentSteps}
                      streaming={!!message.streaming && !message.content}
                    />
                  ),
                },
              ]}
            />
          )}

          <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
            {message.content}
            {message.streaming && (
              <LoadingOutlined style={{ marginLeft: 4, color: '#722ed1' }} />
            )}
          </Paragraph>
        </div>

        {/* Metadata tags */}
        {!isUser && !message.streaming && message.latency_ms != null && (
          <Space size={8} style={{ marginTop: 4 }} wrap>
            <Tag icon={<ClockCircleOutlined />} color="default" style={{ fontSize: 11 }}>
              {(message.latency_ms / 1000).toFixed(1)}s
            </Tag>
            {message.model && message.model !== 'none' && message.model !== 'error' && (
              <Tag color="blue" style={{ fontSize: 11 }}>
                {message.model}
              </Tag>
            )}
            {message.retrieval_count != null && message.retrieval_count > 0 && (
              <Tag icon={<FileTextOutlined />} color="green" style={{ fontSize: 11 }}>
                {message.retrieval_count} 篇引用
              </Tag>
            )}
            {message.toolsUsed && message.toolsUsed.length > 0 && (
              <Tag icon={<ToolOutlined />} color="purple" style={{ fontSize: 11 }}>
                {message.toolsUsed.length} 工具
              </Tag>
            )}
          </Space>
        )}

        {/* Sources collapse */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <Collapse
            ghost
            size="small"
            style={{ marginTop: 8 }}
            items={[
              {
                key: 'sources',
                label: (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <FileTextOutlined /> 查看 {message.sources.length} 篇來源公文
                  </Text>
                ),
                children: (
                  <List
                    size="small"
                    dataSource={message.sources}
                    renderItem={(src: RAGSourceItem) => (
                      <List.Item style={{ padding: '4px 0' }}>
                        <Space direction="vertical" size={0} style={{ width: '100%' }}>
                          <Space>
                            <Tag color="blue" style={{ fontSize: 11 }}>
                              {src.doc_type || '函'}
                            </Tag>
                            <Text strong style={{ fontSize: 12 }}>
                              {src.doc_number}
                            </Text>
                            {src.similarity > 0 && (
                              <Tag style={{ fontSize: 11 }}>
                                {(src.similarity * 100).toFixed(0)}%
                              </Tag>
                            )}
                          </Space>
                          <Text style={{ fontSize: 12 }} ellipsis>
                            {src.subject}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {src.sender} {src.doc_date ? `| ${src.doc_date}` : ''}
                          </Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
          />
        )}
      </div>
    </div>
  );
};

export default RAGChatPanel;
