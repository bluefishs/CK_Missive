/**
 * Budget Analysis Charts
 *
 * Extracted chart components for BudgetAnalysisTab:
 * - CategoryPieChart: case category distribution pie chart
 * - StatusBarChart: execution status bar chart
 */

import React from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
} from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { formatCurrency, COLORS } from './constants';

const { Text } = Typography;

interface ChartDataItem {
  name: string;
  count: number;
  amount: number;
}

// =============================================================================
// CategoryPieChart
// =============================================================================

interface CategoryPieChartProps {
  data: ChartDataItem[];
  totalAmount: number;
  totalProjects: number;
  filterCategory: string | null;
  setFilterCategory: (v: string | null) => void;
  handleCategoryClick: (name: string) => void;
  isMobile: boolean;
}

export const CategoryPieChart: React.FC<CategoryPieChartProps> = ({
  data,
  totalAmount,
  totalProjects,
  filterCategory,
  setFilterCategory,
  handleCategoryClick,
  isMobile,
}) => (
  <Card
    title={
      <Space>
        <span>案件類別分布</span>
        {!filterCategory && (
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
            (點擊篩選)
          </Text>
        )}
        {totalAmount === 0 && totalProjects > 0 && (
          <Text type="warning" style={{ fontSize: 11, fontWeight: 'normal' }}>
            (依案件數繪製)
          </Text>
        )}
      </Space>
    }
    size="small"
    extra={
      filterCategory && (
        <Button type="link" size="small" onClick={() => setFilterCategory(null)}>
          取消篩選
        </Button>
      )
    }
  >
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="45%"
          labelLine={false}
          label={
            isMobile
              ? undefined
              : (entry: { name?: string }) => (entry.name ?? '').replace(/^0\d/, '').substring(0, 4)
          }
          outerRadius={isMobile ? 70 : 80}
          fill="#8884d8"
          dataKey={totalAmount > 0 ? 'amount' : 'count'}
          onClick={(d) => handleCategoryClick(d.name)}
          style={{ cursor: 'pointer' }}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={COLORS[index % COLORS.length]}
              opacity={filterCategory && filterCategory !== entry.name ? 0.3 : 1}
              stroke={filterCategory === entry.name ? '#000' : undefined}
              strokeWidth={filterCategory === entry.name ? 2 : 0}
            />
          ))}
        </Pie>
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const d = payload[0].payload;
              return (
                <div style={{ background: '#fff', padding: '8px 12px', border: '1px solid #ccc', borderRadius: 4 }}>
                  <div style={{ fontWeight: 'bold' }}>{d.name}</div>
                  <div>案件數: {d.count} 件</div>
                  <div>經費: {formatCurrency(d.amount)}</div>
                  <div style={{ fontSize: 12, color: '#1890ff', marginTop: 4 }}>
                    {filterCategory === d.name ? '點擊取消篩選' : '點擊篩選此類別'}
                  </div>
                </div>
              );
            }
            return null;
          }}
        />
        <Legend
          layout="horizontal"
          verticalAlign="bottom"
          align="center"
          wrapperStyle={{ paddingTop: 16 }}
          formatter={(value: string, entry: unknown) => {
            const d = (entry as { payload?: { count?: number; amount?: number } })?.payload;
            return `${value}: ${d?.count ?? 0}件 ${formatCurrency(d?.amount ?? 0)}`;
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  </Card>
);

// =============================================================================
// StatusBarChart
// =============================================================================

interface StatusBarChartProps {
  data: ChartDataItem[];
  filterStatus: string | null;
  setFilterStatus: (v: string | null) => void;
  handleStatusClick: (name: string) => void;
}

export const StatusBarChart: React.FC<StatusBarChartProps> = ({
  data,
  filterStatus,
  setFilterStatus,
  handleStatusClick,
}) => (
  <Card
    title={
      <Space>
        <span>執行狀態分布</span>
        {!filterStatus && (
          <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
            (點擊篩選)
          </Text>
        )}
      </Space>
    }
    size="small"
    extra={
      filterStatus && (
        <Button type="link" size="small" onClick={() => setFilterStatus(null)}>
          取消篩選
        </Button>
      )
    }
  >
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="name" type="category" width={80} />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const d = payload[0].payload;
              return (
                <div style={{ background: '#fff', padding: '8px 12px', border: '1px solid #ccc', borderRadius: 4 }}>
                  <div style={{ fontWeight: 'bold' }}>{d.name}</div>
                  <div>案件數: {d.count} 件</div>
                  <div>經費: {formatCurrency(d.amount)}</div>
                  <div style={{ fontSize: 12, color: '#1890ff', marginTop: 4 }}>
                    {filterStatus === d.name ? '點擊取消篩選' : '點擊篩選此狀態'}
                  </div>
                </div>
              );
            }
            return null;
          }}
        />
        <Bar
          dataKey="count"
          name="案件數"
          onClick={(d: { name?: string }) => d.name && handleStatusClick(d.name)}
          style={{ cursor: 'pointer' }}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={COLORS[index % COLORS.length]}
              opacity={filterStatus && filterStatus !== entry.name ? 0.3 : 1}
              stroke={filterStatus === entry.name ? '#000' : undefined}
              strokeWidth={filterStatus === entry.name ? 2 : 0}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </Card>
);
