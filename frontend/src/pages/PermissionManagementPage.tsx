/**
 * 權限管理頁面
 *
 * 功能：
 * - 顯示角色與權限的矩陣對照
 * - 顯示系統中所有可用權限（分類顯示）
 * - 使用真實 API: /admin/user-management/permissions/available
 *
 * @version 3.0.0 - 新增角色-權限矩陣視圖
 * @date 2026-01-26
 */

import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Typography, Space, Alert, Row, Col, Table, Tag, Collapse, List, Spin,
  Button, Checkbox, Tabs, Tooltip
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SecurityScanOutlined, TeamOutlined, CheckCircleOutlined,
  FileTextOutlined, ProjectOutlined, BankOutlined, ShopOutlined,
  SettingOutlined, BarChartOutlined, CalendarOutlined, BellOutlined,
  UserOutlined, TableOutlined, AppstoreOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { adminUsersApi } from '../api/adminUsersApi';
import { ROUTES } from '../router/types';

const { Title, Text } = Typography;

// 權限分類定義
const PERMISSION_CATEGORIES: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
  permissions: string[];
}> = {
  documents: {
    label: '公文管理',
    icon: <FileTextOutlined />,
    color: 'blue',
    permissions: ['documents:read', 'documents:create', 'documents:edit', 'documents:delete', 'documents:export'],
  },
  projects: {
    label: '承攬案件',
    icon: <ProjectOutlined />,
    color: 'green',
    permissions: ['projects:read', 'projects:create', 'projects:edit', 'projects:delete'],
  },
  agencies: {
    label: '機關單位',
    icon: <BankOutlined />,
    color: 'purple',
    permissions: ['agencies:read', 'agencies:create', 'agencies:edit', 'agencies:delete'],
  },
  vendors: {
    label: '廠商管理',
    icon: <ShopOutlined />,
    color: 'orange',
    permissions: ['vendors:read', 'vendors:create', 'vendors:edit', 'vendors:delete'],
  },
  admin: {
    label: '系統管理',
    icon: <SettingOutlined />,
    color: 'red',
    permissions: ['admin:users', 'admin:settings', 'admin:database', 'admin:site_management'],
  },
  reports: {
    label: '報表功能',
    icon: <BarChartOutlined />,
    color: 'cyan',
    permissions: ['reports:view', 'reports:export'],
  },
  calendar: {
    label: '行事曆',
    icon: <CalendarOutlined />,
    color: 'gold',
    permissions: ['calendar:read', 'calendar:edit'],
  },
  notifications: {
    label: '通知',
    icon: <BellOutlined />,
    color: 'magenta',
    permissions: ['notifications:read'],
  },
};

// 權限顯示名稱
const PERMISSION_LABELS: Record<string, string> = {
  'documents:read': '檢視公文',
  'documents:create': '建立公文',
  'documents:edit': '編輯公文',
  'documents:delete': '刪除公文',
  'documents:export': '匯出公文',
  'projects:read': '檢視案件',
  'projects:create': '建立案件',
  'projects:edit': '編輯案件',
  'projects:delete': '刪除案件',
  'agencies:read': '檢視機關',
  'agencies:create': '建立機關',
  'agencies:edit': '編輯機關',
  'agencies:delete': '刪除機關',
  'vendors:read': '檢視廠商',
  'vendors:create': '建立廠商',
  'vendors:edit': '編輯廠商',
  'vendors:delete': '刪除廠商',
  'admin:users': '使用者管理',
  'admin:settings': '系統設定',
  'admin:database': '資料庫管理',
  'admin:site_management': '網站管理',
  'reports:view': '檢視報表',
  'reports:export': '匯出報表',
  'calendar:read': '檢視行事曆',
  'calendar:edit': '編輯行事曆',
  'notifications:read': '檢視通知',
};

interface RoleData {
  name: string;
  display_name: string;
  default_permissions: string[];
}

const PermissionManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('matrix');

  // 從 API 載入權限與角色資料
  const { data, isLoading, error } = useQuery({
    queryKey: ['availablePermissions'],
    queryFn: () => adminUsersApi.getAvailablePermissions(),
  });

  const permissions = data?.permissions || [];
  const roles: RoleData[] = data?.roles || [];

  // 將權限按分類整理
  const categorizedPermissions = useMemo(() => {
    const result: Record<string, string[]> = {};

    for (const [category, config] of Object.entries(PERMISSION_CATEGORIES)) {
      result[category] = config.permissions.filter(p => permissions.includes(p));
    }

    return result;
  }, [permissions]);

  // 檢查角色是否擁有某權限
  const roleHasPermission = (role: RoleData, permission: string): boolean => {
    if (role.default_permissions.includes('*')) return true;
    return role.default_permissions.includes(permission);
  };

  // 角色-權限矩陣表格欄位
  const matrixColumns: ColumnsType<{ permission: string; category: string }> = useMemo(() => {
    const cols: ColumnsType<{ permission: string; category: string }> = [
      {
        title: '權限分類',
        dataIndex: 'category',
        key: 'category',
        width: 120,
        fixed: 'left',
        render: (category: string) => {
          const config = PERMISSION_CATEGORIES[category];
          return config ? (
            <Tag color={config.color} icon={config.icon}>
              {config.label}
            </Tag>
          ) : category;
        },
      },
      {
        title: '權限名稱',
        dataIndex: 'permission',
        key: 'permission',
        width: 150,
        fixed: 'left',
        render: (permission: string) => (
          <Tooltip title={permission}>
            <Text>{PERMISSION_LABELS[permission] || permission}</Text>
          </Tooltip>
        ),
      },
    ];

    // 為每個角色添加一列
    roles.forEach((role) => {
      cols.push({
        title: (
          <Tooltip title={role.name}>
            <Space direction="vertical" size={0} style={{ textAlign: 'center' }}>
              <Text strong>{role.display_name}</Text>
              {role.default_permissions.includes('*') && (
                <Tag color="red" style={{ fontSize: 10 }}>全權限</Tag>
              )}
            </Space>
          </Tooltip>
        ),
        key: role.name,
        width: 100,
        align: 'center' as const,
        render: (_: unknown, record: { permission: string }) => {
          const hasPermission = roleHasPermission(role, record.permission);
          return (
            <Checkbox
              checked={hasPermission}
              disabled
              style={{
                pointerEvents: 'none',
              }}
            />
          );
        },
      });
    });

    return cols;
  }, [roles]);

  // 矩陣表格資料
  const matrixData = useMemo(() => {
    const data: { permission: string; category: string; key: string }[] = [];

    Object.entries(PERMISSION_CATEGORIES).forEach(([category, config]) => {
      config.permissions.forEach((permission) => {
        if (permissions.includes(permission)) {
          data.push({
            key: permission,
            permission,
            category,
          });
        }
      });
    });

    return data;
  }, [permissions]);

  // 角色表格欄位（傳統視圖）
  const roleColumns = [
    {
      title: '角色名稱',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: RoleData) => (
        <Space>
          <UserOutlined />
          <Text strong>{text}</Text>
          <Text type="secondary">({record.name})</Text>
        </Space>
      ),
    },
    {
      title: '預設權限數量',
      dataIndex: 'default_permissions',
      key: 'permission_count',
      render: (perms: string[]) => {
        if (perms.includes('*')) {
          return <Tag color="red">所有權限</Tag>;
        }
        return <Tag color="blue">{perms.length} 個權限</Tag>;
      },
    },
    {
      title: '預設權限',
      dataIndex: 'default_permissions',
      key: 'permissions',
      render: (perms: string[]) => {
        if (perms.includes('*')) {
          return <Text type="secondary">擁有系統所有權限</Text>;
        }
        if (perms.length === 0) {
          return <Text type="secondary">無預設權限</Text>;
        }
        return (
          <Space wrap size={[4, 4]}>
            {perms.slice(0, 6).map(p => (
              <Tag key={p} color="default">{PERMISSION_LABELS[p] || p}</Tag>
            ))}
            {perms.length > 6 && (
              <Tag color="default">+{perms.length - 6} 更多</Tag>
            )}
          </Space>
        );
      },
    },
  ];

  if (isLoading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" tip="載入權限資料中..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          type="error"
          message="載入失敗"
          description="無法載入權限資料，請稍後再試或聯繫系統管理員。"
          showIcon
        />
      </div>
    );
  }

  const tabItems = [
    {
      key: 'matrix',
      label: (
        <Space>
          <TableOutlined />
          矩陣視圖
        </Space>
      ),
      children: (
        <div>
          <Alert
            message="角色-權限對照表"
            description="此矩陣顯示各角色的預設權限配置。勾選表示該角色擁有該權限。如需修改個別使用者權限，請至「使用者管理」頁面。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            columns={matrixColumns}
            dataSource={matrixData}
            rowKey="key"
            pagination={false}
            size="small"
            bordered
            scroll={{ x: 'max-content' }}
            sticky
          />
        </div>
      ),
    },
    {
      key: 'roles',
      label: (
        <Space>
          <TeamOutlined />
          角色列表
        </Space>
      ),
      children: (
        <div>
          <Title level={4}>
            <TeamOutlined style={{ marginRight: 8 }} />
            角色定義 ({roles.length} 個角色)
          </Title>
          <Table
            columns={roleColumns}
            dataSource={roles}
            rowKey="name"
            pagination={false}
            size="middle"
          />
        </div>
      ),
    },
    {
      key: 'permissions',
      label: (
        <Space>
          <AppstoreOutlined />
          權限分類
        </Space>
      ),
      children: (
        <div>
          <Title level={4}>
            <CheckCircleOutlined style={{ marginRight: 8 }} />
            權限分類 (共 {permissions.length} 個權限)
          </Title>
          <Collapse
            defaultActiveKey={['documents', 'projects']}
            items={Object.entries(PERMISSION_CATEGORIES).map(([key, config]) => ({
              key,
              label: (
                <Space>
                  {config.icon}
                  <Text strong>{config.label}</Text>
                  <Tag color={config.color}>{categorizedPermissions[key]?.length || 0} 個權限</Tag>
                </Space>
              ),
              children: (
                <List
                  size="small"
                  dataSource={categorizedPermissions[key] || []}
                  renderItem={(permission: string) => (
                    <List.Item>
                      <Space>
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        <Text>{PERMISSION_LABELS[permission] || permission}</Text>
                        <Text type="secondary" code>{permission}</Text>
                      </Space>
                    </List.Item>
                  )}
                  locale={{ emptyText: '此分類沒有權限' }}
                />
              ),
            }))}
          />
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ marginBottom: 24 }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <SecurityScanOutlined style={{ marginRight: 8 }} />
                權限管理中心
              </Title>
              <Text type="secondary">
                檢視系統角色與權限的對應關係
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

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>
    </div>
  );
};

export default PermissionManagementPage;
