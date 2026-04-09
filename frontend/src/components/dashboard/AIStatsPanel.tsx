/**
 * AI 使用統計面板
 *
 * 顯示 AI 服務的使用統計資訊，包括：
 * - 總請求數、快取命中率、速率限制次數、平均延遲
 * - 各功能使用佔比圓餅圖 (Recharts PieChart)
 * - 來源分布 (Groq / Ollama / Fallback)
 * - 搜尋趨勢折線圖 (daily_trend)
 * - 策略分布、Top 查詢列表
 *
 * @version 2.0.0
 * @date 2026-02-07
 * @updated 2026-02-24 - 新增搜尋統計 Dashboard 區塊
 */

import React, { useMemo } from 'react';
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

import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { SearchStatsDashboard } from './SearchStatsDashboard';
import { useQuery } from '@tanstack/react-query';
import { aiApi } from '../../api/aiApi';
import { useResponsive } from '../../hooks';
import { getAIFeatureName, type AIFeatureType } from '../../config/aiConfig';
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

  // 與 UnifiedAgentPage (admin 模式) 共享 queryKey，避免重複請求
  const { data: stats = null, isLoading: statsLoading } = useQuery({
    queryKey: ['ai-management', 'ai-stats'],
    queryFn: () => aiApi.getStats(),
    staleTime: 2 * 60 * 1000,
    retry: false,
  });

  const { data: searchStats = null, isLoading: searchLoading } = useQuery({
    queryKey: ['ai-management', 'search-stats'],
    queryFn: () => aiApi.getSearchStats(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const { data: health = null } = useQuery({
    queryKey: ['ai-management', 'health'],
    queryFn: () => aiApi.checkHealth(),
    staleTime: 2 * 60 * 1000,
    retry: false,
  });

  const { data: embeddingStats = null } = useQuery({
    queryKey: ['ai-management', 'embedding-stats'],
    queryFn: () => aiApi.getEmbeddingStats(),
    staleTime: 2 * 60 * 1000,
    retry: false,
  });

  const loading = statsLoading || searchLoading;

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
        {/* AI 服務健康狀態 */}
        {health && (
          <div style={{ marginBottom: 16, padding: '10px 12px', background: '#fafafa', borderRadius: 6, border: '1px solid #f0f0f0' }}>
            <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13 }}>
              AI 服務狀態
            </Text>
            <Row gutter={[12, 8]}>
              <Col xs={12} sm={6}>
                <Space size={4}>
                  {health.groq.available
                    ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
                    : <CloseCircleOutlined style={{ color: '#f5222d', fontSize: 14 }} />}
                  <div>
                    <Text strong style={{ fontSize: 12, display: 'block' }}>Groq API</Text>
                    <Text type={health.groq.available ? 'success' : 'danger'} style={{ fontSize: 11 }}>
                      {health.groq.available ? '正常' : '離線'}
                    </Text>
                  </div>
                </Space>
              </Col>
              <Col xs={12} sm={6}>
                <Space size={4}>
                  {health.ollama.available
                    ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
                    : <CloseCircleOutlined style={{ color: '#f5222d', fontSize: 14 }} />}
                  <div>
                    <Text strong style={{ fontSize: 12, display: 'block' }}>Ollama</Text>
                    <Text type={health.ollama.available ? 'success' : 'danger'} style={{ fontSize: 11 }}>
                      {health.ollama.available ? '正常' : '離線'}
                    </Text>
                  </div>
                </Space>
              </Col>
              <Col xs={12} sm={6}>
                <Space size={4}>
                  {embeddingStats?.pgvector_enabled
                    ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
                    : <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 14 }} />}
                  <div>
                    <Text strong style={{ fontSize: 12, display: 'block' }}>pgvector</Text>
                    <Text type={embeddingStats?.pgvector_enabled ? 'success' : 'warning'} style={{ fontSize: 11 }}>
                      {embeddingStats?.pgvector_enabled ? '已啟用' : '未啟用'}
                    </Text>
                  </div>
                </Space>
              </Col>
              {health.rate_limit && (
                <Col xs={12} sm={6}>
                  <Space size={4}>
                    {health.rate_limit.can_proceed
                      ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
                      : <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 14 }} />}
                    <div>
                      <Text strong style={{ fontSize: 12, display: 'block' }}>速率限制</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {health.rate_limit.current_requests}/{health.rate_limit.max_requests}
                      </Text>
                    </div>
                  </Space>
                </Col>
              )}
            </Row>
            {/* Embedding 覆蓋率 */}
            {embeddingStats && embeddingStats.pgvector_enabled && (
              <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>Embedding 覆蓋率</Text>
                  <Progress
                    percent={Math.round(embeddingStats.coverage_percent)}
                    size="small"
                    style={{ flex: 1 }}
                    strokeColor={embeddingStats.coverage_percent >= 80 ? '#52c41a' : embeddingStats.coverage_percent >= 50 ? '#faad14' : '#f5222d'}
                  />
                  <Text type="secondary" style={{ fontSize: 10, flexShrink: 0 }}>
                    {embeddingStats.with_embedding}/{embeddingStats.total_documents}
                  </Text>
                </div>
              </div>
            )}
          </div>
        )}

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
              styles={
                (stats?.rate_limit_hits ?? 0) > 0
                  ? { content: { color: '#f5222d' } }
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

        {/* 搜尋統計 Dashboard */}
        {searchStats && <SearchStatsDashboard searchStats={searchStats} />}
      </Card>
    </Spin>
  );
};

export default AIStatsPanel;
