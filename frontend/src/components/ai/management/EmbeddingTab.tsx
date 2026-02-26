/**
 * EmbeddingTab - Embedding management
 *
 * Extracted from AIAssistantManagementPage.tsx
 */
import React, { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  InputNumber,
  message,
  Popconfirm,
  Progress,
  Row,
  Space,
  Spin,
  Statistic,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { aiApi } from '../../../api/aiApi';
import type { EmbeddingBatchResponse } from '../../../types/ai';

export const EmbeddingTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [batchLimit, setBatchLimit] = useState<number>(100);

  const {
    data: embStats = null,
    isLoading: statsLoading,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['ai-management', 'embedding-stats'],
    queryFn: () => aiApi.getEmbeddingStats(),
    staleTime: 60 * 1000,
  });

  const batchMutation = useMutation({
    mutationFn: () => aiApi.runEmbeddingBatch({ limit: batchLimit }),
    onSuccess: (result: EmbeddingBatchResponse | null) => {
      if (result?.success) {
        message.success(
          `批次完成：成功 ${result.success_count} 筆、跳過 ${result.skip_count} 筆、` +
          `失敗 ${result.error_count} 筆（耗時 ${result.elapsed_seconds.toFixed(1)}s）`
        );
        refetchStats();
        queryClient.invalidateQueries({ queryKey: ['ai-management', 'embedding-stats'] });
      } else {
        message.error(result?.message || 'Embedding 批次執行失敗');
      }
    },
    onError: () => {
      message.error('Embedding 批次執行失敗');
    },
  });

  if (statsLoading) {
    return (
      <Spin tip="載入 Embedding 統計...">
        <div style={{ height: 200 }} />
      </Spin>
    );
  }

  const pgvectorEnabled = embStats?.pgvector_enabled ?? false;

  return (
    <div>
      {!pgvectorEnabled && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="pgvector 未啟用"
          description="Embedding 功能需要啟用 pgvector 擴展 (PGVECTOR_ENABLED=true) 及 Ollama 服務。"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 覆蓋率統計 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="公文總數"
              value={embStats?.total_documents ?? 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已生成 Embedding"
              value={embStats?.with_embedding ?? 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="未生成 Embedding"
              value={embStats?.without_embedding ?? 0}
              valueStyle={{ color: embStats?.without_embedding ? '#cf1322' : '#3f8600' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="覆蓋率"
              value={embStats?.coverage_percent ?? 0}
              suffix="%"
              precision={1}
              prefix={<DashboardOutlined />}
              valueStyle={{
                color: (embStats?.coverage_percent ?? 0) >= 80 ? '#3f8600'
                  : (embStats?.coverage_percent ?? 0) >= 50 ? '#d48806' : '#cf1322',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 覆蓋率進度條 */}
      <Card size="small" style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 8 }}>
          <Typography.Text strong>Embedding 覆蓋率</Typography.Text>
        </div>
        <Progress
          percent={embStats?.coverage_percent ?? 0}
          status={
            (embStats?.coverage_percent ?? 0) >= 80 ? 'success'
              : (embStats?.coverage_percent ?? 0) >= 50 ? 'normal' : 'exception'
          }
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {embStats?.with_embedding ?? 0} / {embStats?.total_documents ?? 0} 筆公文已生成向量
        </Typography.Text>
      </Card>

      {/* 批次處理 */}
      <Card
        title="手動批次生成 Embedding"
        size="small"
        extra={
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => refetchStats()}
          >
            重新整理
          </Button>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Typography.Text>每批處理筆數：</Typography.Text>
            <InputNumber
              min={10}
              max={500}
              step={10}
              value={batchLimit}
              onChange={(v) => setBatchLimit(v || 100)}
              style={{ marginLeft: 8, width: 120 }}
              disabled={!pgvectorEnabled}
            />
          </div>
          <Popconfirm
            title={`確定要執行 Embedding 批次處理？將處理最多 ${batchLimit} 筆公文。`}
            onConfirm={() => batchMutation.mutate()}
            disabled={!pgvectorEnabled}
          >
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={batchMutation.isPending}
              disabled={!pgvectorEnabled || (embStats?.without_embedding ?? 0) === 0}
            >
              {batchMutation.isPending ? '執行中...' : '開始批次處理'}
            </Button>
          </Popconfirm>
          {(embStats?.without_embedding ?? 0) === 0 && pgvectorEnabled && (
            <Alert type="success" message="所有公文皆已生成 Embedding" showIcon />
          )}
        </Space>
      </Card>
    </div>
  );
};
