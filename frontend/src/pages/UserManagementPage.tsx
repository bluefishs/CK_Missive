/**
 * 使用者權限管理頁面
 * @description 提供使用者帳號、角色與權限的管理功能
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card, Table, Button, Space, Input, Select, App, Row, Col, Typography,
  Modal, AutoComplete
} from 'antd';
import type { TableProps } from 'antd';
import type { SorterResult } from 'antd/es/table/interface';
import debounce from 'lodash/debounce';
import {
  PlusOutlined, SearchOutlined, TeamOutlined,
  DeleteOutlined, StopOutlined, CheckOutlined
} from '@ant-design/icons';
import axios from 'axios';
import authService, { type UserInfo } from '../services/authService';
import { logger } from '../utils/logger';
import {
  getRoleDisplayName,
  getStatusDisplayName,
  getRoleDefaultPermissions
} from '../constants/permissions';
import { createUserTableColumns } from '../config/userTableColumns';
import UserEditModal from '../components/admin/UserEditModal';
import UserPermissionModal from '../components/admin/UserPermissionModal';
import type { User, Permission, UserPermissions, UserPagination } from '../types/user';

// API 配置
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001') + '/api';

// 創建配置好的 axios 實例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// 添加請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    const token = authService.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

const { Title } = Typography;
const { Option } = Select;

const UserManagementPage: React.FC = () => {
  const { message } = App.useApp();

  // 使用者列表狀態
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentLoggedInUser, setCurrentLoggedInUser] = useState<UserInfo | null>(null);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [searchOptions, setSearchOptions] = useState<{ value: string; label: string }[]>([]);

  // Modal 狀態
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  // 權限相關
  const [userPermissions, setUserPermissions] = useState<UserPermissions | null>(null);
  const [roles, setRoles] = useState<Permission[]>([]);

  // 選擇狀態
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  // 分頁狀態
  const [pagination, setPagination] = useState<UserPagination>({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // ==================== API 呼叫 ====================

  const fetchCurrentUser = useCallback(async () => {
    try {
      const userInfo = authService.getUserInfo();
      if (userInfo) {
        setCurrentLoggedInUser(userInfo);
      }
    } catch (error) {
      logger.error('Failed to get current user info:', error);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/admin/user-management/users', {
        params: {
          page: pagination.current,
          per_page: pagination.pageSize,
          q: searchText || undefined,
          role: roleFilter || undefined,
          auth_provider: providerFilter || undefined,
        },
      });

      setUsers(response.data.users);
      setPagination(prev => ({ ...prev, total: response.data.total }));
    } catch (error) {
      logger.error('載入使用者列表失敗:', error);
      message.error('載入使用者列表失敗，請稍後重試');
      setUsers([]);
      setPagination(prev => ({ ...prev, total: 0 }));
    } finally {
      setLoading(false);
    }
  }, [pagination.current, pagination.pageSize, searchText, roleFilter, providerFilter, message]);

  const fetchAvailablePermissions = useCallback(async () => {
    try {
      const response = await apiClient.get('/admin/user-management/permissions/available');
      setRoles(response.data.roles);
    } catch (error) {
      logger.error('載入權限資料失敗:', error);
      message.error('載入權限資料失敗，請稍後重試');
      setRoles([]);
    }
  }, [message]);

  const fetchUserPermissions = useCallback(async (userId: number) => {
    try {
      const response = await apiClient.get(`/admin/user-management/users/${userId}/permissions`);
      setUserPermissions(response.data);
    } catch (error) {
      logger.error('載入使用者權限失敗:', error);
      message.error('載入使用者權限失敗，請稍後重試');
      setUserPermissions(null);
    }
  }, [message]);

  useEffect(() => {
    fetchUsers();
    fetchAvailablePermissions();
    fetchCurrentUser();
  }, [pagination.current, pagination.pageSize, searchText, roleFilter, providerFilter]);

  // ==================== 搜尋處理 ====================

  const handleAutoCompleteSearch = useCallback(
    debounce(async (searchValue: string) => {
      if (!searchValue || searchValue.length < 1) {
        setSearchOptions([]);
        return;
      }
      try {
        const response = await apiClient.get('/admin/user-management/users', {
          params: { q: searchValue, per_page: 10 }
        });
        if (response.data?.users) {
          setSearchOptions(response.data.users.map((user: User) => ({
            value: user.email,
            label: `${user.full_name || user.username} (${user.email})`
          })));
        }
      } catch (error) {
        logger.error('搜尋失敗', error);
      }
    }, 300),
    []
  );

  const handleTableChange: TableProps<User>['onChange'] = useCallback((
    paginationInfo: any,
    _filters: any,
    _sorter: any
  ) => {
    // 處理分頁變更
    if (paginationInfo) {
      setPagination(prev => ({
        ...prev,
        current: paginationInfo.current || 1,
        pageSize: paginationInfo.pageSize || 20,
      }));
    }
  }, []);

  // ==================== 使用者操作 ====================

  const handleEdit = useCallback((user: User) => {
    setCurrentUser(user);
    setEditModalVisible(true);
  }, []);

  const handleEditPermissions = useCallback(async (user: User) => {
    setCurrentUser(user);
    setPermissionModalVisible(true);
    await fetchUserPermissions(user.id);
  }, [fetchUserPermissions]);

  const handleUpdateUser = useCallback(async (values: any) => {
    try {
      const updateData = {
        ...values,
        is_active: values.status === 'active',
      };
      delete updateData.status;

      if (currentUser) {
        await apiClient.put(`/admin/user-management/users/${currentUser.id}`, updateData);
        message.success('使用者資訊更新成功');
      } else {
        await apiClient.post('/admin/user-management/users', updateData);
        message.success('新增使用者成功');
      }

      setEditModalVisible(false);
      fetchUsers();
    } catch (error: any) {
      logger.error('Failed to save user:', error);
      let errorMessage = currentUser ? '更新使用者失敗' : '新增使用者失敗';

      if (error.response?.data) {
        const errorData = error.response.data;
        if (Array.isArray(errorData.detail)) {
          const validationErrors = errorData.detail.map((err: any) =>
            `${err.loc?.join('.')}: ${err.msg}`
          ).join(', ');
          errorMessage = `驗證錯誤: ${validationErrors}`;
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      }

      message.error(errorMessage);
    }
  }, [currentUser, message, fetchUsers]);

  const handleUpdatePermissions = useCallback(async (values: any) => {
    if (!currentUser) return;

    try {
      await apiClient.put(
        `/admin/user-management/users/${currentUser.id}/permissions`,
        {
          user_id: currentUser.id,
          permissions: values.permissions || [],
          role: values.role,
        }
      );

      message.success('使用者權限更新成功');
      setPermissionModalVisible(false);
      fetchUsers();
    } catch (error: any) {
      logger.error('Failed to update permissions:', error);
      const errorMessage = error.response?.data?.detail || '更新權限失敗';
      message.error(errorMessage);
    }
  }, [currentUser, message, fetchUsers]);

  const handleDeleteUser = useCallback(async (userId: number) => {
    try {
      await apiClient.delete(`/admin/user-management/users/${userId}`);
      message.success('使用者已刪除');
      fetchUsers();
    } catch (error: any) {
      logger.error('Failed to delete user:', error);
      const errorMessage = error.response?.data?.detail || '刪除使用者失敗';
      message.error(errorMessage);
    }
  }, [message, fetchUsers]);

  // ==================== 批量操作 ====================

  const handleBatchDelete = useCallback(async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('請選擇要刪除的使用者');
      return;
    }

    Modal.confirm({
      title: '確認批量刪除',
      content: `確定要刪除選中的 ${selectedRowKeys.length} 個使用者嗎？`,
      onOk: async () => {
        try {
          for (const userId of selectedRowKeys) {
            await apiClient.delete(`/admin/user-management/users/${userId}`);
          }
          message.success(`已成功刪除 ${selectedRowKeys.length} 個使用者`);
          setSelectedRowKeys([]);
          fetchUsers();
        } catch (error: any) {
          logger.error('Batch delete failed:', error);
          message.error('批量刪除失敗');
        }
      },
    });
  }, [selectedRowKeys, message, fetchUsers]);

  const handleBatchStatusChange = useCallback(async (status: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('請選擇要更新的使用者');
      return;
    }

    const statusName = getStatusDisplayName(status);

    try {
      for (const userId of selectedRowKeys) {
        await apiClient.put(
          `/admin/user-management/users/${userId}`,
          { status, is_active: status === 'active' }
        );
      }
      message.success(`已成功將 ${selectedRowKeys.length} 個使用者狀態更新為 ${statusName}`);
      setSelectedRowKeys([]);
      fetchUsers();
    } catch (error: any) {
      logger.error('Batch status update failed:', error);
      message.error('批量更新狀態失敗');
    }
  }, [selectedRowKeys, message, fetchUsers]);

  const handleBatchRoleChange = useCallback(async (role: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('請選擇要更新的使用者');
      return;
    }

    const roleName = getRoleDisplayName(role);

    Modal.confirm({
      title: '批量驗證使用者',
      content: `確定要將選中的 ${selectedRowKeys.length} 個使用者驗證為 ${roleName} 嗎？這將會給予他們相應的系統權限。`,
      onOk: async () => {
        try {
          const defaultPermissions = getRoleDefaultPermissions(role);

          for (const userId of selectedRowKeys) {
            await apiClient.put(
              `/admin/user-management/users/${userId}`,
              { role, status: 'active', is_active: true }
            );

            await apiClient.put(
              `/admin/user-management/users/${userId}/permissions`,
              { user_id: userId, permissions: defaultPermissions, role }
            );
          }

          message.success(`已成功驗證 ${selectedRowKeys.length} 個使用者為 ${roleName}`);
          setSelectedRowKeys([]);
          fetchUsers();
        } catch (error: any) {
          logger.error('Batch role update failed:', error);
          message.error('批量驗證失敗');
        }
      },
    });
  }, [selectedRowKeys, message, fetchUsers]);

  const handleRoleChange = useCallback((role: string) => {
    const selectedRole = roles.find(r => r.name === role);
    if (selectedRole) {
      // Role change handled in UserPermissionModal
    }
  }, [roles]);

  // ==================== 表格欄位 ====================

  const columns = useMemo(() => createUserTableColumns({
    onEdit: handleEdit,
    onEditPermissions: handleEditPermissions,
    onDelete: handleDeleteUser,
  }), [handleEdit, handleEditPermissions, handleDeleteUser]);

  // ==================== 渲染 ====================

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        {/* 標題列 */}
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <TeamOutlined style={{ marginRight: '8px' }} />
                使用者權限管理
              </Title>
            </Col>
            <Col>
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    setCurrentUser(null);
                    setEditModalVisible(true);
                  }}
                >
                  新增使用者
                </Button>
                {selectedRowKeys.length > 0 && (
                  <>
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      onClick={() => handleBatchRoleChange('user')}
                    >
                      批量驗證為使用者 ({selectedRowKeys.length})
                    </Button>
                    <Button
                      icon={<CheckOutlined />}
                      onClick={() => handleBatchStatusChange('active')}
                    >
                      批量啟用
                    </Button>
                    <Button
                      icon={<StopOutlined />}
                      onClick={() => handleBatchStatusChange('suspended')}
                    >
                      批量暫停
                    </Button>
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={handleBatchDelete}
                    >
                      批量刪除
                    </Button>
                  </>
                )}
              </Space>
            </Col>
          </Row>
        </div>

        {/* 篩選列 */}
        <Row gutter={16} style={{ marginBottom: '16px' }}>
          <Col span={6}>
            <AutoComplete
              options={searchOptions}
              onSearch={handleAutoCompleteSearch}
              onSelect={(value) => setSearchText(value)}
              style={{ width: '100%' }}
            >
              <Input
                placeholder="搜尋使用者名稱或電子郵件"
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onPressEnter={() => fetchUsers()}
                allowClear
              />
            </AutoComplete>
          </Col>
          <Col span={4}>
            <Select
              placeholder="角色篩選"
              allowClear
              value={roleFilter || undefined}
              onChange={setRoleFilter}
              style={{ width: '100%' }}
            >
              <Option value="user">一般使用者</Option>
              <Option value="admin">管理員</Option>
              <Option value="superuser">超級管理員</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Select
              placeholder="認證方式"
              allowClear
              value={providerFilter || undefined}
              onChange={setProviderFilter}
              style={{ width: '100%' }}
            >
              <Option value="email">電子郵件</Option>
              <Option value="google">Google</Option>
            </Select>
          </Col>
          <Col span={4}>
            <Button type="primary" onClick={() => fetchUsers()}>
              搜尋
            </Button>
          </Col>
        </Row>

        {/* 使用者表格 */}
        <Table
          columns={columns}
          dataSource={users}
          loading={loading}
          rowKey="id"
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          rowSelection={{
            selectedRowKeys,
            onChange: (newSelectedRowKeys) => setSelectedRowKeys(newSelectedRowKeys),
            getCheckboxProps: (record: User) => ({
              disabled: currentLoggedInUser ? record.id === currentLoggedInUser.id : false,
            }),
          }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
            onChange: (page, pageSize) => {
              setPagination(prev => ({
                ...prev,
                current: page,
                pageSize: pageSize || 20,
              }));
            },
          }}
        />
      </Card>

      {/* 編輯使用者 Modal */}
      <UserEditModal
        visible={editModalVisible}
        user={currentUser}
        currentLoggedInUser={currentLoggedInUser}
        onSubmit={handleUpdateUser}
        onCancel={() => setEditModalVisible(false)}
      />

      {/* 權限管理 Modal */}
      <UserPermissionModal
        visible={permissionModalVisible}
        user={currentUser}
        userPermissions={userPermissions}
        roles={roles}
        currentLoggedInUser={currentLoggedInUser}
        onSubmit={handleUpdatePermissions}
        onCancel={() => setPermissionModalVisible(false)}
        onRoleChange={handleRoleChange}
      />
    </div>
  );
};

export default UserManagementPage;
