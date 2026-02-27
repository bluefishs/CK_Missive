/**
 * AI 助理管理頁面
 *
 * Version: 3.1.0
 * Created: 2026-02-09
 * Updated: 2026-02-27 — 移除空殼「AI 配置」Tab（DB 層無資料，YAML 為實際來源）
 *
 * Tab 結構：
 * 1. AI 問答 — RAG/Agent 問答面板
 * 2. 數據分析 — 搜尋總覽 + 搜尋歷史
 * 3. 資料管線 — Embedding 管理 + 知識圖譜
 * 4. 服務狀態 — Ollama 管理 + 系統監控
 */
import React, { useMemo } from 'react';
import { Tabs, Typography } from 'antd';
import {
  BarChartOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  HeartOutlined,
  RobotOutlined,
} from '@ant-design/icons';

import { RAGChatPanel } from '../components/ai/RAGChatPanel';
import {
  DataAnalyticsTab,
  DataPipelineTab,
  ServiceStatusTab,
} from '../components/ai/management';

const { Title, Text } = Typography;

const AIAssistantManagementPage: React.FC = () => {
  const tabItems = useMemo(() => [
    {
      key: 'ai-chat',
      label: (
        <span><RobotOutlined /> AI 問答</span>
      ),
      children: <RAGChatPanel />,
    },
    {
      key: 'analytics',
      label: (
        <span><BarChartOutlined /> 數據分析</span>
      ),
      children: <DataAnalyticsTab />,
    },
    {
      key: 'pipeline',
      label: (
        <span><DatabaseOutlined /> 資料管線</span>
      ),
      children: <DataPipelineTab />,
    },
    {
      key: 'status',
      label: (
        <span><HeartOutlined /> 服務狀態</span>
      ),
      children: <ServiceStatusTab />,
    },
  ], []);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <ExperimentOutlined /> AI 助理管理
        </Title>
        <Text type="secondary">
          AI 問答、數據分析、資料管線、服務狀態
        </Text>
      </div>
      <Tabs defaultActiveKey="ai-chat" items={tabItems} />
    </div>
  );
};

export default AIAssistantManagementPage;
