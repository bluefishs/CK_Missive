/**
 * ServiceMonitorTab - AI service health monitoring
 *
 * Extracted from AIAssistantManagementPage.tsx
 */
import React from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Progress,
  Row,
  Spin,
  Statistic,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

import { aiApi } from '../../../api/aiApi';

export const ServiceMonitorTab: React.FC = () => {
  const {
    data: health = null,
    isLoading: healthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['ai-management', 'health'],
    queryFn: () => aiApi.checkHealth(),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });

  const {
    data: embStats = null,
    isLoading: embLoading,
  } = useQuery({
    queryKey: ['ai-management', 'embedding-stats'],
    queryFn: () => aiApi.getEmbeddingStats(),
    staleTime: 60 * 1000,
  });

  const {
    data: config = null,
  } = useQuery({
    queryKey: ['ai-management', 'config'],
    queryFn: () => aiApi.getConfig(),
    staleTime: 5 * 60 * 1000,
  });

  const loading = healthLoading || embLoading;

  if (loading) {
    return (
      <Spin tip="檢查 AI 服務狀態...">
        <div style={{ height: 200 }} />
      </Spin>
    );
  }

  const groqOk = health?.groq?.available ?? false;
  const ollamaOk = health?.ollama?.available ?? false;
  const pgvectorOk = embStats?.pgvector_enabled ?? false;
  const rateLimit = health?.rate_limit;

  const StatusIcon: React.FC<{ ok: boolean }> = ({ ok }) =>
    ok
      ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
      : <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;

  return (
    <div>
      {/* 服務健康卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={groqOk} />
              <div>
                <Typography.Text strong>Groq API</Typography.Text>
                <br />
                <Badge
                  status={groqOk ? 'success' : 'error'}
                  text={groqOk ? '正常運作' : '無法連線'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  {health?.groq?.message || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={ollamaOk} />
              <div>
                <Typography.Text strong>Ollama</Typography.Text>
                <br />
                <Badge
                  status={ollamaOk ? 'success' : 'error'}
                  text={ollamaOk ? '正常運作' : '無法連線'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  {health?.ollama?.message || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={pgvectorOk} />
              <div>
                <Typography.Text strong>pgvector</Typography.Text>
                <br />
                <Badge
                  status={pgvectorOk ? 'success' : 'warning'}
                  text={pgvectorOk ? '已啟用' : '未啟用'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  向量搜尋 {pgvectorOk ? '可用' : '不可用（語意搜尋降級為關鍵字模式）'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Rate Limit 監控 */}
      <Card title="Rate Limit 監控" size="small" style={{ marginBottom: 24 }}
        extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => refetchHealth()}>重新整理</Button>}
      >
        {rateLimit ? (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8}>
              <Statistic
                title="目前使用量"
                value={rateLimit.current_requests}
                suffix={`/ ${rateLimit.max_requests}`}
                valueStyle={{
                  color: rateLimit.current_requests / rateLimit.max_requests > 0.8
                    ? '#cf1322' : '#3f8600',
                }}
              />
            </Col>
            <Col xs={12} sm={8}>
              <Statistic
                title="使用率"
                value={(rateLimit.current_requests / rateLimit.max_requests * 100)}
                suffix="%"
                precision={1}
              />
            </Col>
            <Col xs={24} sm={8}>
              <Statistic
                title="時間窗口"
                value={rateLimit.window_seconds}
                suffix="秒"
              />
            </Col>
            <Col xs={24}>
              <Progress
                percent={Math.round(rateLimit.current_requests / rateLimit.max_requests * 100)}
                status={
                  rateLimit.current_requests / rateLimit.max_requests > 0.8 ? 'exception'
                    : rateLimit.current_requests / rateLimit.max_requests > 0.5 ? 'normal' : 'success'
                }
              />
            </Col>
          </Row>
        ) : (
          <Empty description="無 Rate Limit 資訊" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* Embedding 覆蓋率 */}
      <Card title="Embedding 覆蓋率" size="small" style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={8}>
            <Statistic title="已生成" value={embStats?.with_embedding ?? 0} suffix="筆" />
          </Col>
          <Col xs={8}>
            <Statistic title="未生成" value={embStats?.without_embedding ?? 0} suffix="筆" />
          </Col>
          <Col xs={8}>
            <Statistic
              title="覆蓋率"
              value={embStats?.coverage_percent ?? 0}
              suffix="%"
              precision={1}
            />
          </Col>
          <Col xs={24}>
            <Progress
              percent={embStats?.coverage_percent ?? 0}
              status={(embStats?.coverage_percent ?? 0) >= 80 ? 'success' : 'normal'}
              format={(p) => `${(p ?? 0).toFixed(1)}%`}
            />
          </Col>
        </Row>
      </Card>

      {/* 服務配置 */}
      {config && (
        <Card title="AI 服務配置" size="small">
          <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
            <Descriptions.Item label="AI 功能">
              <Badge status={config.enabled ? 'success' : 'error'} text={config.enabled ? '已啟用' : '已停用'} />
            </Descriptions.Item>
            <Descriptions.Item label="Groq 模型">
              {config.providers.groq.model}
            </Descriptions.Item>
            <Descriptions.Item label="Ollama 模型">
              {config.providers.ollama.model}
            </Descriptions.Item>
            <Descriptions.Item label="Ollama URL">
              {config.providers.ollama.url}
            </Descriptions.Item>
            <Descriptions.Item label="Rate Limit">
              {config.rate_limit.max_requests} 次 / {config.rate_limit.window_seconds} 秒
            </Descriptions.Item>
            <Descriptions.Item label="快取">
              {config.cache.enabled ? '已啟用' : '停用'} (摘要 {config.cache.ttl_summary}s / 分類 {config.cache.ttl_classify}s)
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
};
