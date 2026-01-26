/**
 * 使用者權限管理頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（使用者列表）
 * - 導航模式：點擊編輯導航至 UserFormPage
 * - 批量操作：支援批量啟用、停用、刪除
 *
 * @version 3.0.0 - 改為導航模式，移除 Modal
 * @date 2026-01-26
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
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
import type { User } from '../types/api';
import {
  useAdminUsersPage,
  useResponsive,
} from '../hooks';
import { ROUTES } from '../router/types';

const { Title } = Typography;
const { Option } = Select;

const UserManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  // RWD 響應式
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

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
    refetch,
    deleteUser,
    batchUpdateStatus,
    batchDelete,
    batchUpdateRole,
    isDeleting,
    isBatchUpdating,
  } = useAdminUsersPage(queryParams);

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
  // 導航操作（取代 Modal）
  // ============================================================================

  const handleCreate = useCallback(() => {
    navigate(ROUTES.USER_CREATE);
  }, [navigate]);

  const handleEdit = useCallback((user: User) => {
    navigate(ROUTES.USER_EDIT.replace(':id', String(user.id)));
  }, [navigate]);

  const handleDeleteUser = useCallback(async (userId: number) => {
    Modal.confirm({
      title: '確認刪除',
      content: '確定要刪除此使用者嗎？',
      okText: '確定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteUser(userId);
          message.success('使用者已刪除');
        } catch (error: any) {
          logger.error('Failed to delete user:', error);
          const errorMessage = error.response?.data?.detail || '刪除使用者失敗';
          message.error(errorMessage);
        }
      },
    });
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

  // ============================================================================
  // 表格欄位（導航模式）
  // ============================================================================

  const columns = useMemo(() => [
    {
      title: '電子郵件',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
    },
    {
      title: '使用者名稱',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '姓名',
      dataIndex: 'full_name',
      key: 'full_name',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => getRoleDisplayName(role),
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean, record: User) => (
        <span style={{ color: isActive ? '#52c41a' : '#ff4d4f' }}>
          {getStatusDisplayName(record.status || (isActive ? 'active' : 'inactive'))}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: User) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(record);
            }}
          >
            編輯
          </Button>
          <Button
            type="link"
            size="small"
            danger
            disabled={currentLoggedInUser?.id === record.id}
            onClick={(e) => {
              e.stopPropagation();
              handleDeleteUser(record.id);
            }}
          >
            刪除
          </Button>
        </Space>
      ),
    },
  ], [handleEdit, handleDeleteUser, currentLoggedInUser]);

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <div style={{ padding: pagePadding }}>
      <Card size={isMobile ? 'small' : 'default'}>
        {/* 標題列 */}
        <div style={{ marginBottom: isMobile ? 12 : 24 }}>
          <Row
            justify="space-between"
            align={isMobile ? 'top' : 'middle'}
            gutter={[8, 8]}
          >
            <Col xs={24} sm={12}>
              <Title level={isMobile ? 4 : 3} style={{ margin: 0 }}>
                <TeamOutlined style={{ marginRight: 8 }} />
                {isMobile ? '使用者管理' : '使用者權限管理'}
              </Title>
            </Col>
            <Col xs={24} sm={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
              <Space size={isMobile ? 'small' : 'middle'} wrap>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size={isMobile ? 'small' : 'middle'}
                  onClick={handleCreate}
                >
                  {isMobile ? '' : '新增使用者'}
                </Button>
                {selectedRowKeys.length > 0 && !isMobile && (
                  <>
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      onClick={() => handleBatchRoleChange('user')}
                      loading={isBatchUpdating}
                    >
                      批量驗證 ({selectedRowKeys.length})
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
        <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <AutoComplete
              options={searchOptions}
              onSearch={handleAutoCompleteSearch}
              onSelect={(value) => setSearchText(value)}
              style={{ width: '100%' }}
            >
              <Input
                placeholder={isMobile ? '搜尋...' : '搜尋使用者名稱或電子郵件'}
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onPressEnter={() => refetch()}
                size={isMobile ? 'small' : 'middle'}
                allowClear
              />
            </AutoComplete>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder={isMobile ? '角色' : '角色篩選'}
              allowClear
              value={roleFilter || undefined}
              onChange={setRoleFilter}
              style={{ width: '100%' }}
              size={isMobile ? 'small' : 'middle'}
            >
              <Option value="user">一般使用者</Option>
              <Option value="admin">管理員</Option>
              <Option value="superuser">超級管理員</Option>
            </Select>
          </Col>
          {!isMobile && (
            <Col sm={6} md={4}>
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
          )}
          <Col xs={12} sm={6} md={4}>
            <Button
              type="primary"
              onClick={() => refetch()}
              size={isMobile ? 'small' : 'middle'}
              style={{ width: isMobile ? '100%' : 'auto' }}
            >
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
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: isMobile ? 400 : 800 }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          rowSelection={isMobile ? undefined : {
            selectedRowKeys,
            onChange: (newSelectedRowKeys) => setSelectedRowKeys(newSelectedRowKeys),
            getCheckboxProps: (record: User) => ({
              disabled: currentLoggedInUser ? record.id === currentLoggedInUser.id : false,
            }),
          }}
          pagination={{
            current: currentPage,
            pageSize: isMobile ? 10 : pageSize,
            total: total,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: isMobile ? undefined : (total, range) =>
              `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size || 20);
            },
            size: isMobile ? 'small' : 'default',
          }}
        />
      </Card>
    </div>
  );
};

export default UserManagementPage;
