/**
 * 使用者管理頁面
 *
 * @version 5.3.0 - 欄位定義拆分至 useUserColumns
 */
import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Button, Input, Select, Row, Col, Typography, AutoComplete, Space,
} from 'antd';
import type { TableProps } from 'antd';
import { ResponsiveTable } from '../components/common';
import debounce from 'lodash/debounce';
import { PlusOutlined, SearchOutlined, TeamOutlined, UserSwitchOutlined } from '@ant-design/icons';
import type { User } from '../types/api';
import { useAdminUsersPage, useResponsive } from '../hooks';
import { ROUTES } from '../router/types';
import { useUserColumns } from './useUserColumns';
import { AliasIntegrationDrawer } from '../components/admin/AliasIntegrationDrawer';

const { Title } = Typography;
const { Option } = Select;

const UserManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [searchOptions, setSearchOptions] = useState<{ value: string; label: string }[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [aliasDrawerOpen, setAliasDrawerOpen] = useState(false);

  // ADR-0025 Identity Unification：永遠以完整姓名為單位呈現（canonical + 聚合 aliases），
  // 活躍用戶優先。已停用帳號以狀態過濾器檢視。
  const queryParams = useMemo(() => ({
    page: currentPage,
    per_page: pageSize,
    canonical_only: true,         // 一人一列，alias 內化為聚合資訊
    is_active: true,              // 預設只看活躍；如需看已停用請用狀態過濾器（未來擴充）
    ...(searchText && { q: searchText }),
    ...(roleFilter && { role: roleFilter }),
    ...(providerFilter && { auth_provider: providerFilter }),
  }), [currentPage, pageSize, searchText, roleFilter, providerFilter]);

  const { users, total, isLoading, refetch } = useAdminUsersPage(queryParams);
  const { columns } = useUserColumns(isMobile);

  // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce instance must be stable; users is captured in closure
  const handleAutoCompleteSearch = useMemo(
    () => debounce(async (searchValue: string) => {
      if (!searchValue || searchValue.length < 1) { setSearchOptions([]); return; }
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

  const handleCreate = useCallback(() => navigate(ROUTES.USER_CREATE), [navigate]);
  const handleRowClick = useCallback((user: User) => {
    navigate(ROUTES.USER_EDIT.replace(':id', String(user.id)));
  }, [navigate]);

  return (
    <div style={{ padding: pagePadding }}>
      <Card size={isMobile ? 'small' : undefined}>
        <div style={{ marginBottom: isMobile ? 12 : 24 }}>
          <Row justify="space-between" align={isMobile ? 'top' : 'middle'} gutter={[8, 8]}>
            <Col xs={24} sm={12}>
              <Title level={isMobile ? 4 : 3} style={{ margin: 0 }}>
                <TeamOutlined style={{ marginRight: 8 }} />使用者管理
              </Title>
            </Col>
            <Col xs={24} sm={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
              <Space>
                <Button
                  icon={<UserSwitchOutlined />}
                  size={isMobile ? 'small' : 'middle'}
                  onClick={() => setAliasDrawerOpen(true)}
                  title="ADR-0025 Identity Unification — 整合多種認證方式建立的同名分身"
                >
                  {isMobile ? '' : '認證整合'}
                </Button>
                <Button type="primary" icon={<PlusOutlined />} size={isMobile ? 'small' : 'middle'} onClick={handleCreate}>
                  {isMobile ? '' : '新增使用者'}
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <AutoComplete options={searchOptions} onSearch={handleAutoCompleteSearch} onSelect={(value) => setSearchText(value)} style={{ width: '100%' }}>
              <Input
                placeholder={isMobile ? '搜尋...' : '搜尋使用者名稱或電子郵件'}
                prefix={<SearchOutlined />} value={searchText}
                onChange={e => setSearchText(e.target.value)}
                onPressEnter={() => refetch()}
                size={isMobile ? 'small' : 'middle'} allowClear
              />
            </AutoComplete>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select placeholder={isMobile ? '角色' : '角色篩選'} allowClear value={roleFilter || undefined}
              onChange={setRoleFilter} style={{ width: '100%' }} size={isMobile ? 'small' : 'middle'}
            >
              {/* 位階排序：超級管理員 > 管理員 > 業務同仁 > 一般使用者 > 未驗證者 */}
              <Option value="superuser">超級管理員</Option>
              <Option value="admin">管理員</Option>
              <Option value="staff">業務同仁</Option>
              <Option value="user">一般使用者</Option>
              <Option value="unverified">未驗證者</Option>
            </Select>
          </Col>
          {!isMobile && (
            <Col sm={6} md={4}>
              <Select placeholder="認證方式" allowClear value={providerFilter || undefined}
                onChange={setProviderFilter} style={{ width: '100%' }}
              >
                <Option value="email">電子郵件</Option>
                <Option value="google">Google</Option>
                <Option value="line">LINE</Option>
                <Option value="internal">內網</Option>
              </Select>
            </Col>
          )}
          <Col xs={12} sm={6} md={4}>
            <Button type="primary" onClick={() => refetch()} size={isMobile ? 'small' : 'middle'}
              style={{ width: isMobile ? '100%' : 'auto' }}
            >
              搜尋
            </Button>
          </Col>
        </Row>

        <ResponsiveTable
          columns={columns} dataSource={users} loading={isLoading} rowKey="id"
          scroll={{ x: isMobile ? 400 : 800 }}
          mobileHiddenColumns={['auth_providers', 'created_at', 'last_login']}
          onChange={handleTableChange}
          onRow={(record) => ({ onClick: () => handleRowClick(record), style: { cursor: 'pointer' } })}
          pagination={{
            current: currentPage,
            pageSize: isMobile ? 10 : pageSize,
            total,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: isMobile ? undefined : (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
            onChange: (page, size) => { setCurrentPage(page); setPageSize(size || 20); },
            size: isMobile ? 'small' : undefined,
          }}
        />
      </Card>

      <AliasIntegrationDrawer
        open={aliasDrawerOpen}
        onClose={() => {
          setAliasDrawerOpen(false);
          refetch();
        }}
      />
    </div>
  );
};

export default UserManagementPage;
