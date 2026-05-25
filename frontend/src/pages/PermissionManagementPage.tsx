/**
 * 角色權限管理頁面 (ADR-0034 動態 SSOT，v4 視覺保留)
 *
 * 設計：
 * - 以角色為主體：表格 + 點 row 進入 /admin/permissions/:role 詳情編輯（導航模式）
 * - 動態資料源：從 DB role_permissions 表讀，不再 hardcode USER_ROLES
 * - 紅點 Alert：site_navigation_items 已配置但無 role 分派的 permissions（治理）
 * - 權限分類說明：底部橫幅 cards 維持 v4 設計
 *
 * @version 5.1.0 — ADR-0034 動態化 + 回歸 v4 導航模式（取代 v5 Drawer）
 * @date 2026-05-06
 */
import React, { useMemo, useState } from 'react';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card,
  Typography,
  Space,
  Button,
  Alert,
  Row,
  Col,
  Tag,
  Tooltip,
  Spin,
} from 'antd';
import {
  SecurityScanOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ReloadOutlined,
  DiffOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { ResponsiveTable } from '../components/common';

import {
  PERMISSION_CATEGORIES,
  groupPermissionsByCategory,
  getPermissionDisplayName,
} from '../constants/permissions';
import { ROUTES } from '../router/types';
import {
  useRolePermissionsList,
  useAvailablePermissions,
} from '../hooks/system/useRolePermissions';
import RolePermissionDiff from '../components/admin/RolePermissionDiff';

const { Title, Text, Paragraph } = Typography;

interface RoleRow {
  key: string;
  name_zh: string | null;
  description_zh: string | null;
  can_login: boolean;
  permissions: string[];
  permission_count: number;
  is_wildcard: boolean;
  icon: React.ReactNode;
  color: string;
}

const roleConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  superuser: { icon: <CrownOutlined />, color: 'gold' },
  admin: { icon: <SafetyCertificateOutlined />, color: 'blue' },
  staff: { icon: <UserOutlined />, color: 'cyan' },
  user: { icon: <UserOutlined />, color: 'green' },
  unverified: { icon: <UserOutlined />, color: 'default' },
};

// 角色位階排序：超級管理員 > 管理員 > 業務同仁 > 一般使用者 > 未驗證者
const ROLE_ORDER: Record<string, number> = {
  superuser: 0,
  admin: 1,
  staff: 2,
  user: 3,
  unverified: 4,
};

const PermissionManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: roleListData, isLoading, refetch } = useRolePermissionsList();
  const { data: availableData } = useAvailablePermissions();
  const [diffOpen, setDiffOpen] = useState(false);

  const rolesData: RoleRow[] = useMemo(() => {
    if (!roleListData?.items) return [];
    return roleListData.items
      .map((r) => ({
        key: r.role,
        name_zh: r.name_zh,
        description_zh: r.description_zh,
        can_login: r.can_login,
        permissions: r.permissions,
        permission_count: r.permission_count,
        is_wildcard: r.is_wildcard,
        icon: roleConfig[r.role]?.icon || <UserOutlined />,
        color: roleConfig[r.role]?.color || 'default',
      }))
      .sort((a, b) => (ROLE_ORDER[a.key] ?? 99) - (ROLE_ORDER[b.key] ?? 99));
  }, [roleListData]);

  const unassignedCount = availableData?.unassigned_count || 0;
  const unassignedList = availableData?.unassigned || [];

  const totalCategories = Object.keys(PERMISSION_CATEGORIES).length;
  const getCategoryCount = (perms: string[]) => {
    if (perms.includes('*')) return totalCategories;
    return Object.keys(groupPermissionsByCategory(perms)).length;
  };

  const columns: ColumnsType<RoleRow> = [
    {
      title: '角色',
      key: 'role',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tag icon={record.icon} color={record.color} style={{ fontSize: 14, padding: '4px 12px' }}>
            {record.name_zh || record.key}
          </Tag>
          {record.is_wildcard && <Tag color="gold">Wildcard</Tag>}
        </Space>
      ),
    },
    {
      title: '說明',
      dataIndex: 'description_zh',
      key: 'description',
      width: 280,
      ellipsis: true,
      render: (text: string | null) => <Text type="secondary">{text || '—'}</Text>,
    },
    {
      title: '權限摘要',
      key: 'permissions',
      width: 220,
      render: (_, record) => {
        if (record.is_wildcard) {
          return (
            <Tooltip title="Wildcard：含系統所有權限">
              <Text style={{ cursor: 'help' }}>
                <InfoCircleOutlined style={{ marginRight: 4, color: '#faad14' }} />
                所有權限 ({totalCategories} 個分類)
              </Text>
            </Tooltip>
          );
        }
        const catCount = getCategoryCount(record.permissions);
        return (
          <Tooltip
            title={
              record.permission_count > 0 ? (
                <div style={{ maxHeight: 300, overflow: 'auto' }}>
                  {record.permissions.map((p) => (
                    <div key={p} style={{ fontSize: 12 }}>{getPermissionDisplayName(p)}</div>
                  ))}
                </div>
              ) : '此角色無任何權限'
            }
          >
            <Text style={{ cursor: 'help' }}>
              <InfoCircleOutlined style={{ marginRight: 4, color: '#1890ff' }} />
              {record.permission_count} 個權限 ({catCount}/{totalCategories} 個分類)
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: '狀態',
      key: 'status',
      width: 120,
      align: 'center' as const,
      render: (_, record) =>
        record.can_login ? (
          <Tag icon={<CheckCircleOutlined />} color="success">可登入</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">禁止登入</Tag>
        ),
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card>
        <div style={{ marginBottom: 24 }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <SecurityScanOutlined style={{ marginRight: 8 }} />
                角色權限管理
              </Title>
              <Text type="secondary">
                ADR-0034 動態 SSOT — 以 DB 為單一真實來源，與 site-management 動態對應
              </Text>
            </Col>
            <Col>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                  重新整理
                </Button>
                <Button icon={<DiffOutlined />} onClick={() => setDiffOpen(true)}>
                  角色差異比較
                </Button>
                <Button type="primary" icon={<TeamOutlined />} onClick={() => navigate(ROUTES.USER_MANAGEMENT)}>
                  使用者管理
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {unassignedCount > 0 && (
          <Alert
            type="warning"
            showIcon
            icon={<WarningOutlined />}
            message={`偵測到 ${unassignedCount} 個 permission 已被 site-management 配置但未分派給任何 role`}
            description={
              <div>
                <Paragraph style={{ margin: 0 }}>
                  下列權限存在於 <Text code>site_navigation_items.permission_required</Text> 但所有 role 都沒被分派 —
                  使用者將無法看到對應選單。請點選對應 role 編輯：
                </Paragraph>
                <Space wrap style={{ marginTop: 8 }}>
                  {unassignedList.map((p) => (
                    <Tag key={p} color="orange">{p}</Tag>
                  ))}
                </Space>
              </div>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        <Alert
          message="角色權限說明"
          description={
            <Space direction="vertical" size={4}>
              <Text>
                系統採用「角色基礎存取控制」(RBAC) 機制。<Text strong>superuser</Text> 為 wildcard 不可編輯，
                其他角色 (<Text strong>admin / staff / user</Text>) 可由介面動態配置。
              </Text>
              <Text type="secondary">
                點擊角色列即可進入詳情頁編輯權限。如需調整個別使用者權限，請至「使用者管理」頁面。
              </Text>
            </Space>
          }
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Spin spinning={isLoading}>
          <ResponsiveTable
            columns={columns}
            dataSource={rolesData}
            rowKey="key"
            pagination={false}
            scroll={{ x: 600 }}
            mobileHiddenColumns={['description', 'status']}
            onRow={(record) => ({
              onClick: () => navigate(`${ROUTES.PERMISSION_MANAGEMENT}/${record.key}`),
              style: { cursor: 'pointer' },
            })}
          />
        </Spin>

        <div style={{ marginTop: 24 }}>
          <Title level={4}>權限分類說明</Title>
          <Row gutter={[16, 16]}>
            {Object.entries(PERMISSION_CATEGORIES).map(([key, category]) => (
              <Col xs={24} sm={12} lg={8} key={key}>
                <Card size="small" style={{ height: '100%' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>{category.name_zh}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {category.permissions.length} 個權限項目
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </Card>

      <RolePermissionDiff
        open={diffOpen}
        onClose={() => setDiffOpen(false)}
        defaultRoleA="admin"
      />
    </ResponsiveContent>
  );
};

export default PermissionManagementPage;
