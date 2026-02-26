/**
 * AI 助理管理頁面
 *
 * Version: 2.2.0
 * Created: 2026-02-09
 * Updated: 2026-02-26 — 將 6 個 Tab 元件拆分至 components/ai/management/
 *
 * 統一管理入口，整合搜尋統計、搜尋歷史、同義詞管理、Prompt 管理、
 * Embedding 管線、知識圖譜、AI 服務監控、Ollama 管理。
 */
import React, { useMemo } from 'react';
import { Tabs, Typography } from 'antd';
import {
  ApartmentOutlined,
  BarChartOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  HeartOutlined,
  HistoryOutlined,
  RobotOutlined,
  TagsOutlined,
} from '@ant-design/icons';

import { SynonymManagementContent } from './AISynonymManagementPage';
import { PromptManagementContent } from './AIPromptManagementPage';
import { RAGChatPanel } from '../components/ai/RAGChatPanel';
import {
  OverviewTab,
  HistoryTab,
  EmbeddingTab,
  KnowledgeGraphTab,
  ServiceMonitorTab,
  OllamaManagementTab,
} from '../components/ai/management';

const { Title, Text } = Typography;

const AIAssistantManagementPage: React.FC = () => {
  const tabItems = useMemo(() => [
    {
      key: 'rag-chat',
      label: (
        <span><RobotOutlined /> RAG 問答</span>
      ),
      children: <RAGChatPanel />,
    },
    {
      key: 'overview',
      label: (
        <span><BarChartOutlined /> 搜尋總覽</span>
      ),
      children: <OverviewTab />,
    },
    {
      key: 'history',
      label: (
        <span><HistoryOutlined /> 搜尋歷史</span>
      ),
      children: <HistoryTab />,
    },
    {
      key: 'synonyms',
      label: (
        <span><TagsOutlined /> 同義詞管理</span>
      ),
      children: <SynonymManagementContent />,
    },
    {
      key: 'prompts',
      label: (
        <span><RobotOutlined /> Prompt 管理</span>
      ),
      children: <PromptManagementContent />,
    },
    {
      key: 'embedding',
      label: (
        <span><DatabaseOutlined /> Embedding 管理</span>
      ),
      children: <EmbeddingTab />,
    },
    {
      key: 'graph',
      label: (
        <span><ApartmentOutlined /> 知識圖譜</span>
      ),
      children: <KnowledgeGraphTab />,
    },
    {
      key: 'monitor',
      label: (
        <span><HeartOutlined /> AI 服務監控</span>
      ),
      children: <ServiceMonitorTab />,
    },
    {
      key: 'ollama',
      label: (
        <span><CloudServerOutlined /> Ollama 管理</span>
      ),
      children: <OllamaManagementTab />,
    },
  ], []);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <ExperimentOutlined /> AI 助理管理
        </Title>
        <Text type="secondary">
          RAG 公文問答、搜尋統計分析、歷史記錄查詢、同義詞管理、Prompt 版本管理、Embedding 管線、知識圖譜、AI 服務監控、Ollama 管理
        </Text>
      </div>
      <Tabs defaultActiveKey="rag-chat" items={tabItems} />
    </div>
  );
};

export default AIAssistantManagementPage;
