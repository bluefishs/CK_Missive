import React from 'react';
import { Card, Row, Col, Statistic, Descriptions, Space, Tag } from 'antd';
import {
  CloudServerOutlined,
  DesktopOutlined,
  DatabaseOutlined,
  BranchesOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { ServiceStatusTag } from './StatusTags';
import type { ServiceStatus } from '../../api/deploymentApi';

interface ServiceInfo {
  name: string;
  status: ServiceStatus;
  version?: string;
}

interface SystemStatusData {
  overall_status: ServiceStatus;
  current_version?: string;
  last_deployment?: string;
  environment?: string;
  services: ServiceInfo[];
}

interface SystemStatusCardProps {
  systemStatus: SystemStatusData | null;
  loading: boolean;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  systemStatus,
  loading,
}) => {
  return (
    <Card title={<><CloudServerOutlined /> 系統狀態</>} loading={loading}>
      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="整體狀態"
            valueRender={() => (
              <ServiceStatusTag status={systemStatus?.overall_status || 'unknown'} />
            )}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="當前版本"
            value={systemStatus?.current_version || '未知'}
            prefix={<BranchesOutlined />}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="最後部署"
            value={
              systemStatus?.last_deployment
                ? dayjs(systemStatus.last_deployment).fromNow()
                : '未知'
            }
            prefix={<ClockCircleOutlined />}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="環境"
            value={systemStatus?.environment || 'production'}
            prefix={<DesktopOutlined />}
          />
        </Col>
      </Row>

      <Descriptions
        title="服務詳情"
        style={{ marginTop: 24 }}
        bordered
        size="small"
        column={{ xs: 1, sm: 2, md: 3 }}
        items={systemStatus?.services.map((service) => ({
          key: service.name,
          label: (
            <Space>
              {service.name === 'Backend API' && <CloudServerOutlined />}
              {service.name === 'Frontend' && <DesktopOutlined />}
              {service.name === 'PostgreSQL' && <DatabaseOutlined />}
              {service.name}
            </Space>
          ),
          children: (
            <Space>
              <ServiceStatusTag status={service.status} />
              {service.version && <Tag>{service.version}</Tag>}
            </Space>
          ),
        })) ?? []}
      />
    </Card>
  );
};
