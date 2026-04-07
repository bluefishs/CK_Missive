/**
 * CategoryPieChart — 標案類別分布共用圓餅圖
 *
 * 統一處理：
 * - 超過 MAX_SLICES 自動合併為「其他」
 * - 甜甜圈樣式 (innerRadius)
 * - Label 顯示類別名+佔比%
 * - Tooltip 顯示筆數
 *
 * 用法：
 *   <CategoryPieChart data={category_distribution} />
 *
 * @version 1.0.0
 */
import React from 'react';
import { Empty } from 'antd';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
} from 'recharts';

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];
const MAX_SLICES = 6;

interface CategoryPieChartProps {
  data: Array<{ name: string; value: number }>;
  height?: number;
}

const CategoryPieChart: React.FC<CategoryPieChartProps> = ({ data, height = 280 }) => {
  if (!data || data.length === 0) return <Empty description="無類別資料" />;

  // 合併小項
  let pieData = data;
  if (data.length > MAX_SLICES) {
    const top = data.slice(0, MAX_SLICES - 1);
    const otherValue = data.slice(MAX_SLICES - 1).reduce((s, d) => s + d.value, 0);
    pieData = [...top, { name: `其他 (${data.length - MAX_SLICES + 1} 類)`, value: otherValue }];
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={pieData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={Math.min(height / 3, 90)}
          innerRadius={Math.min(height / 3, 90) * 0.4}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          label={((p: any) => `${p.name} ${(p.percent * 100).toFixed(0)}%`) as any}
          labelLine={false}
          fontSize={12}
        >
          {pieData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => [`${v} 筆`, '標案數']} />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default React.memo(CategoryPieChart);
