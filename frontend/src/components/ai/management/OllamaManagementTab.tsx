/**
 * OllamaManagementTab - Ollama model management
 *
 * Extracted from AIAssistantManagementPage.tsx
 */
import React from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  List,
  message,
  Popconfirm,
  Row,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';

import { aiApi } from '../../../api/aiApi';
import type { OllamaEnsureModelsResponse, OllamaWarmupResponse } from '../../../types/ai';
import { StatusIcon } from './statusUtils';

/** 格式化位元組為人類可讀格式 */
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
};

export const OllamaManagementTab: React.FC = () => {
  const {
    data: status = null,
    isLoading: statusLoading,
    isError: statusError,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ['ai-management', 'ollama-status'],
    queryFn: () => aiApi.getOllamaStatus(),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });

  const ensureMutation = useMutation({
    mutationFn: () => aiApi.ensureOllamaModels(),
    onSuccess: (result: OllamaEnsureModelsResponse) => {
      if (!result.ollama_available) {
        message.error('Ollama 服務不可用，無法檢查模型');
        return;
      }
      const parts: string[] = [];
      if (result.pulled.length > 0) {
        parts.push(`成功拉取: ${result.pulled.join(', ')}`);
      }
      if (result.failed.length > 0) {
        parts.push(`拉取失敗: ${result.failed.join(', ')}`);
      }
      if (result.pulled.length === 0 && result.failed.length === 0) {
        parts.push('所有必要模型已安裝');
      }
      message.info(parts.join('；'));
      refetchStatus();
    },
    onError: () => {
      message.error('Ollama 模型檢查/拉取請求失敗');
    },
  });

  const warmupMutation = useMutation({
    mutationFn: () => aiApi.warmupOllamaModels(),
    onSuccess: (result: OllamaWarmupResponse) => {
      if (result.all_success) {
        message.success('所有模型預熱完成');
      } else {
        const failed = Object.entries(result.results)
          .filter(([, ok]) => !ok)
          .map(([name]) => name);
        message.warning(`部分模型預熱失敗: ${failed.join(', ')}`);
      }
      refetchStatus();
    },
    onError: () => {
      message.error('Ollama 模型預熱請求失敗');
    },
  });

  if (statusLoading) {
    return (
      <Spin tip="載入 Ollama 狀態...">
        <div style={{ height: 200 }} />
      </Spin>
    );
  }

  if (statusError) {
    return (
      <Alert
        type="error"
        showIcon
        message="Ollama 狀態取得失敗"
        description="無法連線至後端 API 取得 Ollama 狀態。請確認後端服務是否正常運行，且您具有管理員權限。"
        action={
          <Button size="small" icon={<ReloadOutlined />} onClick={() => refetchStatus()}>
            重新嘗試
          </Button>
        }
      />
    );
  }

  if (!status) {
    return <Empty description="無法取得 Ollama 狀態" />;
  }

  const ollamaOk = status.available;
  const groqOk = status.groq_available;
  const modelsReady = status.required_models_ready;
  const gpuModels = status.gpu_info?.loaded_models ?? [];

  return (
    <div>
      {/* 服務連線狀態 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <StatusIcon ok={ollamaOk} />
              <div>
                <Typography.Text strong>Ollama</Typography.Text>
                <br />
                <Badge
                  status={ollamaOk ? 'success' : 'error'}
                  text={ollamaOk ? '線上' : '離線'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  {status.message || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
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
                  {status.groq_message || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {modelsReady
                ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                : <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />
              }
              <div>
                <Typography.Text strong>必要模型</Typography.Text>
                <br />
                <Badge
                  status={modelsReady ? 'success' : 'warning'}
                  text={modelsReady ? '全部就緒' : '有缺少模型'}
                />
                <br />
                <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                  需求: {status.required_models.join(', ') || '-'}
                </Typography.Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 缺少模型警示 */}
      {status.missing_models.length > 0 && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="缺少必要模型"
          description={
            <span>
              以下模型尚未安裝：{' '}
              {status.missing_models.map((m) => (
                <Tag key={m} color="orange" style={{ marginBottom: 2 }}>{m}</Tag>
              ))}
              {' '}請使用下方「檢查並拉取模型」按鈕安裝。
            </span>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* 已安裝模型 */}
        <Col xs={24} sm={12}>
          <Card
            title={
              <span>
                <DatabaseOutlined style={{ marginRight: 8 }} />
                已安裝模型 ({status.models.length})
              </span>
            }
            size="small"
            extra={
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => refetchStatus()}
              >
                重新整理
              </Button>
            }
          >
            {status.models.length > 0 ? (
              <List
                size="small"
                dataSource={status.models}
                renderItem={(model) => {
                  const isRequired = status.required_models.some(
                    (req) => model === req || model.startsWith(req.split(':')[0] ?? req)
                  );
                  const isLoaded = gpuModels.some(
                    (gm) => gm.name === model || model.startsWith(gm.name.split(':')[0] ?? gm.name)
                  );
                  return (
                    <List.Item>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                        <Typography.Text
                          style={{ flex: 1, fontFamily: 'monospace', fontSize: 13 }}
                        >
                          {model}
                        </Typography.Text>
                        {isRequired && (
                          <Tooltip title="系統必要模型">
                            <Tag color="blue">必要</Tag>
                          </Tooltip>
                        )}
                        {isLoaded && (
                          <Tooltip title="已載入 GPU 記憶體">
                            <Tag color="green">GPU</Tag>
                          </Tooltip>
                        )}
                      </div>
                    </List.Item>
                  );
                }}
              />
            ) : (
              <Empty
                description={ollamaOk ? '無已安裝模型' : 'Ollama 離線'}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>

        {/* GPU 載入狀態 */}
        <Col xs={24} sm={12}>
          <Card
            title={
              <span>
                <ThunderboltOutlined style={{ marginRight: 8 }} />
                GPU 載入模型 ({gpuModels.length})
              </span>
            }
            size="small"
          >
            {gpuModels.length > 0 ? (
              <List
                size="small"
                dataSource={gpuModels}
                renderItem={(gm) => (
                  <List.Item>
                    <Descriptions size="small" column={1} style={{ width: '100%' }}>
                      <Descriptions.Item label="模型">
                        <Typography.Text style={{ fontFamily: 'monospace', fontSize: 13 }}>
                          {gm.name}
                        </Typography.Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="模型大小">
                        {formatBytes(gm.size)}
                      </Descriptions.Item>
                      <Descriptions.Item label="VRAM 使用">
                        <Typography.Text
                          type={gm.size_vram > 0 ? undefined : 'secondary'}
                          style={{ fontWeight: gm.size_vram > 0 ? 500 : 400 }}
                        >
                          {gm.size_vram > 0 ? formatBytes(gm.size_vram) : 'N/A'}
                        </Typography.Text>
                      </Descriptions.Item>
                    </Descriptions>
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                description={ollamaOk ? '目前無模型載入 GPU' : 'Ollama 離線'}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 管理動作 */}
      <Card
        title="管理動作"
        size="small"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              檢查系統必要模型是否已安裝，自動拉取缺少的模型。拉取大型模型可能需要數分鐘。
            </Typography.Text>
            <Popconfirm
              title="確定要檢查並拉取缺少的模型？此操作可能需要較長時間。"
              onConfirm={() => ensureMutation.mutate()}
              disabled={!ollamaOk}
            >
              <Button
                icon={<CloudServerOutlined />}
                loading={ensureMutation.isPending}
                disabled={!ollamaOk}
              >
                {ensureMutation.isPending ? '檢查中...' : '檢查並拉取模型'}
              </Button>
            </Popconfirm>
          </div>
          <div>
            <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              對每個必要模型發送最小請求，預載入 GPU 記憶體以消除冷啟動延遲。首次載入約需 1-2 分鐘。
            </Typography.Text>
            <Popconfirm
              title="確定要預熱所有必要模型？首次載入可能需要 1-2 分鐘。"
              onConfirm={() => warmupMutation.mutate()}
              disabled={!ollamaOk || !modelsReady}
            >
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={warmupMutation.isPending}
                disabled={!ollamaOk || !modelsReady}
              >
                {warmupMutation.isPending ? '預熱中...' : '預熱模型'}
              </Button>
            </Popconfirm>
            {!modelsReady && ollamaOk && (
              <Typography.Text type="warning" style={{ marginLeft: 12, fontSize: 12 }}>
                請先安裝所有必要模型
              </Typography.Text>
            )}
          </div>
        </Space>
      </Card>
    </div>
  );
};
