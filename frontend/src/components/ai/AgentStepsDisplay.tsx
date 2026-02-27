/**
 * Agent 推理步驟視覺化元件
 *
 * 顯示 Agentic 模式下的多步推理過程：思考、工具呼叫、工具結果。
 * 從 RAGChatPanel.tsx 提取。
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import React from 'react';
import { Typography, Steps } from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  NodeIndexOutlined,
  DatabaseOutlined,
  LoadingOutlined,
  BulbOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  BarChartOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

/** 推理步驟 */
export interface AgentStepInfo {
  type: 'thinking' | 'tool_call' | 'tool_result';
  step_index: number;
  step?: string;
  tool?: string;
  params?: Record<string, unknown>;
  summary?: string;
  count?: number;
}

export const TOOL_ICONS: Record<string, React.ReactNode> = {
  search_documents: <SearchOutlined />,
  search_dispatch_orders: <FileTextOutlined />,
  search_entities: <NodeIndexOutlined />,
  get_entity_detail: <DatabaseOutlined />,
  find_similar: <CopyOutlined />,
  get_statistics: <BarChartOutlined />,
};

export const TOOL_LABELS: Record<string, string> = {
  search_documents: '搜尋公文',
  search_dispatch_orders: '搜尋派工單',
  search_entities: '搜尋實體',
  get_entity_detail: '實體詳情',
  find_similar: '相似公文',
  get_statistics: '統計資訊',
};

export const AgentStepsDisplay: React.FC<{ steps: AgentStepInfo[]; streaming: boolean }> = ({
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

export default AgentStepsDisplay;
