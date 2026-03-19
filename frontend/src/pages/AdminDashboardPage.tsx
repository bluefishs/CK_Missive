import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { logger } from '../services/logger';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { Typography, Space, Button, Divider, App } from 'antd';
import { SettingOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { documentsApi } from '../api/documentsApi';
import { SystemHealthDashboard, AIStatsPanel } from '../components/dashboard';
import { ROUTES } from '../router/types';
import type { PendingUser, SystemAlert } from '../types/api';
import {
  UserStatsCards,
  SystemAlertsCard,
  PendingUsersCard,
  QuickActionsPanel,
  DocumentStatsSection,
  RoleStatusReference,
} from './adminDashboard';
import type { UserStats } from './adminDashboard';

dayjs.extend(relativeTime);

const { Title, Text } = Typography;

const AdminDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { message: messageApi, modal } = App.useApp();
  const queryClient = useQueryClient();

  // React Query: fetch users data
  const {
    data: usersData,
    isLoading: usersLoading,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ['admin-dashboard', 'users'],
    queryFn: () => apiClient.post<{ users: PendingUser[] }>(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_LIST,
      { page: 1, per_page: 100 }
    ),
    staleTime: 5 * 60 * 1000,
  });

  // React Query: fetch document efficiency
  const {
    data: efficiency,
    refetch: refetchEfficiency,
  } = useQuery({
    queryKey: ['admin-dashboard', 'efficiency'],
    queryFn: () => documentsApi.getDocumentEfficiency(),
    staleTime: 5 * 60 * 1000,
  });

  // Derived state from users data
  const pendingUsers = useMemo(() => {
    const allUsers = usersData?.users || [];
    return allUsers.filter((user) =>
      user.status === 'pending' || user.role === 'unverified'
    );
  }, [usersData]);

  const systemStats: UserStats = useMemo(() => {
    const allUsers = usersData?.users || [];
    return {
      totalUsers: allUsers.length,
      activeUsers: allUsers.filter((u) => u.status === 'active').length,
      pendingUsers: allUsers.filter((u) => u.status === 'pending' || u.role === 'unverified').length,
      suspendedUsers: allUsers.filter((u) => u.status === 'suspended').length,
      unverifiedUsers: allUsers.filter((u) => u.role === 'unverified').length,
    };
  }, [usersData]);

  const systemAlerts = useMemo(() => {
    const alerts: SystemAlert[] = [];
    if (systemStats.pendingUsers > 0) {
      alerts.push({
        id: '1',
        type: 'warning',
        title: '待驗證使用者',
        description: `有 ${systemStats.pendingUsers} 個新使用者等待驗證`,
        timestamp: dayjs().subtract(10, 'minutes').toISOString(),
        action: () => navigate(ROUTES.USER_MANAGEMENT),
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
    return alerts;
  }, [systemStats.pendingUsers, navigate]);

  const loading = usersLoading;

  const loadDashboardData = () => {
    refetchUsers();
    refetchEfficiency();
  };

  // Mutation: approve user
  const approveMutation = useMutation({
    mutationFn: (userId: number) => apiClient.post(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_UPDATE(userId),
      { role: 'user', status: 'active' }
    ),
    onSuccess: () => {
      messageApi.success('使用者已成功驗證');
      queryClient.invalidateQueries({ queryKey: ['admin-dashboard', 'users'] });
    },
    onError: (error) => {
      logger.error('Approve user failed:', error);
      messageApi.error('驗證使用者失敗');
    },
  });

  // Mutation: reject user
  const rejectMutation = useMutation({
    mutationFn: (userId: number) => apiClient.post(
      API_ENDPOINTS.ADMIN_USER_MANAGEMENT.USERS_DELETE(userId),
      {}
    ),
    onSuccess: () => {
      messageApi.success('已拒絕使用者申請');
      queryClient.invalidateQueries({ queryKey: ['admin-dashboard', 'users'] });
    },
    onError: (error) => {
      logger.error('Delete user failed:', error);
      messageApi.error('拒絕使用者失敗');
    },
  });

  const handleApproveUser = (userId: number) => {
    modal.confirm({
      title: '確認驗證使用者',
      content: '確定要將此使用者驗證為一般使用者嗎？',
      onOk: () => approveMutation.mutateAsync(userId),
    });
  };

  const handleRejectUser = (userId: number) => {
    modal.confirm({
      title: '確認拒絕使用者',
      content: '確定要拒絕此使用者的註冊申請嗎？此操作將刪除該使用者帳戶。',
      okText: '確認拒絕',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => rejectMutation.mutateAsync(userId),
    });
  };

  const quickActions = useMemo(() => [
    {
      title: '使用者管理',
      description: '管理系統使用者、權限設定和帳戶狀態',
      tags: [
        { label: '權限配置', color: 'blue' },
        { label: '帳戶驗證', color: 'green' },
        { label: '狀態管理', color: 'orange' },
      ],
      buttonLabel: '管理使用者',
      buttonKey: 'manage-users',
      onNavigate: () => navigate(ROUTES.USER_MANAGEMENT),
    },
    {
      title: '權限管理',
      description: '詳細的權限配置和角色管理',
      tags: [
        { label: '中英對照', color: 'purple' },
        { label: '分類管理', color: 'cyan' },
        { label: '批量操作', color: 'geekblue' },
      ],
      buttonLabel: '權限設定',
      buttonKey: 'permission-settings',
      onNavigate: () => navigate(ROUTES.PERMISSION_MANAGEMENT),
    },
    {
      title: '備份與部署',
      description: '資料庫備份、附件備份與系統部署管理',
      tags: [
        { label: '備份管理', color: 'red' },
        { label: '排程設定', color: 'orange' },
        { label: '部署控制', color: 'lime' },
      ],
      buttonLabel: '備份管理',
      buttonKey: 'backup-management',
      onNavigate: () => navigate(ROUTES.BACKUP_MANAGEMENT),
    },
  ], [navigate]);

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space vertical style={{ width: '100%' }} size="large">
        {/* Page header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2} style={{ marginBottom: 4 }}>
              <SettingOutlined style={{ marginRight: 8 }} />
              管理員控制台
            </Title>
            <Text type="secondary">
              系統管理概覽和使用者權限管理中心
            </Text>
          </div>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadDashboardData}
            loading={loading}
          >
            重新整理
          </Button>
        </div>

        <UserStatsCards stats={systemStats} />
        <SystemAlertsCard alerts={systemAlerts} />
        <PendingUsersCard
          pendingUsers={pendingUsers}
          loading={loading}
          onNavigateToUsers={() => navigate(ROUTES.USER_MANAGEMENT)}
          onApprove={handleApproveUser}
          onReject={handleRejectUser}
        />
        <QuickActionsPanel actions={quickActions} />
        <DocumentStatsSection efficiency={efficiency} />

        {/* System monitoring */}
        <Divider />
        <Title level={4}>系統監控</Title>
        <SystemHealthDashboard />
        <div style={{ marginTop: 16 }}>
          <AIStatsPanel />
        </div>

        <RoleStatusReference />
      </Space>
    </ResponsiveContent>
  );
};

export default AdminDashboardPage;
