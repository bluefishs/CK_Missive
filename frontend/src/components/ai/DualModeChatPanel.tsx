/**
 * 雙模式並列比較面板
 *
 * 同時發送問題至 Missive Agent 和數位分身，
 * 左右並列顯示回答結果，供使用者比較差異。
 *
 * 架構:
 *   左面板: useAgentSSE (Missive Agent)
 *   右面板: useDigitalTwinSSE (Digital Twin Agent)
 *
 * @version 2.0.0
 * @created 2026-03-22
 * @updated 2026-04-17 — v2.0 移除 NemoClaw 引用 (ADR-0014/0015)
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
  Badge,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  CloudServerOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { MessageBubble } from './MessageBubble';
import { VoiceInputButton } from './VoiceInputButton';
import { useAgentSSE } from '../../hooks/system/useAgentSSE';
import { useDigitalTwinSSE } from '../../hooks/system/useDigitalTwinSSE';

const { Text } = Typography;
const { TextArea } = Input;

export interface DualModeChatPanelProps {
  /** 助理上下文 */
  context?: string;
  /** 嵌入模式：省略外層 Card，直接填充父容器 */
  embedded?: boolean;
}

export const DualModeChatPanel: React.FC<DualModeChatPanelProps> = ({
  context,
  embedded = false,
}) => {
  const { message: messageApi } = App.useApp();
  const [input, setInput] = useState('');
  const leftEndRef = useRef<HTMLDivElement>(null);
  const rightEndRef = useRef<HTMLDivElement>(null);

  // --- 左: Missive Agent ---
  const agent = useAgentSSE({
    agentMode: true,
    context,
    onError: useCallback(
      (msg: string, severity: 'warning' | 'error') => {
        if (severity === 'warning') messageApi.warning(`[Agent] ${msg}`);
        else messageApi.error(`[Agent] ${msg}`);
      },
      [messageApi],
    ),
  });

  // --- 右: 數位分身 ---
  const [twinStatus, setTwinStatus] = useState<string>('');
  const twin = useDigitalTwinSSE({
    onError: useCallback(
      (msg: string) => {
        messageApi.error(`[數位分身] ${msg}`);
      },
      [messageApi],
    ),
    onStatus: useCallback((_status: string, detail?: string) => {
      setTwinStatus(detail || _status);
    }, []),
  });

  // 滾動
  useEffect(() => {
    leftEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agent.messages]);
  useEffect(() => {
    rightEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [twin.messages]);

  // 同時送出
  const handleSend = useCallback(() => {
    const question = input.trim();
    if (!question || agent.loading || twin.loading) return;
    setInput('');
    setTwinStatus('');
    agent.sendQuestion(question);
    twin.sendQuestion(question);
  }, [input, agent, twin]);

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
    agent.clearConversation();
    twin.clearConversation();
    setTwinStatus('');
  }, [agent, twin]);

  const bothLoading = agent.loading || twin.loading;
  const hasMessages = agent.messages.length > 0 || twin.messages.length > 0;

  // --- 訊息列 ---
  const renderMessageList = (
    messages: typeof agent.messages,
    endRef: React.RefObject<HTMLDivElement>,
    emptyLabel: string,
  ) => (
    <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '8px 12px' }}>
      {messages.length === 0 ? (
        <Empty
          image={<ThunderboltOutlined style={{ fontSize: 32, color: '#bfbfbf' }} />}
          description={<Text type="secondary" style={{ fontSize: 12 }}>{emptyLabel}</Text>}
          style={{ marginTop: 60 }}
        />
      ) : (
        messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} embedded />
        ))
      )}
      <div ref={endRef as React.RefObject<HTMLDivElement>} />
    </div>
  );

  // --- 共用內容 ---
  const dualContent = (
    <>
      {/* --- 並列面板 --- */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        {/* 左: Missive Agent */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid #f0f0f0' }}>
          <div style={{ padding: '6px 10px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
            <Space size={4}>
              <Badge status={agent.loading ? 'processing' : 'success'} />
              <RobotOutlined style={{ color: '#722ed1', fontSize: 12 }} />
              <Text strong style={{ fontSize: 12 }}>Agent</Text>
              {agent.loading && <Tag color="processing" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>推理中</Tag>}
            </Space>
          </div>
          {renderMessageList(agent.messages, leftEndRef, '等待問題...')}
        </div>

        {/* 右: 數位分身 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '6px 10px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
            <Space size={4}>
              <Badge status={twin.loading ? 'processing' : 'default'} />
              <CloudServerOutlined style={{ color: '#13c2c2', fontSize: 12 }} />
              <Text strong style={{ fontSize: 12 }}>數位分身</Text>
              {twin.loading && <Tag color="cyan" style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>{twinStatus || '連線中'}</Tag>}
            </Space>
          </div>
          {renderMessageList(twin.messages, rightEndRef, '等待問題...')}
        </div>
      </div>

      {/* --- 底部輸入區 (共用) --- */}
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
            placeholder="輸入問題同時送出比較... (Enter 送出)"
            autoSize={{ minRows: 1, maxRows: embedded ? 2 : 3 }}
            disabled={bothLoading}
            style={{ borderRadius: '6px 0 0 6px' }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={bothLoading}
            disabled={!input.trim()}
            style={{ height: 'auto', borderRadius: '0 6px 6px 0' }}
          >
            {embedded ? '' : '同時送出'}
          </Button>
        </Space.Compact>
        <VoiceInputButton
          onTranscribed={(text) => setInput(prev => prev ? `${prev} ${text}` : text)}
          disabled={bothLoading}
        />
      </div>
    </>
  );

  // --- embedded 模式：直接輸出，不包 Card ---
  if (embedded) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
        {hasMessages && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '4px 8px 0', flexShrink: 0 }}>
            <Tooltip title="清除兩側對話">
              <Button type="text" icon={<DeleteOutlined />} onClick={handleClear} size="small" />
            </Tooltip>
          </div>
        )}
        {dualContent}
      </div>
    );
  }

  // --- 獨立 Card 模式 ---
  return (
    <Card
      title={
        <Space>
          <SwapOutlined />
          <span>雙模式比較</span>
          <Tag color="purple">Agent</Tag>
          <Text type="secondary">vs</Text>
          <Tag color="cyan">數位分身</Tag>
        </Space>
      }
      extra={
        hasMessages && (
          <Tooltip title="清除兩側對話">
            <Button type="text" icon={<DeleteOutlined />} onClick={handleClear} size="small" />
          </Tooltip>
        )
      }
      styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', height: 600 } }}
    >
      {dualContent}
    </Card>
  );
};

export default DualModeChatPanel;
