/**
 * 角色權限詳情頁面
 *
 * 功能：
 * - 顯示指定角色的詳細權限設定
 * - 使用 PermissionManager 元件進行權限編輯
 * - 支援儲存角色預設權限配置
 *
 * @version 1.0.0
 * @date 2026-02-02
 */
import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Space,
  Button,
  Alert,
  Typography,
  App
} from 'antd';
import {
  SecurityScanOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  SaveOutlined
} from '@ant-design/icons';

import { DetailPageLayout, createTabItem } from '../components/common/DetailPage';
import PermissionManager from '../components/admin/PermissionManager';
import {
  USER_ROLES,
} from '../constants/permissions';
import { ROUTES } from '../router/types';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';

const { Text } = Typography;

// 角色圖示與顏色配置
const roleConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  superuser: { icon: <CrownOutlined />, color: 'gold' },
  admin: { icon: <SafetyCertificateOutlined />, color: 'blue' },
  user: { icon: <UserOutlined />, color: 'green' },
  unverified: { icon: <UserOutlined />, color: 'default' },
};

const RolePermissionDetailPage: React.FC = () => {
  const { role } = useParams<{ role: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [permissions, setPermissions] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  // 取得角色資訊
  const roleInfo = useMemo(() => {
    if (!role) return null;
    const info = USER_ROLES[role as keyof typeof USER_ROLES];
    if (!info) return null;

    return {
      key: role,
      name_zh: info.name_zh,
      name_en: info.name_en,
      description_zh: info.description_zh,
      can_login: info.can_login,
      default_permissions: info.default_permissions,
      icon: roleConfig[role]?.icon || <UserOutlined />,
      color: roleConfig[role]?.color || 'default',
    };
  }, [role]);

  // 初始化權限
  useEffect(() => {
    if (roleInfo) {
      setPermissions(roleInfo.default_permissions);
      setHasChanges(false);
    }
  }, [roleInfo]);

  // 處理權限變更
  const handlePermissionChange = (newPermissions: string[]) => {
    setPermissions(newPermissions);
    setHasChanges(true);
  };

  // 儲存權限至後端
  const handleSave = async () => {
    if (!role) return;
    setSaving(true);
    try {
      await apiClient.post(
        API_ENDPOINTS.ADMIN_USER_MANAGEMENT.ROLE_PERMISSIONS_UPDATE(role),
        { permissions }
      );
      message.success('角色權限已更新');
      setHasChanges(false);
    } catch (error) {
      message.error('儲存失敗，請確認您具有管理員權限');
    } finally {
      setSaving(false);
    }
  };

  // 返回列表
  const handleBack = () => {
    navigate(ROUTES.PERMISSION_MANAGEMENT);
  };

  const tabs = [
    createTabItem(
      'permissions',
      { icon: <SecurityScanOutlined />, text: '權限設定' },
      roleInfo ? (
        <>
          <Alert
            message="權限設定說明"
            description={
              <Space direction="vertical" size={4}>
                <Text>
                  此頁面顯示「{roleInfo.name_zh}」角色的預設權限配置。
                </Text>
                <Text type="secondary">
                  勾選權限項目可調整該角色的預設權限。目前角色權限由系統設定檔定義。
                </Text>
              </Space>
            }
            type="info"
            showIcon
            style={{ marginBottom: '24px' }}
          />
          <PermissionManager
            userPermissions={permissions}
            onPermissionChange={handlePermissionChange}
            readOnly={false}
          />
        </>
      ) : null
    ),
  ];

  const headerExtra = roleInfo ? (
    <Space>
      <Button onClick={handleBack}>
        取消
      </Button>
      <Button
        type="primary"
        icon={<SaveOutlined />}
        onClick={handleSave}
        loading={saving}
        disabled={!hasChanges}
      >
        儲存
      </Button>
    </Space>
  ) : undefined;

  return (
    <DetailPageLayout
      header={{
        title: `${roleInfo?.name_zh ?? role ?? ''} 詳細權限設定`,
        subtitle: roleInfo?.description_zh,
        icon: <SecurityScanOutlined />,
        tags: roleInfo ? [{ text: roleInfo.name_zh, color: roleInfo.color }] : [],
        backText: '返回角色列表',
        backPath: ROUTES.PERMISSION_MANAGEMENT,
        extra: headerExtra,
      }}
      tabs={tabs}
      hasData={!!roleInfo}
    />
  );
};

export default RolePermissionDetailPage;
