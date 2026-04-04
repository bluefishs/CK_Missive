/**
 * 預算使用率排行 Bar Chart (Top 15)
 */
import React from 'react';
import { Card, Typography } from 'antd';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { BudgetRankingItem } from '../../types/erp';

const { Text } = Typography;

interface Props {
  data: BudgetRankingItem[];
  loading?: boolean;
}

const BudgetRankingChart: React.FC<Props> = ({ data, loading }) => (
  <Card title={<Text strong>預算使用率排行 (Top 15)</Text>} size="small" loading={loading}>
    {data.length > 0 ? (
      <ResponsiveContainer width="100%" height={320}>
        <BarChart
          data={data.map((r) => ({
            name: r.case_name || r.case_code,
            usage: r.usage_pct ?? 0,
            alert: r.alert,
          }))}
          layout="vertical"
          margin={{ left: 100, right: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, (max: number) => Math.max(max, 100)]} tickFormatter={(v: number) => `${v}%`} />
          <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, '使用率']} />
          <Bar dataKey="usage" name="使用率" barSize={14}>
            {data.map((r, idx) => (
              <Cell key={idx} fill={r.alert === 'critical' ? '#ff4d4f' : r.alert === 'warning' ? '#faad14' : '#52c41a'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    ) : (
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無排行資料</div>
    )}
  </Card>
);

export default BudgetRankingChart;
