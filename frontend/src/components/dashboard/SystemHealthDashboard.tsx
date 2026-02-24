/**
 * 系統健康度儀表板元件
 *
 * 從 /health/summary API 取得系統健康狀態，
 * 以四張統計卡片呈現服務狀態、記憶體使用率、資料庫連線數、系統版本。
 * 每 30 秒自動刷新。
 *
 * @version 1.0.0
 * @date 2026-02-07
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Spin,
  Alert,
  Space,
  Typography,
  Button,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { SYSTEM_ENDPOINTS } from '../../api/endpoints';
import { useResponsive } from '../../hooks';
import { logger } from '../../services/logger';

const { Text } = Typography;

/** 自動刷新間隔 (毫秒) */
const REFRESH_INTERVAL_MS = 30_000;

/** 健康摘要 API 回應型別 */
interface HealthSummaryResponse {
  timestamp: string;
  uptime: string;
  overall_status: 'healthy' | 'degraded' | 'unhealthy';
  components: {
    database?: {
      status: string;
      response_ms?: number;
    };
    connection_pool?: {
      status: string;
      active?: number;
    };
    background_tasks?: {
      status: string;
      total?: number;
      failed?: number;
    };
    system?: {
      status: string;
      memory_percent?: number;
      cpu_percent?: number;
    };
  };
  issues?: string[];
}

/** 將 overall_status 映射到 Tag 顯示顏色 */
function getStatusTagColor(status: string): string {
  switch (status) {
    case 'healthy':
      return 'green';
    case 'degraded':
      return 'orange';
    case 'unhealthy':
    default:
      return 'red';
  }
}

/** 將 overall_status 映射到中文標籤 */
function getStatusLabel(status: string): string {
  switch (status) {
    case 'healthy':
      return '正常';
    case 'degraded':
      return '警告';
    case 'unhealthy':
      return '異常';
    default:
      return '未知';
  }
}

/** 根據記憶體百分比決定 Progress 顏色 */
function getMemoryStrokeColor(percent: number): string {
  if (percent >= 90) return '#f5222d';
  if (percent >= 70) return '#faad14';
  return '#52c41a';
}

export const SystemHealthDashboard: React.FC = () => {
  const { isMobile } = useResponsive();
  const [healthData, setHealthData] = useState<HealthSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchHealthSummary = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }
    try {
      const data = await apiClient.get<HealthSummaryResponse>(
        SYSTEM_ENDPOINTS.HEALTH_SUMMARY
      );
      setHealthData(data);
      setError(null);
    } catch (err) {
      logger.error('Failed to fetch health summary:', err);
      // 規範: catch 中不清空已有資料，只記錄錯誤
      setError('無法取得系統健康狀態，請確認您有管理員權限。');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealthSummary(true);

    intervalRef.current = setInterval(() => {
      fetchHealthSummary(false);
    }, REFRESH_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchHealthSummary]);

  const handleManualRefresh = () => {
    fetchHealthSummary(true);
  };

  // --- 衍生數據 ---
  const overallStatus = healthData?.overall_status ?? 'unhealthy';
  const memoryPercent = healthData?.components?.system?.memory_percent ?? 0;
  const dbActive = healthData?.components?.connection_pool?.active ?? 0;
  const cpuPercent = healthData?.components?.system?.cpu_percent ?? 0;
  const uptime = healthData?.uptime ?? '--';

  const statusIcon =
    overallStatus === 'healthy' ? (
      <CheckCircleOutlined style={{ color: '#52c41a' }} />
    ) : (
      <CloseCircleOutlined
        style={{ color: overallStatus === 'degraded' ? '#faad14' : '#f5222d' }}
      />
    );

  // --- 渲染 ---
  if (loading && !healthData) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin tip="載入系統健康狀態..."><div /></Spin>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <CloudServerOutlined />
          <span>系統健康狀態</span>
          {loading && <Spin size="small" />}
        </Space>
      }
      extra={
        <Button
          type="text"
          icon={<ReloadOutlined spin={loading} />}
          onClick={handleManualRefresh}
          disabled={loading}
          size="small"
          aria-label={isMobile ? '重新整理' : undefined}
        >
          {!isMobile && '重新整理'}
        </Button>
      }
    >
      {error && !healthData && (
        <Alert
          message="載入失敗"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {error && healthData && (
        <Alert
          message="刷新失敗，顯示上次資料"
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]}>
        {/* 卡片 1: 服務狀態 */}
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card size="small" hoverable>
            <Statistic
              title="服務狀態"
              value={getStatusLabel(overallStatus)}
              valueRender={() => (
                <Space>
                  {statusIcon}
                  <Tag color={getStatusTagColor(overallStatus)}>
                    {getStatusLabel(overallStatus)}
                  </Tag>
                </Space>
              )}
            />
            {healthData?.issues && healthData.issues.length > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                異常項目: {healthData.issues.join(', ')}
              </Text>
            )}
          </Card>
        </Col>

        {/* 卡片 2: 記憶體使用率 */}
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card size="small" hoverable>
            <Statistic
              title="記憶體使用率"
              value={memoryPercent}
              suffix="%"
              valueStyle={{
                color: memoryPercent >= 90 ? '#f5222d' : memoryPercent >= 70 ? '#faad14' : '#52c41a',
              }}
            />
            <Progress
              percent={memoryPercent}
              size="small"
              showInfo={false}
              strokeColor={getMemoryStrokeColor(memoryPercent)}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>

        {/* 卡片 3: 資料庫連線數 */}
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card size="small" hoverable>
            <Statistic
              title="資料庫活躍連線"
              value={dbActive}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              回應:{' '}
              {healthData?.components?.database?.response_ms != null
                ? `${healthData.components.database.response_ms} ms`
                : '--'}
            </Text>
          </Card>
        </Col>

        {/* 卡片 4: 系統運行時間 */}
        <Col xs={24} sm={12} md={12} lg={6}>
          <Card size="small" hoverable>
            <Statistic
              title="系統運行時間"
              value={uptime}
              prefix={<CloudServerOutlined />}
              valueStyle={{ fontSize: 18, color: '#722ed1' }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              CPU: {cpuPercent}%
            </Text>
          </Card>
        </Col>
      </Row>
    </Card>
  );
};

export default SystemHealthDashboard;
