/**
 * 訊息氣泡元件
 *
 * 顯示使用者/AI 助理的對話訊息，含推理步驟、Metadata、來源引用。
 * 從 RAGChatPanel.tsx 提取。
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import React from 'react';
import {
  Typography,
  Space,
  Tag,
  List,
  Collapse,
  Button,
  Tooltip,
} from 'antd';
import {
  RobotOutlined,
  UserOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  LikeOutlined,
  LikeFilled,
  DislikeOutlined,
  DislikeFilled,
} from '@ant-design/icons';
import { AgentStepsDisplay } from './AgentStepsDisplay';
import type { AgentStepInfo } from './AgentStepsDisplay';
import type { RAGSourceItem } from '../../types/ai';

const { Text, Paragraph } = Typography;

export interface ChatMessage {
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
  // 回饋
  feedbackScore?: 1 | -1 | null;
}

interface MessageBubbleProps {
  message: ChatMessage;
  embedded?: boolean;
  /** 回饋回呼 (messageIndex, score) */
  onFeedback?: (score: 1 | -1) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  embedded = false,
  onFeedback,
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

        {/* Feedback buttons */}
        {!isUser && !message.streaming && message.content && onFeedback && (
          <Space size={4} style={{ marginTop: 6 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>回答有幫助嗎？</Text>
            <Tooltip title="有幫助">
              <Button
                type="text"
                size="small"
                icon={message.feedbackScore === 1 ? <LikeFilled style={{ color: '#52c41a' }} /> : <LikeOutlined />}
                onClick={() => onFeedback(1)}
                disabled={message.feedbackScore != null}
              />
            </Tooltip>
            <Tooltip title="沒有幫助">
              <Button
                type="text"
                size="small"
                icon={message.feedbackScore === -1 ? <DislikeFilled style={{ color: '#ff4d4f' }} /> : <DislikeOutlined />}
                onClick={() => onFeedback(-1)}
                disabled={message.feedbackScore != null}
              />
            </Tooltip>
            {message.feedbackScore != null && (
              <Text type="secondary" style={{ fontSize: 11 }}>已回饋</Text>
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

export default MessageBubble;
