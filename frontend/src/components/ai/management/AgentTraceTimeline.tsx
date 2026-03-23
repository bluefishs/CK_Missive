/**
 * Agent Trace Timeline — 甘特圖式工具呼叫時序視覺化
 *
 * 展示單筆 Agent Trace 的 tool_calls 執行順序與耗時，
 * 以水平 bar 呈現各工具的 duration_ms，類似甘特圖效果。
 *
 * @version 1.0.0
 * @created 2026-03-23
 */

import React, { useState } from 'react';
import {
  Card,
  Empty,
  Select,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { aiApi } from '../../../api/aiApi';
import type { TraceToolCallItem } from '../../../types/ai';

const { Text } = Typography;

/** 工具顏色映射 (按 call_order 循環) */
const BAR_COLORS = [
  '#1890ff', '#52c41a', '#fa8c16', '#722ed1',
  '#13c2c2', '#eb2f96', '#f5222d', '#2f54eb',
];

const getBarColor = (index: number, success: boolean) =>
  success ? BAR_COLORS[index % BAR_COLORS.length] : '#ff4d4f';

interface TraceSelectItem {
  id: number;
  question: string;
  total_ms: number;
  tools_used?: string[] | null;
  created_at?: string | null;
}

interface AgentTraceTimelineProps {
  traces: TraceSelectItem[];
}

export const AgentTraceTimeline: React.FC<AgentTraceTimelineProps> = ({ traces }) => {
  const [selectedTraceId, setSelectedTraceId] = useState<number | null>(null);

  const { data: detail, isLoading } = useQuery({
    queryKey: ['agent-trace-detail', selectedTraceId],
    queryFn: () => aiApi.getTraceDetail(selectedTraceId!),
    enabled: selectedTraceId !== null,
    staleTime: 5 * 60_000,
  });

  const toolCalls = detail?.tool_calls ?? [];
  const totalMs = detail?.total_ms ?? 0;

  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          <span>Agent Trace Timeline</span>
        </Space>
      }
      size="small"
      extra={
        <Select
          placeholder="選擇 Trace 記錄"
          style={{ width: 320 }}
          size="small"
          allowClear
          showSearch
          filterOption={(input, option) =>
            (option?.label as string ?? '').toLowerCase().includes(input.toLowerCase())
          }
          value={selectedTraceId}
          onChange={(val) => setSelectedTraceId(val ?? null)}
          options={traces.slice(0, 50).map((t) => ({
            label: `#${t.id} ${t.question.slice(0, 40)}${t.question.length > 40 ? '...' : ''} (${t.total_ms}ms)`,
            value: t.id,
          }))}
        />
      }
    >
      {!selectedTraceId && (
        <Empty description="選擇一筆 Trace 記錄以檢視工具呼叫時序" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      {selectedTraceId && isLoading && (
        <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
      )}

      {selectedTraceId && !isLoading && detail && (
        <div>
          {/* 摘要列 */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined /> 總耗時: <Text strong>{totalMs}ms</Text>
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              路由: <Tag color="blue" style={{ fontSize: 11 }}>{detail.route_type}</Tag>
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              迭代: <Text strong>{detail.iterations}</Text>
            </Text>
            {detail.correction_triggered && <Tag color="orange" style={{ fontSize: 11 }}>自動修正</Tag>}
            {detail.react_triggered && <Tag color="purple" style={{ fontSize: 11 }}>ReAct</Tag>}
            {detail.model_used && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                模型: <Tag style={{ fontSize: 11 }}>{detail.model_used}</Tag>
              </Text>
            )}
          </div>

          {/* 甘特圖 */}
          {toolCalls.length === 0 ? (
            <Empty description="此 Trace 無工具呼叫記錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <GanttChart toolCalls={toolCalls} totalMs={totalMs} />
          )}

          {/* 問題預覽 */}
          {detail.answer_preview && (
            <div style={{ marginTop: 12, padding: '8px 12px', background: '#fafafa', borderRadius: 4 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>回答預覽：</Text>
              <div style={{ fontSize: 12, marginTop: 4 }}>{detail.answer_preview}</div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

/** 甘特圖渲染 */
const GanttChart: React.FC<{ toolCalls: TraceToolCallItem[]; totalMs: number }> = ({
  toolCalls,
  totalMs,
}) => {
  // 計算每個 bar 的起始偏移（累加 duration）
  const maxDuration = Math.max(totalMs, 1);
  let cumulativeMs = 0;
  const bars = toolCalls.map((tc, i) => {
    const start = cumulativeMs;
    cumulativeMs += tc.duration_ms;
    return { ...tc, start, index: i };
  });

  return (
    <div style={{ position: 'relative' }}>
      {/* 時間軸刻度 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, padding: '0 100px 0 0' }}>
        <Text type="secondary" style={{ fontSize: 10 }}>0ms</Text>
        <Text type="secondary" style={{ fontSize: 10 }}>{Math.round(maxDuration / 2)}ms</Text>
        <Text type="secondary" style={{ fontSize: 10 }}>{maxDuration}ms</Text>
      </div>

      {/* Bars */}
      {bars.map((bar) => {
        const leftPct = (bar.start / maxDuration) * 100;
        const widthPct = Math.max((bar.duration_ms / maxDuration) * 100, 1);
        const color = getBarColor(bar.index, bar.success);

        return (
          <Tooltip
            key={`${bar.tool_name}-${bar.call_order}`}
            title={
              <div>
                <div><strong>{bar.tool_name}</strong></div>
                <div>耗時: {bar.duration_ms}ms</div>
                <div>結果: {bar.result_count} 筆</div>
                <div>狀態: {bar.success ? '成功' : '失敗'}</div>
                {bar.error_message && <div style={{ color: '#ff7875' }}>錯誤: {bar.error_message}</div>}
              </div>
            }
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                height: 28,
                marginBottom: 3,
              }}
            >
              {/* 標籤 */}
              <div style={{
                width: 96,
                flexShrink: 0,
                fontSize: 11,
                textAlign: 'right',
                paddingRight: 8,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {bar.success
                  ? <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 3 }} />
                  : <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 3 }} />
                }
                <Text style={{ fontSize: 11 }}>{bar.tool_name}</Text>
              </div>

              {/* Bar 軌道 */}
              <div style={{ flex: 1, position: 'relative', height: 20, background: '#f5f5f5', borderRadius: 3 }}>
                <div
                  style={{
                    position: 'absolute',
                    left: `${leftPct}%`,
                    width: `${widthPct}%`,
                    height: '100%',
                    background: color,
                    borderRadius: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minWidth: 24,
                    transition: 'opacity 0.2s',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = '0.8'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                >
                  <Text style={{ fontSize: 10, color: '#fff', fontWeight: 500 }}>
                    {bar.duration_ms}ms
                  </Text>
                </div>
              </div>
            </div>
          </Tooltip>
        );
      })}

      {/* 總覽 */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
        <Text type="secondary" style={{ fontSize: 11 }}>
          工具呼叫 {toolCalls.length} 次
        </Text>
        <Text type="secondary" style={{ fontSize: 11 }}>
          工具耗時 {cumulativeMs}ms / 總計 {maxDuration}ms
          ({maxDuration > 0 ? Math.round((cumulativeMs / maxDuration) * 100) : 0}%)
        </Text>
        <Text type="secondary" style={{ fontSize: 11 }}>
          成功率 {toolCalls.filter(t => t.success).length}/{toolCalls.length}
        </Text>
      </div>
    </div>
  );
};

export default AgentTraceTimeline;
