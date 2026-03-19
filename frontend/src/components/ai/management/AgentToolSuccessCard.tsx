/**
 * Agent 工具成功率卡片
 *
 * 顯示工具成功率統計 + BarChart + 降級警示
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import React from 'react';
import { Card, Col, Row, Statistic, Typography } from 'antd';
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { ToolSuccessRatesResponse } from '../../../types/ai';

const { Text } = Typography;

interface ToolChartItem {
  name: string;
  success_rate: number;
  avg_latency: number;
  calls: number;
}

interface AgentToolSuccessCardProps {
  toolStats: ToolSuccessRatesResponse | null | undefined;
  toolChartData: ToolChartItem[];
}

export const AgentToolSuccessCard: React.FC<AgentToolSuccessCardProps> = ({
  toolStats,
  toolChartData,
}) => {
  return (
    <Card
      title={<><ThunderboltOutlined /> 工具成功率（近 7 天）</>}
      size="small"
    >
      {/* 降級工具警示 */}
      {toolStats?.degraded_tools && toolStats.degraded_tools.length > 0 && (
        <div style={{
          marginBottom: 12,
          padding: '8px 12px',
          background: '#fff7e6',
          border: '1px solid #ffe7ba',
          borderRadius: 6,
        }}>
          <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
          <Text type="warning">
            降級工具：{toolStats.degraded_tools.join(', ')}
          </Text>
        </div>
      )}

      {/* 摘要卡片 */}
      <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Statistic
            title="活躍工具數"
            value={toolStats?.tools?.length ?? 0}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="總呼叫次數"
            value={toolStats?.tools?.reduce((s, t) => s + t.total_calls, 0) ?? 0}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="平均成功率"
            value={
              toolStats?.tools?.length
                ? Math.round(
                    (toolStats.tools.reduce((s, t) => s + t.success_rate, 0) /
                      toolStats.tools.length) * 100
                  )
                : 0
            }
            suffix="%"
            prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="降級工具"
            value={toolStats?.degraded_tools?.length ?? 0}
            prefix={
              (toolStats?.degraded_tools?.length ?? 0) > 0
                ? <ExclamationCircleOutlined style={{ color: '#f5222d' }} />
                : <CheckCircleOutlined style={{ color: '#52c41a' }} />
            }
          />
        </Col>
      </Row>

      {/* 成功率 BarChart */}
      {toolChartData.length > 0 && (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={toolChartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="name"
              width={100}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'success_rate') return [`${value}%`, '成功率'];
                return [value, name];
              }}
            />
            <Bar
              dataKey="success_rate"
              radius={[0, 4, 4, 0]}
            >
              {toolChartData.map((entry, i) => (
                <Cell
                  key={`bar-${i}`}
                  fill={entry.success_rate >= 80 ? '#52c41a' : entry.success_rate >= 50 ? '#faad14' : '#f5222d'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
};
