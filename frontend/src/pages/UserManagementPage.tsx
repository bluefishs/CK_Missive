/**
 * 使用者管理頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（使用者列表）
 * - 純導航模式：點擊列直接導航至 UserFormPage 進行編輯
 *
 * 表格欄位：
 * - 使用者（姓名 + 電子郵件）
 * - 認證方式（Google/電子郵件）
 * - 角色
 * - 狀態
 * - 註冊時間
 * - 最後登入
 *
 * @version 5.2.0 - 移除權限維護欄位（改由使用者編輯頁處理）
 * @date 2026-02-02
 */
import { useState, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Button, Space, Input, Select, Row, Col, Typography, AutoComplete, Tag
} from 'antd';
import type { TableProps, InputRef } from 'antd';
import { ResponsiveTable } from '../components/common';
import type { ColumnsType, ColumnType } from 'antd/es/table';
import type { FilterConfirmProps } from 'antd/es/table/interface';
import Highlighter from 'react-highlight-words';
import debounce from 'lodash/debounce';
import { PlusOutlined, SearchOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
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

// 認證方式顯示名稱
const getAuthProviderDisplay = (provider?: string) => {
  const providerNames: Record<string, { label: string; color: string }> = {
    google: { label: 'Google', color: 'blue' },
    email: { label: '電子郵件', color: 'green' },
    local: { label: '本地帳號', color: 'default' },
  };
  return providerNames[provider || 'email'] || { label: provider || '未知', color: 'default' };
};

// 格式化日期時間
const formatDateTime = (dateStr?: string | null) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

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

  // 表格內建搜尋狀態
  const [tableSearchText, setTableSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

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
  // 表格內建搜尋處理
  // ============================================================================

  const handleTableSearch = useCallback(
    (selectedKeys: string[], confirm: (param?: FilterConfirmProps) => void, dataIndex: string) => {
      confirm();
      setTableSearchText(selectedKeys[0] || '');
      setSearchedColumn(dataIndex);
    },
    []
  );

  const handleTableReset = useCallback((clearFilters: () => void) => {
    clearFilters();
    setTableSearchText('');
  }, []);

  // 取得欄位搜尋配置
  const getColumnSearchProps = useCallback(
    (dataIndex: string, title: string): ColumnType<User> => ({
      filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
        <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
          <Input
            ref={searchInput}
            placeholder={`搜尋${title}`}
            value={selectedKeys[0]}
            onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
            onPressEnter={() => handleTableSearch(selectedKeys as string[], confirm, dataIndex)}
            style={{ marginBottom: 8, display: 'block' }}
          />
          <Space>
            <Button
              type="primary"
              onClick={() => handleTableSearch(selectedKeys as string[], confirm, dataIndex)}
              icon={<SearchOutlined />}
              size="small"
              style={{ width: 90 }}
            >
              搜尋
            </Button>
            <Button
              onClick={() => clearFilters && handleTableReset(clearFilters)}
              size="small"
              style={{ width: 90 }}
            >
              重置
            </Button>
            <Button type="link" size="small" onClick={() => close()}>
              關閉
            </Button>
          </Space>
        </div>
      ),
      filterIcon: (filtered: boolean) => (
        <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
      ),
      onFilter: (value, record) => {
        if (dataIndex === 'user') {
          // 使用者欄位搜尋：名稱、email、帳號
          const searchValue = (value as string).toLowerCase();
          return (
            (record.full_name?.toLowerCase().includes(searchValue) || false) ||
            record.email.toLowerCase().includes(searchValue) ||
            record.username.toLowerCase().includes(searchValue)
          );
        }
        const fieldValue = record[dataIndex as keyof User];
        if (fieldValue === null || fieldValue === undefined) return false;
        return String(fieldValue).toLowerCase().includes((value as string).toLowerCase());
      },
      filterDropdownProps: {
        onOpenChange(open: boolean) {
          if (open) {
            setTimeout(() => searchInput.current?.select(), 100);
          }
        },
      },
    }),
    [handleTableSearch, handleTableReset]
  );

  // ============================================================================
  // 外部搜尋處理（AutoComplete）
  // ============================================================================

  // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce instance must be stable; users is captured in closure
  const handleAutoCompleteSearch = useMemo(
    () => debounce(async (searchValue: string) => {
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
    paginationInfo: { current?: number; pageSize?: number } | undefined,
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
  // 篩選選項定義
  // ============================================================================

  // 角色篩選選項
  const roleFilters = [
    { text: '超級管理員', value: 'superuser' },
    { text: '管理員', value: 'admin' },
    { text: '一般使用者', value: 'user' },
    { text: '訪客', value: 'guest' },
  ];

  // 認證方式篩選選項
  const authProviderFilters = [
    { text: 'Google', value: 'google' },
    { text: '電子郵件', value: 'email' },
    { text: '本地帳號', value: 'local' },
  ];

  // 狀態篩選選項
  const statusFilters = [
    { text: '啟用', value: true },
    { text: '停用', value: false },
  ];

  // ============================================================================
  // 表格欄位 - 依規範調整（含排序、篩選、搜尋功能）
  // ============================================================================

  const columns: ColumnsType<User> = useMemo(() => [
    {
      title: '使用者',
      key: 'user',
      width: isMobile ? 150 : 200,
      ...getColumnSearchProps('user', '使用者'),
      sorter: (a, b) => (a.full_name || a.username).localeCompare(b.full_name || b.username, 'zh-TW'),
      render: (_: unknown, record: User) => {
        const displayName = record.full_name || record.username;
        return (
          <Space>
            <UserOutlined style={{ color: '#1976d2' }} />
            <div>
              <div style={{ fontWeight: 500 }}>
                {searchedColumn === 'user' && tableSearchText ? (
                  <Highlighter
                    highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                    searchWords={[tableSearchText]}
                    autoEscape
                    textToHighlight={displayName}
                  />
                ) : displayName}
              </div>
              <Typography.Text type="secondary" style={{ fontSize: '12px' }}>
                {searchedColumn === 'user' && tableSearchText ? (
                  <Highlighter
                    highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                    searchWords={[tableSearchText]}
                    autoEscape
                    textToHighlight={record.email}
                  />
                ) : record.email}
              </Typography.Text>
            </div>
          </Space>
        );
      },
    },
    {
      title: '認證方式',
      dataIndex: 'auth_provider',
      key: 'auth_provider',
      width: 100,
      align: 'center' as const,
      filters: authProviderFilters,
      onFilter: (value, record) => (record.auth_provider || 'email') === value,
      sorter: (a, b) => (a.auth_provider || 'email').localeCompare(b.auth_provider || 'email'),
      render: (provider: string) => {
        const display = getAuthProviderDisplay(provider);
        return <Tag color={display.color}>{display.label}</Tag>;
      },
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      align: 'center' as const,
      filters: roleFilters,
      onFilter: (value, record) => record.role === value,
      sorter: (a, b) => (a.role || '').localeCompare(b.role || '', 'zh-TW'),
      render: (role: string) => getRoleDisplayName(role),
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      align: 'center' as const,
      filters: statusFilters,
      onFilter: (value, record) => record.is_active === value,
      sorter: (a, b) => (a.is_active === b.is_active ? 0 : a.is_active ? -1 : 1),
      render: (isActive: boolean, record: User) => (
        <span style={{ color: isActive ? '#52c41a' : '#ff4d4f' }}>
          {getStatusDisplayName(record.status || (isActive ? 'active' : 'inactive'))}
        </span>
      ),
    },
    {
      title: '註冊時間',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      sorter: (a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateA - dateB;
      },
      render: (date: string) => formatDateTime(date),
    },
    {
      title: '最後登入',
      dataIndex: 'last_login',
      key: 'last_login',
      width: 140,
      sorter: (a, b) => {
        const dateA = a.last_login ? new Date(a.last_login).getTime() : 0;
        const dateB = b.last_login ? new Date(b.last_login).getTime() : 0;
        return dateA - dateB;
      },
      render: (date: string) => formatDateTime(date),
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps -- authProviderFilters/roleFilters/statusFilters are stable inline arrays
  ], [isMobile, getColumnSearchProps, searchedColumn, tableSearchText]);

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
        <ResponsiveTable
          columns={columns}
          dataSource={users}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: isMobile ? 400 : 800 }}
          mobileHiddenColumns={['auth_provider', 'created_at', 'last_login']}
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
