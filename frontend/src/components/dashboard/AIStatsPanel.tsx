/**
 * AI 使用統計面板
 *
 * 顯示 AI 服務的使用統計資訊，包括：
 * - 總請求數、快取命中率、速率限制次數、平均延遲
 * - 各功能使用佔比圓餅圖 (Recharts PieChart)
 * - 來源分布 (Groq / Ollama / Fallback)
 *
 * @version 1.0.0
 * @date 2026-02-07
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Statistic,
  Progress,
  Tag,
  Row,
  Col,
  Spin,
  Empty,
  Space,
  Typography,
} from 'antd';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

import { aiApi } from '../../api/aiApi';
import { useResponsive } from '../../hooks';
import { getAIFeatureName, type AIFeatureType } from '../../config/aiConfig';
import { logger } from '../../services/logger';
import type { AIStatsResponse } from '../../types/api';

const { Text } = Typography;

/** PieChart 色彩配置 */
const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'];

/** 功能佔比資料項 */
interface FeatureDataItem {
  name: string;
  value: number;
}

/**
 * AI 使用統計面板元件
 *
 * 呼叫 aiApi.getStats() 取得統計數據並以視覺化方式呈現。
 */
export const AIStatsPanel: React.FC = () => {
  const { isMobile } = useResponsive();
  const [stats, setStats] = useState<AIStatsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // 載入統計資料
  useEffect(() => {
    let cancelled = false;

    const fetchStats = async () => {
      setLoading(true);
      try {
        const data = await aiApi.getStats();
        if (!cancelled) {
          setStats(data);
        }
      } catch (error) {
        logger.error('載入 AI 使用統計失敗:', error);
        // 保留現有資料，不清空
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchStats();

    return () => {
      cancelled = true;
    };
  }, []);

  // 計算統計摘要
  const summary = useMemo(() => {
    if (!stats) return null;

    const features = Object.values(stats.by_feature);
    const totalCacheHits = features.reduce((sum, f) => sum + f.cache_hits, 0);
    const totalCacheMisses = features.reduce((sum, f) => sum + f.cache_misses, 0);
    const totalCacheAttempts = totalCacheHits + totalCacheMisses;
    const cacheHitRate = totalCacheAttempts > 0
      ? Math.round((totalCacheHits / totalCacheAttempts) * 100)
      : 0;

    const totalLatency = features.reduce((sum, f) => sum + f.total_latency_ms, 0);
    const totalCount = features.reduce((sum, f) => sum + f.count, 0);
    const avgLatency = totalCount > 0 ? Math.round(totalLatency / totalCount) : 0;

    return { cacheHitRate, avgLatency };
  }, [stats]);

  // 計算功能佔比圓餅圖資料
  const featureData = useMemo((): FeatureDataItem[] => {
    if (!stats || !stats.by_feature) return [];

    return Object.entries(stats.by_feature)
      .filter(([, feature]) => feature.count > 0)
      .map(([key, feature]) => ({
        name: getAIFeatureName(key as AIFeatureType),
        value: feature.count,
      }));
  }, [stats]);

  // 無資料狀態
  if (!loading && !stats) {
    return (
      <Card title="AI 使用統計" size="small">
        <Empty description="無法取得 AI 統計資料" />
      </Card>
    );
  }

  return (
    <Spin spinning={loading}>
      <Card title="AI 使用統計" size="small">
        {/* 統計卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic
              title="總請求數"
              value={stats?.total_requests ?? 0}
            />
          </Col>
          <Col xs={12} sm={6}>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>快取命中率</Text>
              <Progress
                type="circle"
                percent={summary?.cacheHitRate ?? 0}
                size={isMobile ? 60 : 80}
                strokeColor="#52c41a"
              />
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="速率限制次數"
              value={stats?.rate_limit_hits ?? 0}
              valueStyle={
                (stats?.rate_limit_hits ?? 0) > 0
                  ? { color: '#f5222d' }
                  : undefined
              }
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="平均延遲"
              value={summary?.avgLatency ?? 0}
              suffix="ms"
            />
          </Col>
        </Row>

        {/* 功能使用佔比 */}
        {featureData.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              功能使用佔比
            </Text>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={featureData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  nameKey="name"
                  label
                >
                  {featureData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* 來源分布 */}
        <div style={{ marginTop: 16 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            來源分布
          </Text>
          <Space wrap>
            <Tag color="blue">
              Groq: {stats?.groq_requests ?? 0}
            </Tag>
            <Tag color="green">
              Ollama: {stats?.ollama_requests ?? 0}
            </Tag>
            <Tag color="orange">
              Fallback: {stats?.fallback_requests ?? 0}
            </Tag>
          </Space>
        </div>
      </Card>
    </Spin>
  );
};

export default AIStatsPanel;
