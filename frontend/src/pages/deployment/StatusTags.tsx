import React from 'react';
import { Tag } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ServiceStatus, DeploymentStatus } from '../../api/deploymentApi';

export const ServiceStatusTag: React.FC<{ status: ServiceStatus }> = ({ status }) => {
  const config: Record<ServiceStatus, { color: string; icon: React.ReactNode; text: string }> = {
    running: { color: 'success', icon: <CheckCircleOutlined />, text: '運行中' },
    stopped: { color: 'default', icon: <CloseCircleOutlined />, text: '已停止' },
    error: { color: 'error', icon: <ExclamationCircleOutlined />, text: '異常' },
    unknown: { color: 'warning', icon: <ClockCircleOutlined />, text: '未知' },
  };

  const cfg = config[status] || config.unknown;
  return (
    <Tag color={cfg.color} icon={cfg.icon}>
      {cfg.text}
    </Tag>
  );
};

export const DeploymentStatusTag: React.FC<{ status: DeploymentStatus; conclusion?: string }> = ({
  status,
  conclusion,
}) => {
  const defaultConfig = { color: 'warning', icon: <ClockCircleOutlined />, text: '等待中' };
  const config: Record<DeploymentStatus, { color: string; icon: React.ReactNode; text: string }> = {
    success: { color: 'success', icon: <CheckCircleOutlined />, text: '成功' },
    failure: { color: 'error', icon: <CloseCircleOutlined />, text: '失敗' },
    in_progress: { color: 'processing', icon: <SyncOutlined spin />, text: '進行中' },
    cancelled: { color: 'default', icon: <CloseCircleOutlined />, text: '已取消' },
    pending: defaultConfig,
  };

  const key: DeploymentStatus = status === 'success' && conclusion === 'failure' ? 'failure' : status;
  const { color, icon, text } = config[key] || defaultConfig;
  return (
    <Tag color={color} icon={icon}>
      {text}
    </Tag>
  );
};
