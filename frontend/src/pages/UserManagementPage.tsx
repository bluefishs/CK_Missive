/**
 * 使用者權限管理頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（使用者列表、權限）
 * - Zustand: 不使用（本頁面無需跨頁面共享狀態）
 * - Mutation Hooks: 處理建立/更新/刪除，自動失效快取
 *
 * @version 2.0.0 - 優化為 React Query 架構
 * @date 2026-01-08
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Card, Table, Button, Space, Input, Select, App, Row, Col, Typography,
  Modal, AutoComplete
} from 'antd';
import type { TableProps } from 'antd';
import debounce from 'lodash/debounce';
import {
  PlusOutlined, SearchOutlined, TeamOutlined,
  DeleteOutlined, StopOutlined, CheckOutlined
} from '@ant-design/icons';
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
import type { User, UserPermissions } from '../types/user';
import {
  useAdminUsersPage,
  useUserPermissions,
} from '../hooks';

const { Title } = Typography;
const { Option } = Select;

const UserManagementPage: React.FC = () => {
  const { message } = App.useApp();

  // ============================================================================
  // UI 狀態（本地狀態）
  // ============================================================================

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [searchOptions, setSearchOptions] = useState<{ value: string; label: string }[]>([]);

  // 分頁狀態
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Modal 狀態
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  // 選擇狀態
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  // 當前登入使用者
  const currentLoggedInUser = useMemo<UserInfo | null>(() => {
    return authService.getUserInfo();
  }, []);

  // ============================================================================
  // React Query: 唯一的伺服器資料來源
  // ============================================================================

  const queryParams = useMemo(() => ({
    page: currentPage,
    per_page: pageSize,
    ...(searchText && { q: searchText }),
    ...(roleFilter && { role: roleFilter }),
    ...(providerFilter && { auth_provider: providerFilter }),
  }), [currentPage, pageSize, searchText, roleFilter, providerFilter]);

  const {
    users,
    total,
    isLoading,
    roles,
    refetch,
    createUser,
    updateUser,
    deleteUser,
    updatePermissions,
    batchUpdateStatus,
    batchDelete,
    batchUpdateRole,
    isCreating,
    isUpdating,
    isDeleting,
    isBatchUpdating,
  } = useAdminUsersPage(queryParams);

  // 使用者權限查詢（當 permissionModal 開啟時才查詢）
  const {
    data: userPermissions,
    isLoading: isPermissionsLoading,
  } = useUserPermissions(permissionModalVisible ? currentUser?.id ?? null : null);

  // ============================================================================
  // 搜尋處理
  // ============================================================================

  const handleAutoCompleteSearch = useCallback(
    debounce(async (searchValue: string) => {
      if (!searchValue || searchValue.length < 1) {
        setSearchOptions([]);
        return;
      }
      // 使用當前查詢的 users 進行過濾（避免額外 API 呼叫）
      const filtered = users.filter((user: User) =>
        user.email.toLowerCase().includes(searchValue.toLowerCase()) ||
        (user.full_name && user.full_name.toLowerCase().includes(searchValue.toLowerCase())) ||
        user.username.toLowerCase().includes(searchValue.toLowerCase())
      );
      setSearchOptions(filtered.slice(0, 10).map((user: User) => ({
        value: user.email,
        label: `${user.full_name || user.username} (${user.email})`
      })));
    }, 300),
    [users]
  );

  const handleTableChange: TableProps<User>['onChange'] = useCallback((
    paginationInfo: any,
  ) => {
    if (paginationInfo) {
      setCurrentPage(paginationInfo.current || 1);
      setPageSize(paginationInfo.pageSize || 20);
    }
  }, []);

  // ============================================================================
  // 使用者操作（使用 Mutation Hooks）
  // ============================================================================

  const handleEdit = useCallback((user: User) => {
    setCurrentUser(user);
    setEditModalVisible(true);
  }, []);

  const handleEditPermissions = useCallback((user: User) => {
    setCurrentUser(user);
    setPermissionModalVisible(true);
  }, []);

  const handleUpdateUser = useCallback(async (values: any) => {
    try {
      const updateData = {
        ...values,
        is_active: values.status === 'active',
      };
      delete updateData.status;

      if (currentUser) {
        await updateUser({ userId: currentUser.id, data: updateData });
        message.success('使用者資訊更新成功');
      } else {
        await createUser(updateData);
        message.success('新增使用者成功');
      }

      setEditModalVisible(false);
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
  }, [currentUser, message, updateUser, createUser]);

  const handleUpdatePermissions = useCallback(async (values: any) => {
    if (!currentUser) return;

    try {
      await updatePermissions({
        userId: currentUser.id,
        data: {
          user_id: currentUser.id,
          permissions: values.permissions || [],
          role: values.role,
        },
      });

      message.success('使用者權限更新成功');
      setPermissionModalVisible(false);
    } catch (error: any) {
      logger.error('Failed to update permissions:', error);
      const errorMessage = error.response?.data?.detail || '更新權限失敗';
      message.error(errorMessage);
    }
  }, [currentUser, message, updatePermissions]);

  const handleDeleteUser = useCallback(async (userId: number) => {
    try {
      await deleteUser(userId);
      message.success('使用者已刪除');
    } catch (error: any) {
      logger.error('Failed to delete user:', error);
      const errorMessage = error.response?.data?.detail || '刪除使用者失敗';
      message.error(errorMessage);
    }
  }, [message, deleteUser]);

  // ============================================================================
  // 批量操作
  // ============================================================================

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
          await batchDelete(selectedRowKeys as number[]);
          message.success(`已成功刪除 ${selectedRowKeys.length} 個使用者`);
          setSelectedRowKeys([]);
        } catch (error: any) {
          logger.error('Batch delete failed:', error);
          message.error('批量刪除失敗');
        }
      },
    });
  }, [selectedRowKeys, message, batchDelete]);

  const handleBatchStatusChange = useCallback(async (status: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('請選擇要更新的使用者');
      return;
    }

    const statusName = getStatusDisplayName(status);

    try {
      await batchUpdateStatus({
        userIds: selectedRowKeys as number[],
        status,
        isActive: status === 'active',
      });
      message.success(`已成功將 ${selectedRowKeys.length} 個使用者狀態更新為 ${statusName}`);
      setSelectedRowKeys([]);
    } catch (error: any) {
      logger.error('Batch status update failed:', error);
      message.error('批量更新狀態失敗');
    }
  }, [selectedRowKeys, message, batchUpdateStatus]);

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
          await batchUpdateRole({
            userIds: selectedRowKeys as number[],
            role,
            permissions: defaultPermissions,
          });
          message.success(`已成功驗證 ${selectedRowKeys.length} 個使用者為 ${roleName}`);
          setSelectedRowKeys([]);
        } catch (error: any) {
          logger.error('Batch role update failed:', error);
          message.error('批量驗證失敗');
        }
      },
    });
  }, [selectedRowKeys, message, batchUpdateRole]);

  const handleRoleChange = useCallback((role: string) => {
    const selectedRole = roles.find(r => r.name === role);
    if (selectedRole) {
      // Role change handled in UserPermissionModal
    }
  }, [roles]);

  // ============================================================================
  // 表格欄位
  // ============================================================================

  const columns = useMemo(() => createUserTableColumns({
    onEdit: handleEdit,
    onEditPermissions: handleEditPermissions,
    onDelete: handleDeleteUser,
  }), [handleEdit, handleEditPermissions, handleDeleteUser]);

  // ============================================================================
  // 渲染
  // ============================================================================

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
                      loading={isBatchUpdating}
                    >
                      批量驗證為使用者 ({selectedRowKeys.length})
                    </Button>
                    <Button
                      icon={<CheckOutlined />}
                      onClick={() => handleBatchStatusChange('active')}
                      loading={isBatchUpdating}
                    >
                      批量啟用
                    </Button>
                    <Button
                      icon={<StopOutlined />}
                      onClick={() => handleBatchStatusChange('suspended')}
                      loading={isBatchUpdating}
                    >
                      批量暫停
                    </Button>
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={handleBatchDelete}
                      loading={isBatchUpdating}
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
                onPressEnter={() => refetch()}
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
            <Button type="primary" onClick={() => refetch()}>
              搜尋
            </Button>
          </Col>
        </Row>

        {/* 使用者表格 */}
        <Table
          columns={columns}
          dataSource={users}
          loading={isLoading || isDeleting}
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
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size || 20);
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
        userPermissions={userPermissions ?? null}
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
