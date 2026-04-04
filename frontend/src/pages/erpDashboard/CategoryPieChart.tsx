/**
 * 支出分類圓餅圖
 */
import React from 'react';
import { Card, Typography } from 'antd';
import {
  PieChart, Pie, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';

const { Text } = Typography;

const PIE_COLORS = [
  '#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1',
  '#13c2c2', '#eb2f96', '#fa8c16', '#2f54eb', '#a0d911',
];

interface CategoryItem {
  name: string;
  value: number;
}

interface Props {
  data: CategoryItem[];
}

const CategoryPieChart: React.FC<Props> = ({ data }) => (
  <Card title={<Text strong>支出分類分布</Text>} size="small">
    {data.length > 0 ? (
      <ResponsiveContainer width="100%" height={360}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={120}
            dataKey="value"
            label={(props) => {
              const { name, percent } = props as { name: string; percent: number };
              return `${name} ${(percent * 100).toFixed(1)}%`;
            }}
            labelLine={{ strokeWidth: 1 }}
          >
            {data.map((_, idx) => (
              <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => [`${value.toLocaleString()} 元`]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    ) : (
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>無分類資料</div>
    )}
  </Card>
);

export default CategoryPieChart;
