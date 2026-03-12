/**
 * RAG / Agentic 問答面板
 *
 * 支援兩種模式：
 * - RAG 模式：單步向量檢索 + LLM 回答
 * - Agent 模式：多步工具呼叫 + 推理過程可視化 + LLM 合成回答
 *
 * 共用 SSE 串流逐字顯示、多輪對話記憶、來源引用展開。
 * v4.0: SSE 邏輯提取至 useAgentSSE hook，消除 ~200 行重複代碼。
 *
 * @version 4.0.0
 * @created 2026-02-25
 * @updated 2026-03-11 - v4.0.0 使用 useAgentSSE hook
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
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
import { submitAIFeedback } from '../../api/ai/adminManagement';
import { MessageBubble } from './MessageBubble';
import { useGraphAgentBridgeOptional } from './knowledgeGraph/GraphAgentBridge';
import type { RequestSummaryEvent, RequestNavigateEvent } from './knowledgeGraph/GraphAgentBridge';
import { useAgentSSE, type DrawDiagramPayload } from '../../hooks/system/useAgentSSE';

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
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 三位一體：GraphAgentBridge 連接（可選）
  const bridge = useGraphAgentBridgeOptional();

  // SSE 串流邏輯（從 useAgentSSE hook 取得）
  const {
    messages,
    loading,
    conversationId,
    sendQuestion,
    clearConversation,
    setMessages,
  } = useAgentSSE({
    agentMode,
    onError: useCallback((msg: string, severity: 'warning' | 'error') => {
      if (severity === 'warning') messageApi.warning(msg);
      else messageApi.error(msg);
    }, [messageApi]),
    onToolResultPost: useCallback((tool: string, summary: string) => {
      if (!bridge) return;
      // navigate_graph → 圖譜 fly-to
      if (tool === 'navigate_graph') {
        try {
          const parsed = JSON.parse(summary);
          if (parsed.action === 'navigate' && parsed.highlight_ids) {
            bridge.navigateToCluster({
              highlightIds: parsed.highlight_ids,
              centerEntityName: parsed.center_entity?.name,
              clusterNodes: parsed.cluster_nodes,
            });
          }
        } catch { /* ignore */ }
      }
      // summarize_entity → 圖譜高亮上下游
      if (tool === 'summarize_entity') {
        try {
          const parsed = JSON.parse(summary);
          if (parsed.entity) {
            bridge.sendSummaryResult({
              entityId: parsed.entity.id,
              entityName: parsed.entity.name,
              entityType: parsed.entity.type,
              upstreamNames: parsed.upstream?.map((u: { entity_name: string }) => u.entity_name),
              downstreamNames: parsed.downstream?.map((d: { entity_name: string }) => d.entity_name),
            });
          }
        } catch { /* ignore */ }
      }
    }, [bridge]),
    onDrawDiagram: useCallback((parsed: DrawDiagramPayload) => {
      if (bridge && parsed.mermaid) {
        bridge.sendDrawResult({
          mermaidCode: parsed.mermaid,
          diagramType: (parsed.diagram_type as 'er' | 'flowchart' | 'classDiagram' | 'dependency') || 'er',
          relatedEntities: parsed.related_entities || [],
        });
      }
    }, [bridge]),
  });

  const conversationIdRef = useRef(conversationId);
  conversationIdRef.current = conversationId;

  // 滾動到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);
  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  // cleanup abort on unmount
  useEffect(() => {
    return () => { /* useAgentSSE handles cleanup internally */ };
  }, []);

  // 送出
  const handleSend = useCallback(() => {
    const question = input.trim();
    if (!question || loading) return;
    setInput('');
    sendQuestion(question);
  }, [input, loading, sendQuestion]);

  // 三位一體：programmatic 發送（供 Bridge 事件觸發）
  const sendQuestionRef = useRef(sendQuestion);
  sendQuestionRef.current = sendQuestion;

  // 三位一體：監聽圖譜事件 → 自動發問
  useEffect(() => {
    if (!bridge || !agentMode) return;

    const unsubSummary = bridge.bus.on<RequestSummaryEvent>('request_summary', (event) => {
      const question = `請簡報「${event.entityName}」（${event.entityType}）的來龍去脈、上下游關係和關鍵事件`;
      sendQuestionRef.current?.(question);
    });

    const unsubNavigate = bridge.bus.on<RequestNavigateEvent>('request_navigate', (event) => {
      const question = `帶我到「${event.query}」相關的公文叢集`;
      sendQuestionRef.current?.(question);
    });

    return () => {
      unsubSummary();
      unsubNavigate();
    };
  }, [bridge, agentMode]);

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

    setMessages(prev => {
      const updated = [...prev];
      updated[msgIndex] = { ...updated[msgIndex]!, feedbackScore: score };
      return updated;
    });

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
  }, [messages, agentMode, setMessages]);

  const chatContent = (
    <>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: embedded ? '8px' : '16px' }}>
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
              <Button type="text" icon={<DeleteOutlined />} onClick={clearConversation} size="small" />
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
            <Button type="text" icon={<DeleteOutlined />} onClick={clearConversation} size="small" />
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
