/**
 * AI 搜尋統計儀表板
 *
 * 從 AIStatsPanel 拆分，獨立顯示搜尋統計：
 * - 搜尋摘要卡片 (累計/今日/延遲/命中率)
 * - 近 30 天搜尋趨勢折線圖
 * - 策略分布 + 來源分布並排圖表
 * - Top 10 熱門查詢表格
 *
 * @version 1.0.0
 * @date 2026-03-29
 */

import React, { useMemo } from 'react';
import {
  Statistic,
  Row,
  Col,
  Table,
  Typography,
} from 'antd';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import type { SearchStatsResponse } from '../../types/ai';

const { Text } = Typography;
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];

interface SearchStatsDashboardProps {
  searchStats: SearchStatsResponse;
}

export const SearchStatsDashboard: React.FC<SearchStatsDashboardProps> = ({ searchStats }) => {
  const strategyData = useMemo(() => {
    if (!searchStats?.strategy_distribution) return [];
    const labelMap: Record<string, string> = {
      keyword: '關鍵字', similarity: '向量', hybrid: '混合', semantic: '語意',
    };
    return Object.entries(searchStats.strategy_distribution)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ name: labelMap[k] || k, value: v }));
  }, [searchStats]);

  const topQueryColumns = useMemo(() => [
    { title: '查詢', dataIndex: 'query', key: 'query', ellipsis: true, width: 200 },
    { title: '次數', dataIndex: 'count', key: 'count', width: 60 },
    { title: '平均筆數', dataIndex: 'avg_results', key: 'avg_results', width: 80,
      render: (v: number) => v.toFixed(1) },
  ], []);

  return (
    <div style={{ marginTop: 24, borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
      <Text strong style={{ display: 'block', marginBottom: 12, fontSize: 14 }}>
        AI 搜尋統計
      </Text>

      {/* 搜尋摘要卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Statistic title="累計搜尋" value={searchStats.total_searches} />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic title="今日搜尋" value={searchStats.today_searches} />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic title="平均延遲" value={searchStats.avg_latency_ms} suffix="ms" precision={0} />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="規則引擎命中"
            value={searchStats.rule_engine_hit_rate * 100}
            suffix="%"
            precision={1}
          />
        </Col>
      </Row>

      {/* 搜尋趨勢折線圖 */}
      {searchStats.daily_trend.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            近 30 天搜尋趨勢
          </Text>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={searchStats.daily_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip
                labelFormatter={(label: string) => `日期: ${label}`}
                formatter={(value: number) => [`${value} 次`, '搜尋次數']}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#1890ff"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 策略分布 + 來源分布 並排 */}
      <Row gutter={[16, 16]}>
        {strategyData.length > 0 && (
          <Col xs={24} sm={12}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              搜尋策略分布
            </Text>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={strategyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#722ed1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Col>
        )}
        {searchStats.source_distribution && Object.keys(searchStats.source_distribution).length > 0 && (
          <Col xs={24} sm={12}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              搜尋來源分布
            </Text>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={Object.entries(searchStats.source_distribution)
                    .filter(([, v]) => v > 0)
                    .map(([k, v]) => ({ name: k, value: v }))}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={65}
                  dataKey="value"
                  nameKey="name"
                  label
                >
                  {Object.keys(searchStats.source_distribution).map((_, index) => (
                    <Cell key={`src-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Col>
        )}
      </Row>

      {/* Top 10 查詢 */}
      {searchStats.top_queries.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            Top 10 熱門查詢
          </Text>
          <Table
            dataSource={searchStats.top_queries}
            columns={topQueryColumns}
            rowKey="query"
            size="small"
            pagination={false}
            style={{ fontSize: 12 }}
          />
        </div>
      )}
    </div>
  );
};
