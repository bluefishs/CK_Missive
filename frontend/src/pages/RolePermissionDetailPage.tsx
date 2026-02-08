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
  Spin,
  App
} from 'antd';
import {
  ArrowLeftOutlined,
  SecurityScanOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  SaveOutlined
} from '@ant-design/icons';

import PermissionManager from '../components/admin/PermissionManager';
import {
  USER_ROLES,
  getRoleDefaultPermissions
} from '../constants/permissions';
import { ROUTES } from '../router/types';

const { Title, Text } = Typography;

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

  // 儲存權限（目前為前端常數，實際應連接後端 API）
  const handleSave = async () => {
    setSaving(true);
    try {
      // TODO: 當後端支援角色權限管理 API 時，在此呼叫 API
      // await rolePermissionsApi.updateRolePermissions(role, permissions);

      message.info('角色預設權限目前由系統設定檔定義，如需調整請聯繫系統管理員');
      setHasChanges(false);
    } catch (error) {
      message.error('儲存失敗');
    } finally {
      setSaving(false);
    }
  };

  // 返回列表
  const handleBack = () => {
    navigate(ROUTES.PERMISSION_MANAGEMENT);
  };

  // 角色不存在
  if (!roleInfo) {
    return (
      <ResponsiveContent maxWidth="full" padding="medium">
        <Card>
          <Alert
            message="角色不存在"
            description={`找不到角色「${role}」的權限設定`}
            type="error"
            showIcon
          />
          <Button
            type="primary"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            style={{ marginTop: 16 }}
          >
            返回角色列表
          </Button>
        </Card>
      </ResponsiveContent>
    );
  }

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card>
        {/* 標題區 */}
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Space direction="vertical" size={4}>
                <Button
                  type="link"
                  icon={<ArrowLeftOutlined />}
                  onClick={handleBack}
                  style={{ padding: 0, height: 'auto' }}
                >
                  返回角色列表
                </Button>
                <Title level={3} style={{ margin: 0 }}>
                  <SecurityScanOutlined style={{ marginRight: '8px' }} />
                  詳細權限設定
                  <Tag
                    icon={roleInfo.icon}
                    color={roleInfo.color}
                    style={{ marginLeft: 12, fontSize: 14, padding: '4px 12px' }}
                  >
                    {roleInfo.name_zh}
                  </Tag>
                </Title>
                <Text type="secondary">{roleInfo.description_zh}</Text>
              </Space>
            </Col>
            <Col>
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
            </Col>
          </Row>
        </div>

        {/* 說明提示 */}
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

        {/* 權限管理元件 */}
        <PermissionManager
          userPermissions={permissions}
          onPermissionChange={handlePermissionChange}
          readOnly={false}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default RolePermissionDetailPage;
