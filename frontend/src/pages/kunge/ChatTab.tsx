/**
 * 坤哥 — 直接對話板塊（embedded，不跳頁）
 *
 * 走與 Telegram 同一後端：AgentOrchestrator.stream_agent_query
 * → build_system_prompt_with_soul() → 2691 字坤哥人格 prompt。
 *
 * @version 1.1.0 — 恢復 embed，不跳頁；context="web" 為後端已註冊的 role
 */

import React from 'react';
import { Card, Typography, Alert, Space } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
import { RAGChatPanel } from '../../components/ai/RAGChatPanel';

const { Title, Paragraph, Text } = Typography;

export const ChatTab: React.FC = () => (
  <div>
    <Card bordered={false} style={{ marginBottom: 8 }}>
      <Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
        <MessageOutlined /> 與坤哥對話
      </Title>
      <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 8 }}>
        同一個意識體 — Telegram / Web 皆得到相同人格的回應。
      </Paragraph>
      <Alert
        type="info"
        showIcon
        message={
          <Space size={8} wrap>
            <Text style={{ fontSize: 13 }}>坤哥行事準則：</Text>
            <Text strong>穩定即信任</Text>
            <Text>·</Text>
            <Text strong>異常即訊號</Text>
            <Text>·</Text>
            <Text strong>記憶即資產</Text>
          </Space>
        }
      />
    </Card>

    <Card
      bordered={false}
      styles={{ body: { padding: 0, minHeight: '60vh', display: 'flex', flexDirection: 'column' } }}
    >
      {/* context="web" 後端已註冊；SOUL 人格由 build_system_prompt_with_soul 自動注入 */}
      <RAGChatPanel embedded agentMode context="web" enableDualMode={false} />
    </Card>
  </div>
);

export default ChatTab;
