/**
 * 角色權限管理頁面
 *
 * 功能：
 * - 以角色為主體顯示權限配置
 * - 提供權限分類摘要視圖
 * - 採用導航模式進行權限編輯
 *
 * @version 4.0.0 - 重構為角色為主體，採用導航模式
 * @date 2026-02-02
 */
import React, { useMemo } from 'react';
import { ResponsiveContent } from '../components/common';
import {
  Card,
  Typography,
  Space,
  Button,
  Alert,
  Row,
  Col,
  Tag,
  Tooltip
} from 'antd';
import {
  SecurityScanOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { ResponsiveTable } from '../components/common';

import {
  PERMISSION_CATEGORIES,
  USER_ROLES,
  ALL_PERMISSIONS,
  groupPermissionsByCategory,
  getPermissionDisplayName
} from '../constants/permissions';
import { ROUTES } from '../router/types';

const { Title, Text } = Typography;

// 角色資料型別
interface RoleData {
  key: string;
  name_zh: string;
  description_zh: string;
  can_login: boolean;
  default_permissions: string[];
  permissionCount: number;
  categoryCount: number;
  icon: React.ReactNode;
  color: string;
}

const PermissionManagementPage: React.FC = () => {
  const navigate = useNavigate();

  // 角色圖示與顏色配置
  const roleConfig: Record<string, { icon: React.ReactNode; color: string }> = {
    superuser: { icon: <CrownOutlined />, color: 'gold' },
    admin: { icon: <SafetyCertificateOutlined />, color: 'blue' },
    user: { icon: <UserOutlined />, color: 'green' },
    unverified: { icon: <UserOutlined />, color: 'default' },
  };

  // 整理角色資料
  const rolesData: RoleData[] = useMemo(() => {
    return Object.entries(USER_ROLES).map(([key, role]) => {
      const permissions = role.default_permissions;
      const grouped = groupPermissionsByCategory(permissions);
      const categoryCount = Object.keys(grouped).length;

      return {
        key,
        name_zh: role.name_zh,
        description_zh: role.description_zh,
        can_login: role.can_login,
        default_permissions: permissions,
        permissionCount: permissions.length,
        categoryCount,
        icon: roleConfig[key]?.icon || <UserOutlined />,
        color: roleConfig[key]?.color || 'default',
      };
    });
  }, []);

  // 取得權限摘要文字
  const getPermissionSummary = (role: RoleData) => {
    const totalCategories = Object.keys(PERMISSION_CATEGORIES).length;
    return `${role.permissionCount} 個權限 (${role.categoryCount}/${totalCategories} 個分類)`;
  };

  // 表格欄位定義
  const columns: ColumnsType<RoleData> = [
    {
      title: '角色',
      key: 'role',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tag icon={record.icon} color={record.color} style={{ fontSize: 14, padding: '4px 12px' }}>
            {record.name_zh}
          </Tag>
        </Space>
      ),
    },
    {
      title: '說明',
      dataIndex: 'description_zh',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Text type="secondary">{text}</Text>
      ),
    },
    {
      title: '權限摘要',
      key: 'permissions',
      width: 200,
      render: (_, record) => (
        <Tooltip
          title={
            record.permissionCount > 0 ? (
              <div style={{ maxHeight: 300, overflow: 'auto' }}>
                {record.default_permissions.map(p => (
                  <div key={p} style={{ fontSize: 12 }}>{getPermissionDisplayName(p)}</div>
                ))}
              </div>
            ) : '此角色無任何權限'
          }
        >
          <Text style={{ cursor: 'help' }}>
            <InfoCircleOutlined style={{ marginRight: 4, color: '#1890ff' }} />
            {getPermissionSummary(record)}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '狀態',
      key: 'status',
      width: 120,
      align: 'center' as const,
      render: (_, record) => (
        <Space>
          {record.can_login ? (
            <Tag icon={<CheckCircleOutlined />} color="success">可登入</Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="error">禁止登入</Tag>
          )}
        </Space>
      ),
    },
  ];

  // 展開行：顯示權限詳情
  const expandedRowRender = (record: RoleData) => {
    if (record.permissionCount === 0) {
      return (
        <div style={{ padding: '16px 24px', background: '#fafafa' }}>
          <Text type="secondary">此角色無任何預設權限</Text>
        </div>
      );
    }

    const grouped = groupPermissionsByCategory(record.default_permissions);

    return (
      <div style={{ padding: '16px 24px', background: '#fafafa' }}>
        <Row gutter={[16, 16]}>
          {Object.entries(grouped).map(([category, permissions]) => (
            <Col xs={24} sm={12} md={8} lg={6} key={category}>
              <Card size="small" title={PERMISSION_CATEGORIES[category]?.name_zh || category}>
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  {permissions.map(p => (
                    <Text key={p.key} style={{ fontSize: 12 }}>
                      • {p.name_zh}
                    </Text>
                  ))}
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card>
        {/* 標題區 */}
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <SecurityScanOutlined style={{ marginRight: '8px' }} />
                角色權限管理
              </Title>
              <Text type="secondary">
                管理系統角色及其預設權限配置
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

        {/* 說明提示 */}
        <Alert
          message="角色權限說明"
          description={
            <Space direction="vertical" size={4}>
              <Text>
                系統採用「角色基礎存取控制」(RBAC) 機制，每個角色具有預設權限配置。
              </Text>
              <Text type="secondary">
                點擊展開按鈕可查看各角色的詳細權限清單。如需調整個別使用者權限，請至「使用者管理」頁面編輯。
              </Text>
            </Space>
          }
          type="info"
          showIcon
          style={{ marginBottom: '24px' }}
        />

        {/* 角色列表 */}
        <ResponsiveTable
          columns={columns}
          dataSource={rolesData}
          rowKey="key"
          pagination={false}
          scroll={{ x: 600 }}
          mobileHiddenColumns={['description', 'status']}
          expandable={{
            expandedRowRender,
            rowExpandable: () => true,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`${ROUTES.PERMISSION_MANAGEMENT}/${record.key}`),
            style: { cursor: 'pointer' },
          })}
        />

        {/* 權限分類說明 */}
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
    </ResponsiveContent>
  );
};

export default PermissionManagementPage;
