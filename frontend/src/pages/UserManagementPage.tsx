/**
 * 使用者管理頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（使用者列表）
 * - 純導航模式：點擊列直接導航至 UserFormPage
 * - 無操作按鈕：編輯/刪除操作統一在 UserFormPage 處理
 *
 * @version 4.0.0 - 純導航模式，移除 Modal 和操作按鈕
 * @date 2026-01-26
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Table, Button, Space, Input, Select, Row, Col, Typography, AutoComplete
} from 'antd';
import type { TableProps } from 'antd';
import debounce from 'lodash/debounce';
import { PlusOutlined, SearchOutlined, TeamOutlined } from '@ant-design/icons';
import {
  getRoleDisplayName,
  getStatusDisplayName,
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
  // 導航操作
  // ============================================================================

  const handleCreate = useCallback(() => {
    navigate(ROUTES.USER_CREATE);
  }, [navigate]);

  const handleRowClick = useCallback((user: User) => {
    navigate(ROUTES.USER_EDIT.replace(':id', String(user.id)));
  }, [navigate]);

  // ============================================================================
  // 表格欄位（純顯示，無操作按鈕）
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
  ], []);

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
                {isMobile ? '使用者管理' : '使用者管理'}
              </Title>
            </Col>
            <Col xs={24} sm={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size={isMobile ? 'small' : 'middle'}
                onClick={handleCreate}
              >
                {isMobile ? '' : '新增使用者'}
              </Button>
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
          loading={isLoading}
          rowKey="id"
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: isMobile ? 400 : 800 }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' },
          })}
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
