/**
 * 公文趨勢圖元件
 *
 * 顯示過去 12 個月每月收文/發文數量的折線圖。
 * 使用 Recharts LineChart 搭配 Ant Design Card 外框。
 * 支援響應式設計：手機/平板/桌面三種高度。
 *
 * @version 1.0.0
 * @date 2026-02-07
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Card, Spin, Empty } from 'antd';
import { LineChartOutlined } from '@ant-design/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

import { documentsApi } from '../../api/documentsApi';
import type { DocumentTrendItem } from '../../types/api';
import { useResponsive } from '../../hooks';
import { logger } from '../../services/logger';

/** 圖表高度依裝置類型區分 */
const CHART_HEIGHTS = {
  mobile: 220,
  tablet: 280,
  desktop: 320,
} as const;

/** 折線顏色常數 */
const LINE_COLORS = {
  received: '#1890ff',
  sent: '#52c41a',
} as const;

/**
 * 公文趨勢圖
 *
 * 呼叫 documentsApi.getDocumentTrends() 取得過去 12 個月收發文統計，
 * 以 LineChart 呈現趨勢變化。
 */
export const DocumentTrendsChart: React.FC = () => {
  const { isMobile, isTablet, responsiveValue } = useResponsive();

  const [trends, setTrends] = useState<DocumentTrendItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const chartHeight = responsiveValue<number>({
    mobile: CHART_HEIGHTS.mobile,
    tablet: CHART_HEIGHTS.tablet,
    desktop: CHART_HEIGHTS.desktop,
  }) ?? CHART_HEIGHTS.desktop;

  const fetchTrends = useCallback(async () => {
    setLoading(true);
    try {
      const response = await documentsApi.getDocumentTrends();
      setTrends(response.trends);
    } catch (error) {
      logger.error('取得公文趨勢資料失敗:', error);
      // 保留現有資料，不清空
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrends();
  }, [fetchTrends]);

  const renderChart = () => {
    if (!loading && trends.length === 0) {
      return <Empty description="暫無趨勢資料" style={{ padding: '40px 0' }} />;
    }

    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart
          data={trends}
          margin={{
            top: 5,
            right: isMobile ? 10 : 30,
            left: isMobile ? 0 : 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: isMobile ? 11 : 13 }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: isMobile ? 11 : 13 }}
          />
          <Tooltip />
          <Legend
            wrapperStyle={{ fontSize: isTablet || isMobile ? 12 : 14 }}
          />
          <Line
            type="monotone"
            dataKey="received"
            stroke={LINE_COLORS.received}
            name="收文"
            strokeWidth={2}
            dot={{ r: isMobile ? 2 : 4 }}
            activeDot={{ r: isMobile ? 4 : 6 }}
          />
          <Line
            type="monotone"
            dataKey="sent"
            stroke={LINE_COLORS.sent}
            name="發文"
            strokeWidth={2}
            dot={{ r: isMobile ? 2 : 4 }}
            activeDot={{ r: isMobile ? 4 : 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  return (
    <Card
      title={
        <span>
          <LineChartOutlined style={{ marginRight: 8 }} />
          公文趨勢
        </span>
      }
      size="small"
    >
      <Spin spinning={loading}>
        {renderChart()}
      </Spin>
    </Card>
  );
};

export default DocumentTrendsChart;
