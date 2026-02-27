/**
 * ServiceMonitorTab - AI service health monitoring
 *
 * 顯示 pgvector 狀態、Rate Limit 監控、AI 服務配置。
 * Groq/Ollama 連線狀態已移至 OllamaManagementTab（更詳細），
 * Embedding 覆蓋率已移至 EmbeddingTab（含批次操作）。
 *
 * @version 2.0.0
 * @updated 2026-02-27 — 移除與 OllamaManagementTab / EmbeddingTab 重複區塊
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
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

import { aiApi } from '../../../api/aiApi';
import { StatusIcon } from './statusUtils';

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

  const pgvectorOk = embStats?.pgvector_enabled ?? false;
  const rateLimit = health?.rate_limit;

  return (
    <div>
      {/* pgvector 狀態 */}
      <Card size="small" style={{ marginBottom: 24 }}>
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
