import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Space,
  Table,
  Tag,
  Button,
  Alert,
  Divider,
  List,
  Avatar,
  Badge,
  Modal,
  message
} from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  SecurityScanOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  StopOutlined,
  SettingOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

import {
  USER_ROLES,
  USER_STATUSES,
  getRoleDisplayName,
  getStatusDisplayName,
  canRoleLogin,
  canStatusLogin
} from '../constants/permissions';

const { Title, Text } = Typography;

interface PendingUser {
  id: number;
  email: string;
  full_name: string;
  auth_provider: string;
  created_at: string;
  role: string;
  status: string;
}

interface SystemAlert {
  id: string;
  type: 'warning' | 'error' | 'info';
  title: string;
  description: string;
  timestamp: string;
  action?: () => void;
  actionText?: string;
}

const AdminDashboardPage: React.FC = () => {
  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([]);
  const [systemStats, setSystemStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    pendingUsers: 0,
    suspendedUsers: 0,
    unverifiedUsers: 0
  });
  const [systemAlerts, setSystemAlerts] = useState<SystemAlert[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // 載入真實數據
      const usersResponse = await fetch('/api/users/');
      const usersData = await usersResponse.json();

      // 篩選待驗證使用者
      const pendingUsersList = usersData.users?.filter((user: any) =>
        user.status === 'pending' || user.role === 'unverified'
      ) || [];

      // 計算統計數據
      const allUsers = usersData.users || [];
      const stats = {
        totalUsers: allUsers.length,
        activeUsers: allUsers.filter((u: any) => u.status === 'active').length,
        pendingUsers: pendingUsersList.length,
        suspendedUsers: allUsers.filter((u: any) => u.status === 'suspended').length,
        unverifiedUsers: allUsers.filter((u: any) => u.role === 'unverified').length
      };

      // 系統警告
      const alerts: SystemAlert[] = [];
      if (stats.pendingUsers > 0) {
        alerts.push({
          id: '1',
          type: 'warning',
          title: '待驗證使用者',
          description: `有 ${stats.pendingUsers} 個新使用者等待驗證`,
          timestamp: dayjs().subtract(10, 'minutes').toISOString(),
          action: () => window.location.href = '/admin/user-management',
          actionText: '立即處理'
        });
      }

      alerts.push({
        id: '2',
        type: 'info',
        title: '系統狀態',
        description: '所有核心服務運行正常',
        timestamp: dayjs().subtract(1, 'hour').toISOString()
      });

      setPendingUsers(pendingUsersList);
      setSystemStats(stats);
      setSystemAlerts(alerts);

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      message.error('載入數據失敗');
      setPendingUsers([]);
      setSystemStats({
        totalUsers: 0,
        activeUsers: 0,
        pendingUsers: 0,
        suspendedUsers: 0,
        unverifiedUsers: 0
      });
      setSystemAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveUser = async (userId: number) => {
    Modal.confirm({
      title: '確認驗證使用者',
      content: '確定要將此使用者驗證為一般使用者嗎？',
      onOk: async () => {
        try {
          const response = await fetch(`/api/users/${userId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              role: 'user',
              status: 'active'
            })
          });

          if (!response.ok) {
            throw new Error('Failed to approve user');
          }

          message.success('使用者已成功驗證');

          // 重新載入數據
          loadDashboardData();
        } catch (error) {
          console.error('Approve user failed:', error);
          message.error('驗證使用者失敗');
        }
      }
    });
  };

  const handleRejectUser = async (userId: number) => {
    Modal.confirm({
      title: '確認拒絕使用者',
      content: '確定要拒絕此使用者的註冊申請嗎？此操作將刪除該使用者帳戶。',
      okText: '確認拒絕',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          const response = await fetch(`/api/users/${userId}`, {
            method: 'DELETE'
          });

          if (!response.ok) {
            throw new Error('Failed to delete user');
          }

          message.success('已拒絕使用者申請');

          // 重新載入數據
          loadDashboardData();
        } catch (error) {
          console.error('Delete user failed:', error);
          message.error('拒絕使用者失敗');
        }
      }
    });
  };

  const pendingUsersColumns = [
    {
      title: '使用者',
      key: 'user',
      render: (_, record: PendingUser) => (
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
      render: (_, record: PendingUser) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CheckCircleOutlined />}
            onClick={() => handleApproveUser(record.id)}
          >
            通過
          </Button>
          <Button
            danger
            size="small"
            icon={<StopOutlined />}
            onClick={() => handleRejectUser(record.id)}
          >
            拒絕
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 頁面標題 */}
        <div>
          <Title level={2}>
            <SettingOutlined style={{ marginRight: 8 }} />
            管理員控制台
          </Title>
          <Text type="secondary">
            系統管理概覽和使用者權限管理中心
          </Text>
        </div>

        {/* 統計卡片 */}
        <Row gutter={16}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="總使用者數"
                value={systemStats.totalUsers}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="啟用使用者"
                value={systemStats.activeUsers}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="待驗證使用者"
                value={systemStats.pendingUsers}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="暫停使用者"
                value={systemStats.suspendedUsers}
                prefix={<StopOutlined />}
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 系統警告 */}
        {systemAlerts.length > 0 && (
          <Card title="系統通知" extra={<Badge count={systemAlerts.length} />}>
            <List
              dataSource={systemAlerts}
              renderItem={alert => (
                <List.Item
                  actions={[
                    alert.action && alert.actionText && (
                      <Button type="link" onClick={alert.action}>
                        {alert.actionText}
                      </Button>
                    )
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={
                      <Badge
                        status={
                          alert.type === 'error' ? 'error' : 
                          alert.type === 'warning' ? 'warning' : 'processing'
                        }
                      />
                    }
                    title={alert.title}
                    description={
                      <Space direction="vertical" size={0}>
                        <Text>{alert.description}</Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {dayjs(alert.timestamp).fromNow()}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* 待驗證使用者 */}
        {pendingUsers.length > 0 && (
          <Card
            title={
              <Space>
                <TeamOutlined />
                <span>待驗證使用者</span>
                <Badge count={pendingUsers.length} />
              </Space>
            }
            extra={
              <Button 
                type="primary" 
                href="/admin/user-management"
              >
                管理所有使用者
              </Button>
            }
          >
            <Alert
              message="新使用者需要驗證"
              description="以下使用者已註冊帳戶但需要管理者驗證後才能使用系統功能。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Table
              columns={pendingUsersColumns}
              dataSource={pendingUsers}
              rowKey="id"
              size="small"
              loading={loading}
              pagination={{ pageSize: 5 }}
            />
          </Card>
        )}

        {/* 快速操作面板 */}
        <Row gutter={16}>
          <Col xs={24} md={8}>
            <Card
              title="使用者管理"
              actions={[
                <Button type="link" href="/admin/user-management">
                  管理使用者
                </Button>
              ]}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>管理系統使用者、權限設定和帳戶狀態</Text>
                <div>
                  <Tag color="blue">權限配置</Tag>
                  <Tag color="green">帳戶驗證</Tag>
                  <Tag color="orange">狀態管理</Tag>
                </div>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card
              title="權限管理"
              actions={[
                <Button type="link" href="/admin/permissions">
                  權限設定
                </Button>
              ]}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>詳細的權限配置和角色管理</Text>
                <div>
                  <Tag color="purple">中英對照</Tag>
                  <Tag color="cyan">分類管理</Tag>
                  <Tag color="geekblue">批量操作</Tag>
                </div>
              </Space>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card
              title="系統設定"
              actions={[
                <Button type="link" href="/admin/system-settings">
                  系統設定
                </Button>
              ]}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>系統全域設定和安全配置</Text>
                <div>
                  <Tag color="red">安全設定</Tag>
                  <Tag color="yellow">系統配置</Tag>
                  <Tag color="lime">監控管理</Tag>
                </div>
              </Space>
            </Card>
          </Col>
        </Row>

        {/* 角色和狀態說明 */}
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Card title="系統角色說明">
              <List
                size="small"
                dataSource={Object.entries(USER_ROLES)}
                renderItem={([key, role]) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          status={role.can_login ? 'success' : 'error'}
                        />
                      }
                      title={role.name_zh}
                      description={
                        <Space direction="vertical" size={0}>
                          <Text type="secondary">{role.description_zh}</Text>
                          <Text type="secondary" style={{ fontSize: '11px' }}>
                            權限數量: {role.default_permissions.length}
                            {!role.can_login && ' • 無法登入'}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="使用者狀態說明">
              <List
                size="small"
                dataSource={Object.entries(USER_STATUSES)}
                renderItem={([key, status]) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          status={status.can_login ? 'success' : 'error'}
                        />
                      }
                      title={status.name_zh}
                      description={
                        <Space direction="vertical" size={0}>
                          <Text type="secondary">{status.description_zh}</Text>
                          {!status.can_login && (
                            <Text type="secondary" style={{ fontSize: '11px', color: '#f5222d' }}>
                              🚫 此狀態下無法登入系統
                            </Text>
                          )}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      </Space>
    </div>
  );
};

export default AdminDashboardPage;