/**
 * 專案利潤排名 Bar Chart (Top 15)
 */
import React from 'react';
import { Card, Typography } from 'antd';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const { Text } = Typography;

interface ProfitItem {
  name: string;
  income: number;
  expense: number;
  net: number;
}

interface Props {
  data: ProfitItem[];
}

const ProfitRankingChart: React.FC<Props> = ({ data }) => (
  <Card title={<Text strong>專案利潤排名 (Top 15)</Text>} size="small">
    {data.length > 0 ? (
      <ResponsiveContainer width="100%" height={360}>
        <BarChart data={data} layout="vertical" margin={{ left: 80, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}K`} />
          <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value: number, name: string) => [
              `${value.toLocaleString()} 元`,
              name === 'income' ? '收入' : name === 'expense' ? '支出' : '淨額',
            ]}
          />
          <Bar dataKey="income" name="收入" fill="#52c41a" barSize={8} />
          <Bar dataKey="expense" name="支出" fill="#ff4d4f" barSize={8} />
          <Bar dataKey="net" name="淨額" barSize={10}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={entry.net >= 0 ? '#1890ff' : '#faad14'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    ) : (
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無專案資料</div>
    )}
  </Card>
);

export default ProfitRankingChart;
