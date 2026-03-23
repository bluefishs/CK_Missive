/**
 * AccountInfoCard - Account status, role, auth providers, login statistics, and LINE binding
 *
 * @version 1.2.0 - 多 Provider 顯示 + React Query invalidation (取代 reload)
 */

import { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Tag,
  Typography,
  Button,
  App,
  Popconfirm,
  Space,
} from 'antd';
import {
  GoogleOutlined,
  MailOutlined,
  LinkOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import authService from '../../services/authService';
import { LINE_LOGIN_CHANNEL_ID, LINE_BIND_REDIRECT_URI } from '../../config/env';
import { logger } from '../../utils/logger';
import type { AccountInfoCardProps } from './types';

const { Text } = Typography;

/** Provider 顯示配置 */
const PROVIDER_CONFIG: Record<string, { label: string; color: string; icon?: React.ReactNode; style?: React.CSSProperties }> = {
  email: { label: '電子郵件', color: 'green', icon: <MailOutlined /> },
  google: { label: 'Google', color: 'blue', icon: <GoogleOutlined /> },
  line: { label: 'LINE', color: 'green', style: { backgroundColor: '#06C755', borderColor: '#06C755', color: '#fff' } },
  internal: { label: '內網', color: 'cyan' },
};

/** Render a colored Tag based on user role */
const getRoleTag = (role: string | undefined, isAdmin: boolean) => {
  if (isAdmin) {
    return <Tag color="red">管理員</Tag>;
  }
  switch (role) {
    case 'superuser':
      return <Tag color="purple">超級管理員</Tag>;
    case 'admin':
      return <Tag color="red">管理員</Tag>;
    case 'staff':
      return <Tag color="geekblue">承辦同仁</Tag>;
    case 'user':
      return <Tag color="blue">一般用戶</Tag>;
    case 'unverified':
      return <Tag color="orange">未驗證</Tag>;
    default:
      return <Tag>{role || '未設定'}</Tag>;
  }
};

/** Render single auth provider tag */
const getProviderTag = (provider: string) => {
  const config = PROVIDER_CONFIG[provider];
  if (!config) return <Tag key={provider}>{provider}</Tag>;
  return (
    <Tag key={provider} icon={config.icon} color={config.color} style={config.style}>
      {config.label}
    </Tag>
  );
};

export const AccountInfoCard = ({ profile, isMobile }: AccountInfoCardProps) => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [unbinding, setUnbinding] = useState(false);
  const fontSize = isMobile ? 12 : 14;
  const lineEnabled = Boolean(LINE_LOGIN_CHANNEL_ID);

  // LINE 綁定：重導向至 LINE 授權頁面 (mode=bind)
  const handleBindLine = () => {
    const uuid = typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const state = `bind_${uuid}`;
    sessionStorage.setItem('line_bind_state', state);

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: LINE_LOGIN_CHANNEL_ID,
      redirect_uri: LINE_BIND_REDIRECT_URI,
      state,
      scope: 'profile openid',
    });

    window.location.href = `https://access.line.me/oauth2/v2.1/authorize?${params.toString()}`;
  };

  // LINE 解除綁定
  const handleUnbindLine = async () => {
    setUnbinding(true);
    try {
      const result = await authService.unbindLine();
      message.success(result.message);
      // 刷新 profile 資料 (不重新整理頁面)
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    } catch (err) {
      logger.error('[LINE] Unbind failed:', err);
      const errorMsg = (err as { detail?: string })?.detail
        || (err instanceof Error ? err.message : 'LINE 解除綁定失敗');
      message.error(errorMsg);
    } finally {
      setUnbinding(false);
    }
  };

  return (
    <Card title="帳戶資訊" size={isMobile ? 'small' : 'medium'}>
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>帳戶狀態：</Text>
          <br />
          {profile.is_active ?
            <Tag color="green">已啟用</Tag> :
            <Tag color="red">已停用</Tag>
          }
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>用戶角色：</Text>
          <br />
          {getRoleTag(profile.role, profile.is_admin)}
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>驗證方式：</Text>
          <br />
          <Space size={4} wrap>
            {(profile.auth_providers && profile.auth_providers.length > 0)
              ? profile.auth_providers.map(getProviderTag)
              : getProviderTag(profile.auth_provider || 'email')
            }
          </Space>
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>郵箱驗證：</Text>
          <br />
          {profile.email_verified ?
            <Tag color="green">已驗證</Tag> :
            <Tag color="orange">未驗證</Tag>
          }
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>登入次數：</Text>
          <br />
          <Text style={{ fontSize }}>{profile.login_count ?? 0} 次</Text>
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>最後登入：</Text>
          <br />
          <Text style={{ fontSize }}>
            {profile.last_login
              ? new Date(profile.last_login).toLocaleString()
              : '從未登入'
            }
          </Text>
        </Col>
        <Col xs={24} sm={8}>
          <Text strong style={{ fontSize }}>註冊時間：</Text>
          <br />
          <Text style={{ fontSize }}>
            {new Date(profile.created_at).toLocaleString()}
          </Text>
        </Col>

        {/* LINE 帳號綁定 */}
        {lineEnabled && (
          <Col xs={24}>
            <Text strong style={{ fontSize }}>LINE 帳號：</Text>
            <br />
            {profile.line_user_id ? (
              <Space style={{ marginTop: 4 }}>
                <Tag color="green" style={{ backgroundColor: '#06C755', borderColor: '#06C755', color: '#fff' }}>
                  {profile.line_display_name || 'LINE 已綁定'}
                </Tag>
                <Popconfirm
                  title="確定要解除 LINE 綁定嗎？"
                  description="解除後需重新授權才能使用 LINE 登入"
                  onConfirm={handleUnbindLine}
                  okText="確定解除"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                >
                  <Button
                    size="small"
                    icon={<DisconnectOutlined />}
                    loading={unbinding}
                    danger
                  >
                    解除綁定
                  </Button>
                </Popconfirm>
              </Space>
            ) : (
              <Space style={{ marginTop: 4 }}>
                <Tag color="default">未綁定</Tag>
                <Button
                  size="small"
                  icon={<LinkOutlined />}
                  onClick={handleBindLine}
                  style={{ backgroundColor: '#06C755', borderColor: '#06C755', color: '#fff' }}
                >
                  綁定 LINE
                </Button>
              </Space>
            )}
          </Col>
        )}
      </Row>
    </Card>
  );
};
