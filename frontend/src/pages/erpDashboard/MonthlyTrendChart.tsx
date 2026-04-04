/**
 * 月度收支趨勢折線圖 (近 12 個月)
 */
import React from 'react';
import { Card, Typography } from 'antd';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const { Text } = Typography;

interface TrendMonth {
  month: string;
  income: number;
  expense: number;
  net: number;
}

interface Props {
  data: TrendMonth[];
  loading?: boolean;
}

const MonthlyTrendChart: React.FC<Props> = ({ data, loading }) => (
  <Card title={<Text strong>月度收支趨勢 (近 12 個月)</Text>} size="small" loading={loading}>
    {data.length > 0 ? (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ left: 10, right: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`} />
          <Tooltip formatter={(value: number, name: string) => [
            `${value.toLocaleString()} 元`,
            name === 'income' ? '收入' : name === 'expense' ? '支出' : '淨額',
          ]} />
          <Line type="monotone" dataKey="income" name="收入" stroke="#52c41a" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="expense" name="支出" stroke="#ff4d4f" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="net" name="淨額" stroke="#1890ff" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} />
          <Legend />
        </LineChart>
      </ResponsiveContainer>
    ) : (
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無趨勢資料</div>
    )}
  </Card>
);

export default MonthlyTrendChart;
