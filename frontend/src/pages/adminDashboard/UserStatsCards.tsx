import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import {
  UserOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';

export interface UserStats {
  totalUsers: number;
  activeUsers: number;
  pendingUsers: number;
  suspendedUsers: number;
  unverifiedUsers: number;
}

interface UserStatsCardsProps {
  stats: UserStats;
}

const UserStatsCards: React.FC<UserStatsCardsProps> = ({ stats }) => (
  <Row gutter={16}>
    <Col xs={24} sm={12} lg={6}>
      <Card>
        <Statistic
          title="總使用者數"
          value={stats.totalUsers}
          prefix={<UserOutlined />}
          styles={{ content: { color: '#1890ff' } }}
        />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={6}>
      <Card>
        <Statistic
          title="啟用使用者"
          value={stats.activeUsers}
          prefix={<CheckCircleOutlined />}
          styles={{ content: { color: '#52c41a' } }}
        />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={6}>
      <Card>
        <Statistic
          title="待驗證使用者"
          value={stats.pendingUsers}
          prefix={<ClockCircleOutlined />}
          styles={{ content: { color: '#faad14' } }}
        />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={6}>
      <Card>
        <Statistic
          title="暫停使用者"
          value={stats.suspendedUsers}
          prefix={<StopOutlined />}
          styles={{ content: { color: '#f5222d' } }}
        />
      </Card>
    </Col>
  </Row>
);

export default UserStatsCards;
