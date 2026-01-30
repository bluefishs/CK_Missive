/**
 * 權限管理頁面
 *
 * 功能：
 * - 顯示使用者權限列表（使用真實 API）
 * - 提供權限分類摘要視圖
 * - 支援詳細權限編輯（使用 PermissionManager 元件）
 *
 * @version 3.1.0 - 恢復原設計並整合真實 API
 * @date 2026-01-26
 */
import React, { useState, useMemo } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Alert,
  Row,
  Col,
  Select,
  Input,
  Table,
  Modal,
  Spin,
  App
} from 'antd';
import {
  SecurityScanOutlined,
  UserOutlined,
  EditOutlined,
  SearchOutlined,
  TeamOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import PermissionManager from '../components/admin/PermissionManager';
import {
  PERMISSION_CATEGORIES,
  groupPermissionsByCategory
} from '../constants/permissions';
import { adminUsersApi } from '../api/adminUsersApi';
import { ROUTES } from '../router/types';
import type { User, UserPermissions } from '../types/api';

const { Title, Text } = Typography;
const { Option } = Select;

const PermissionManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');

  // 從 API 載入使用者列表
  const { data: usersData, isLoading } = useQuery({
    queryKey: ['adminUsers', { page: 1, per_page: 100 }],
    queryFn: () => adminUsersApi.getUsers({ page: 1, per_page: 100 }),
  });

  const users = usersData?.items || [];

  // 載入選中使用者的權限
  const { data: userPermissions, isLoading: permissionsLoading } = useQuery({
    queryKey: ['userPermissions', selectedUser?.id],
    queryFn: () => adminUsersApi.getUserPermissions(selectedUser!.id),
    enabled: !!selectedUser?.id && modalVisible,
  });

  // 更新權限 mutation
  const updatePermissionsMutation = useMutation({
    mutationFn: (data: { userId: number; permissions: UserPermissions }) =>
      adminUsersApi.updateUserPermissions(data.userId, data.permissions),
    onSuccess: () => {
      message.success(`已更新 ${selectedUser?.full_name || selectedUser?.username} 的權限`);
      queryClient.invalidateQueries({ queryKey: ['userPermissions', selectedUser?.id] });
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
    onError: (error: Error) => {
      const detail = (error as any)?.response?.data?.detail;
      message.error(detail || error.message || '權限更新失敗');
    },
  });

  const handleEditPermissions = (user: User) => {
    setSelectedUser(user);
    setModalVisible(true);
  };

  const handlePermissionUpdate = (permissions: string[]) => {
    if (!selectedUser) return;

    updatePermissionsMutation.mutate({
      userId: selectedUser.id,
      permissions: {
        user_id: selectedUser.id,
        role: selectedUser.role || 'user',
        permissions,
      },
    });
  };

  const handleSaveAndClose = () => {
    setModalVisible(false);
    setSelectedUser(null);
  };

  const filteredUsers = useMemo(() => {
    return users.filter((user: User) => {
      const matchesSearch = !searchText ||
        (user.full_name && user.full_name.toLowerCase().includes(searchText.toLowerCase())) ||
        user.email.toLowerCase().includes(searchText.toLowerCase()) ||
        user.username.toLowerCase().includes(searchText.toLowerCase());

      const matchesRole = !roleFilter || user.role === roleFilter;

      return matchesSearch && matchesRole;
    });
  }, [users, searchText, roleFilter]);

  const getPermissionSummary = (user: User) => {
    // 從 user.permissions 解析權限數量
    let permissionCount = 0;
    let categoryCount = 0;

    if (user.permissions) {
      try {
        const perms = typeof user.permissions === 'string'
          ? JSON.parse(user.permissions)
          : user.permissions;

        if (Array.isArray(perms)) {
          permissionCount = perms.length;
          const grouped = groupPermissionsByCategory(perms);
          categoryCount = Object.keys(grouped).length;
        }
      } catch {
        // 忽略解析錯誤
      }
    }

    const totalCategories = Object.keys(PERMISSION_CATEGORIES).length;
    return `${permissionCount} 個權限 (${categoryCount}/${totalCategories} 個分類)`;
  };

  const getRoleDisplayName = (role: string) => {
    const roleNames: Record<string, string> = {
      superuser: '超級管理員',
      admin: '管理員',
      user: '一般使用者',
      guest: '訪客',
    };
    return roleNames[role] || role;
  };

  const columns: ColumnsType<User> = [
    {
      title: '使用者',
      key: 'user',
      render: (_, record) => (
        <Space>
          <UserOutlined style={{ fontSize: '16px', color: '#1976d2' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.full_name || record.username}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.email}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => getRoleDisplayName(role),
    },
    {
      title: '權限摘要',
      key: 'permissions',
      render: (_, record) => (
        <Text>{getPermissionSummary(record)}</Text>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <span style={{
          color: isActive ? '#52c41a' : '#ff4d4f',
          fontWeight: 500
        }}>
          {isActive ? '啟用' : '停用'}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleEditPermissions(record)}
        >
          管理權限
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" tip="載入使用者資料中..." />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <SecurityScanOutlined style={{ marginRight: '8px' }} />
                權限管理中心
              </Title>
              <Text type="secondary">
                管理系統使用者的詳細權限設定
              </Text>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<TeamOutlined />}
                onClick={() => navigate(ROUTES.USER_MANAGEMENT)}
              >
                使用者管理
              </Button>
            </Col>
          </Row>
        </div>

        <Alert
          message="權限管理說明"
          description="此頁面提供完整的權限管理功能，包含分類管理、批量操作等功能。點擊「管理權限」按鈕可以詳細設定各使用者的權限。"
          type="info"
          showIcon
          style={{ marginBottom: '24px' }}
        />

        <Row gutter={16} style={{ marginBottom: '16px' }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Input
              placeholder="搜尋使用者"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Select
              placeholder="角色篩選"
              allowClear
              value={roleFilter || undefined}
              onChange={setRoleFilter}
              style={{ width: '100%' }}
            >
              <Option value="superuser">{getRoleDisplayName('superuser')}</Option>
              <Option value="admin">{getRoleDisplayName('admin')}</Option>
              <Option value="user">{getRoleDisplayName('user')}</Option>
            </Select>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredUsers}
          loading={isLoading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
          }}
        />

        {/* 權限詳細分類摘要 */}
        <div style={{ marginTop: '24px' }}>
          <Title level={4}>權限分類說明</Title>
          <Row gutter={[16, 16]}>
            {Object.entries(PERMISSION_CATEGORIES).map(([key, category]) => (
              <Col xs={24} sm={12} lg={8} key={key}>
                <Card size="small" style={{ height: '100%' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>{category.name_zh}</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {category.permissions.length} 個權限項目
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </Card>

      {/* 權限管理 Modal */}
      <Modal
        title={
          <Space>
            <SecurityScanOutlined />
            詳細權限設定
            {selectedUser && (
              <Text type="secondary">
                - {selectedUser.full_name || selectedUser.username}
              </Text>
            )}
          </Space>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setSelectedUser(null);
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setModalVisible(false);
            setSelectedUser(null);
          }}>
            取消
          </Button>,
          <Button
            key="save"
            type="primary"
            onClick={handleSaveAndClose}
            loading={updatePermissionsMutation.isPending}
            disabled={updatePermissionsMutation.isPending}
          >
            完成
          </Button>
        ]}
        width={1000}
        style={{ top: '20px' }}
      >
        {permissionsLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="載入權限資料..." />
          </div>
        ) : selectedUser && (
          <PermissionManager
            userPermissions={userPermissions?.permissions || []}
            onPermissionChange={handlePermissionUpdate}
            readOnly={false}
          />
        )}
      </Modal>
    </div>
  );
};

export default PermissionManagementPage;
