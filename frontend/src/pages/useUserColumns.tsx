/**
 * User Management - Column definitions & search
 *
 * Extracted from UserManagementPage.tsx to reduce main file size.
 */

import { useState, useRef, useCallback, useMemo } from 'react';
import { Input, Button, Space, Typography, Tag } from 'antd';
import type { InputRef } from 'antd';
import type { ColumnType, ColumnsType } from 'antd/es/table';
import type { FilterConfirmProps } from 'antd/es/table/interface';
import Highlighter from 'react-highlight-words';
import { SearchOutlined, UserOutlined } from '@ant-design/icons';
import { getRoleDisplayName, getStatusDisplayName } from '../constants/permissions';
import type { User } from '../types/api';

// Auth provider display config
const PROVIDER_CONFIG: Record<string, { label: string; color: string; icon?: string }> = {
  email: { label: '電子郵件', color: 'green' },
  google: { label: 'Google', color: 'blue' },
  line: { label: 'LINE', color: 'lime' },
  internal: { label: '內網', color: 'orange' },
  local: { label: '本地帳號', color: 'default' },
};

const getProviderTag = (provider: string) => {
  const config = PROVIDER_CONFIG[provider] || { label: provider, color: 'default' };
  return config;
};

// Date formatting
const formatDateTime = (dateStr?: string | null) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString('zh-TW', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
};

export function useUserColumns(isMobile: boolean) {
  const [tableSearchText, setTableSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

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
          if (open) setTimeout(() => searchInput.current?.select(), 100);
        },
      },
    }),
    [handleTableSearch, handleTableReset]
  );

  const roleFilters = [
    { text: '超級管理員', value: 'superuser' },
    { text: '管理員', value: 'admin' },
    { text: '一般使用者', value: 'user' },
    { text: '訪客', value: 'guest' },
  ];

  const authProviderFilters = [
    { text: '電子郵件', value: 'email' },
    { text: 'Google', value: 'google' },
    { text: 'LINE', value: 'line' },
    { text: '內網', value: 'internal' },
  ];

  const statusFilters = [
    { text: '啟用', value: true },
    { text: '停用', value: false },
  ];

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
      dataIndex: 'auth_providers',
      key: 'auth_providers',
      width: 130,
      align: 'center' as const,
      filters: authProviderFilters,
      onFilter: (value, record) => {
        const providers = record.auth_providers || [record.auth_provider || 'email'];
        return providers.includes(value as string);
      },
      sorter: (a, b) => {
        const aProviders = (a.auth_providers || [a.auth_provider || 'email']).join(',');
        const bProviders = (b.auth_providers || [b.auth_provider || 'email']).join(',');
        return aProviders.localeCompare(bProviders);
      },
      render: (_: unknown, record: User) => {
        const providers = record.auth_providers?.length
          ? record.auth_providers
          : [record.auth_provider || 'email'];
        return (
          <Space size={2} wrap>
            {providers.map((p) => {
              const config = getProviderTag(p);
              return <Tag key={p} color={config.color} style={{ margin: 0 }}>{config.label}</Tag>;
            })}
          </Space>
        );
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

  return { columns };
}
