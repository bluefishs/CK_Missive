import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import {
  OrderedListOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  RocketOutlined,
} from '@ant-design/icons';

export interface WorkflowStats {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
  incomingDocs: number;
  outgoingDocs: number;
  currentStage: string;
}

interface WorkflowStatsCardProps {
  stats: WorkflowStats;
}

export const WorkflowStatsCard: React.FC<WorkflowStatsCardProps> = ({ stats }) => {
  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Row gutter={[16, 8]}>
        <Col xs={12} sm={8} md={4}>
          <Statistic
            title="總紀錄數"
            value={stats.total}
            prefix={<OrderedListOutlined />}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic
            title="已完成"
            value={stats.completed}
            styles={{ content: { color: '#52c41a' } }}
            prefix={<CheckCircleOutlined />}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic
            title="進行中"
            value={stats.inProgress}
            styles={{ content: { color: '#1890ff' } }}
            prefix={<ClockCircleOutlined />}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic title="關聯來文" value={stats.incomingDocs} prefix={<FileTextOutlined />} />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Statistic
            title="當前階段"
            value={stats.currentStage}
            prefix={<RocketOutlined />}
            styles={{ content: { fontSize: 16 } }}
          />
        </Col>
      </Row>
    </Card>
  );
};
