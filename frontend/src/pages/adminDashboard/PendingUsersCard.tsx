import React from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Alert,
  Space,
  Badge,
  Avatar,
  Typography,
} from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { PendingUser } from '../../types/api';

const { Text } = Typography;

interface PendingUsersCardProps {
  pendingUsers: PendingUser[];
  loading: boolean;
  onNavigateToUsers: () => void;
  onApprove: (userId: number) => void;
  onReject: (userId: number) => void;
}

const PendingUsersCard: React.FC<PendingUsersCardProps> = ({
  pendingUsers,
  loading,
  onNavigateToUsers,
  onApprove,
  onReject,
}) => {
  if (pendingUsers.length === 0) return null;

  const columns = [
    {
      title: '使用者',
      key: 'user',
      render: (_: unknown, record: PendingUser) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.full_name}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.email}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '註冊方式',
      dataIndex: 'auth_provider',
      key: 'auth_provider',
      render: (provider: string) => (
        <Tag color={provider === 'google' ? 'blue' : 'green'}>
          {provider === 'google' ? 'Google' : '電子郵件'}
        </Tag>
      ),
    },
    {
      title: '註冊時間',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: PendingUser) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CheckCircleOutlined />}
            onClick={() => onApprove(record.id)}
          >
            通過
          </Button>
          <Button
            danger
            size="small"
            icon={<StopOutlined />}
            onClick={() => onReject(record.id)}
          >
            拒絕
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>待驗證使用者</span>
          <Badge count={pendingUsers.length} />
        </Space>
      }
      extra={
        <Button type="primary" onClick={onNavigateToUsers}>
          管理所有使用者
        </Button>
      }
    >
      <Alert
        title="新使用者需要驗證"
        description="以下使用者已註冊帳戶但需要管理者驗證後才能使用系統功能。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Table
        columns={columns}
        dataSource={pendingUsers}
        rowKey="id"
        size="small"
        loading={loading}
        pagination={{ pageSize: 5 }}
        scroll={{ x: 600 }}
      />
    </Card>
  );
};

export default PendingUsersCard;
