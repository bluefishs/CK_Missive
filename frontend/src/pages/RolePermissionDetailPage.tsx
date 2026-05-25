/**
 * 角色權限詳情頁面 (ADR-0034 動態 SSOT)
 *
 * 功能：
 * - 顯示指定角色的詳細權限設定（從 DB role_permissions 動態載入）
 * - 使用 PermissionManager 元件進行權限編輯（保留 v4 視覺）
 * - 儲存呼叫動態 update endpoint，含 audit log
 * - superuser wildcard 保護：唯讀模式 + 警告
 * - 紅點提示：未被任何 role 分派的 permissions
 *
 * @version 2.0.0 — ADR-0034 動態化（取代 USER_ROLES hardcode）
 * @date 2026-05-06
 */
import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Space,
  Button,
  Alert,
  Typography,
  App,
  Tag,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  SecurityScanOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  SaveOutlined,
  WarningOutlined,
  TeamOutlined,
} from '@ant-design/icons';

import { DetailPageLayout, createTabItem } from '../components/common/DetailPage';
import PermissionManager from '../components/admin/PermissionManager';
import { ROUTES } from '../router/types';
import {
  useRolePermissionsDetail,
  useAvailablePermissions,
  useUpdateRolePermissions,
  useSyncRoleUsers,
  useNavTree,
} from '../hooks/system/useRolePermissions';
import NavTreePermissionEditor from '../components/admin/NavTreePermissionEditor';

const { Text, Paragraph } = Typography;

const roleConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  superuser: { icon: <CrownOutlined />, color: 'gold' },
  admin: { icon: <SafetyCertificateOutlined />, color: 'blue' },
  staff: { icon: <UserOutlined />, color: 'cyan' },
  user: { icon: <UserOutlined />, color: 'green' },
  unverified: { icon: <UserOutlined />, color: 'default' },
};

const RolePermissionDetailPage: React.FC = () => {
  const { role } = useParams<{ role: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const { data: detailData, isLoading } = useRolePermissionsDetail(role);
  const { data: availableData } = useAvailablePermissions();
  const updateMutation = useUpdateRolePermissions();
  const syncUsersMutation = useSyncRoleUsers();
  const { data: navTreeData, isLoading: navTreeLoading, refetch: refetchNavTree } = useNavTree(role);

  const [permissions, setPermissions] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  const roleData = detailData?.role;
  const isWildcard = roleData?.is_wildcard ?? false;

  const roleInfo = useMemo(() => {
    if (!roleData) return null;
    return {
      key: roleData.role,
      name_zh: roleData.name_zh || roleData.role,
      description_zh: roleData.description_zh,
      can_login: roleData.can_login,
      default_permissions: roleData.permissions,
      icon: roleConfig[roleData.role]?.icon || <UserOutlined />,
      color: roleConfig[roleData.role]?.color || 'default',
    };
  }, [roleData]);

  useEffect(() => {
    if (roleData) {
      setPermissions(roleData.permissions);
      setHasChanges(false);
    }
  }, [roleData]);

  const handlePermissionChange = (newPermissions: string[]) => {
    setPermissions(newPermissions);
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!role) return;
    try {
      await updateMutation.mutateAsync({ role, permissions });
      message.success(`已更新 ${roleInfo?.name_zh}（${permissions.length} 個權限）`);
      setHasChanges(false);
    } catch (error) {
      message.error('儲存失敗：' + (error instanceof Error ? error.message : '未知錯誤'));
    }
  };

  /** NavTree v1.2：直接接收完整新 draft（已處理父子級聯 + 保留 nav 外 perm） */
  const handleNavTreeDraftChange = (newDraft: string[]) => {
    setPermissions(newDraft);
    setHasChanges(true);
  };

  const handleBack = () => {
    navigate(ROUTES.PERMISSION_MANAGEMENT);
  };

  const unassignedCount = availableData?.unassigned_count || 0;
  const unassignedList = availableData?.unassigned || [];

  const sharedAlertSection = roleInfo ? (
    <>
      {isWildcard && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="superuser 為 Wildcard 角色（系統保護）"
          description="superuser 自動具備所有權限，不可由介面修改。如需調整管理範圍，請編輯 admin role。"
          style={{ marginBottom: 16 }}
        />
      )}

      {!isWildcard && unassignedCount > 0 && (
        <Alert
          type="info"
          showIcon
          message={`系統內有 ${unassignedCount} 個 permission 未被任何 role 分派`}
          description={
            <div>
              <Paragraph style={{ margin: 0 }}>
                若該權限應屬本角色，請於下方勾選後儲存。
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
    </>
  ) : null;

  const tabs = [
    // Tab 1：依選單階層編輯（推薦，與 site-management 結構對齊）
    createTabItem(
      'nav-tree',
      { icon: <SecurityScanOutlined />, text: '依選單階層' },
      roleInfo ? (
        <>
          {sharedAlertSection}
          <Alert
            message="依選單階層編輯（與 site-management 動態對應）"
            description={
              <Space direction="vertical" size={4}>
                <Text>
                  此 Tab 以 <Text code>site_navigation_items</Text> 階層展示，與
                  <Text code>/admin/site-management</Text> 結構同步。每個節點對應一個或多個 permission；
                  勾選即把該 permission 加入「{roleInfo.name_zh}」role。
                </Text>
                <Text type="secondary">
                  共用同 permission 的多個選單會同時切換（如「平臺資訊 / 知識地圖 / AI助理」共用 admin:settings）。
                </Text>
              </Space>
            }
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
          <NavTreePermissionEditor
            data={navTreeData}
            isLoading={navTreeLoading}
            draftPermissions={permissions}
            onDraftChange={handleNavTreeDraftChange}
            onRefetch={() => refetchNavTree()}
            readOnly={isWildcard}
          />
        </>
      ) : null
    ),
    // Tab 2：依權限分類編輯（傳統視角，by category）
    createTabItem(
      'by-category',
      { icon: <SecurityScanOutlined />, text: '依權限分類' },
      roleInfo ? (
        <>
          {sharedAlertSection}
          <Alert
            message="依權限分類編輯（傳統 PERMISSION_CATEGORIES 視角）"
            description={
              <Text type="secondary">
                此 Tab 按權限分類（公文/專案/機關/廠商/...）展示。若新權限不在 PERMISSION_CATEGORIES 內，請改用「依選單階層」Tab。
              </Text>
            }
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
          <PermissionManager
            userPermissions={permissions}
            onPermissionChange={handlePermissionChange}
            readOnly={isWildcard}
          />
        </>
      ) : null
    ),
  ];

  const handleSyncUsers = async () => {
    if (!role || isWildcard) return;
    try {
      const result = await syncUsersMutation.mutateAsync({ role, onlyOutdated: true });
      message.success(result.message);
    } catch (e) {
      message.error('同步失敗：' + (e instanceof Error ? e.message : '未知錯誤'));
    }
  };

  const headerExtra = roleInfo ? (
    <Space>
      {!isWildcard && (
        <Popconfirm
          title={`同步 '${roleInfo.name_zh}' 角色所有 user 的權限？`}
          description={
            <span>
              將該 role 的所有 active user 之 <code>user.permissions</code> 同步為當前 role 配置。<br/>
              已對齊的 user 會略過。建議在儲存 role 變更後執行。
            </span>
          }
          onConfirm={handleSyncUsers}
          okText="確認同步"
          cancelText="取消"
          disabled={hasChanges}
        >
          <Tooltip title={hasChanges ? '請先儲存變更' : '把當前 role 配置同步給所有 active user'}>
            <Button
              icon={<TeamOutlined />}
              loading={syncUsersMutation.isPending}
              disabled={hasChanges || isWildcard}
            >
              同步至所有用戶
            </Button>
          </Tooltip>
        </Popconfirm>
      )}
      <Button onClick={handleBack}>取消</Button>
      <Button
        type="primary"
        icon={<SaveOutlined />}
        onClick={handleSave}
        loading={updateMutation.isPending}
        disabled={!hasChanges || isWildcard}
      >
        儲存（{permissions.length}）
      </Button>
    </Space>
  ) : undefined;

  return (
    <DetailPageLayout
      header={{
        title: `${roleInfo?.name_zh ?? role ?? ''} 詳細權限設定`,
        subtitle: roleInfo?.description_zh ?? undefined,
        icon: <SecurityScanOutlined />,
        tags: roleInfo
          ? [
              { text: roleInfo.name_zh, color: roleInfo.color },
              ...(isWildcard ? [{ text: 'Wildcard *', color: 'gold' }] : []),
            ]
          : [],
        backText: '返回角色列表',
        backPath: ROUTES.PERMISSION_MANAGEMENT,
        extra: headerExtra,
      }}
      tabs={tabs}
      hasData={!!roleInfo}
      loading={isLoading}
    />
  );
};

export default RolePermissionDetailPage;
