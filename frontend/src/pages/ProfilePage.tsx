/**
 * 個人資料頁面
 *
 * 顯示與編輯當前使用者的個人資訊、帳戶狀態、安全設定、登入紀錄。
 * 使用 apiClient 統一 API 呼叫，型別從 types/api.ts 匯入 (SSOT)。
 *
 * @version 3.0.0 - Refactored: extracted ProfileInfoCard, AccountInfoCard, PasswordChangeModal
 * @date 2026-03-16
 */

import { useState } from 'react';
import {
  Card,
  Button,
  Typography,
  Row,
  Col,
  App,
  Tabs,
} from 'antd';
import { logger } from '../utils/logger';
import {
  UserOutlined,
  KeyOutlined,
  HistoryOutlined,
  SafetyOutlined,
  LaptopOutlined,
} from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { LoginHistoryTab } from '../components/auth/LoginHistoryTab';
import { SessionManagementTab } from '../components/auth/SessionManagementTab';
import { MFASettingsTab } from '../components/auth/MFASettingsTab';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import authService from '../services/authService';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useResponsive } from '../hooks';
import type { User } from '../types/api';
import {
  ProfileInfoCard,
  AccountInfoCard,
  PasswordChangeModal,
} from './profile';
import type { ProfileUpdatePayload, PasswordChangeFormValues } from './profile';

const { Title } = Typography;

export const ProfilePage = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);

  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  /**
   * Load user profile
   * 1. Use localStorage as placeholderData
   * 2. Fetch latest from /auth/me
   * 3. Sync differences to localStorage
   */
  const {
    data: profile = null,
    isLoading: loading,
  } = useQuery<User | null>({
    queryKey: ['profile'],
    queryFn: async () => {
      const userInfo = authService.getUserInfo();
      if (!userInfo) {
        navigate(ROUTES.LOGIN);
        return null;
      }

      try {
        const fullProfile = await apiClient.post<User>(API_ENDPOINTS.AUTH.ME, {});
        syncLocalStorage(userInfo, fullProfile);
        return fullProfile;
      } catch {
        logger.debug('使用本地用戶資訊');
        return userInfo as User;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
    placeholderData: () => {
      const userInfo = authService.getUserInfo();
      return userInfo ? (userInfo as User) : null;
    },
  });

  /** Sync localStorage when backend data differs from local cache */
  const syncLocalStorage = (local: Partial<User>, remote: User) => {
    const keysToSync: (keyof User)[] = [
      'role', 'is_admin', 'is_active', 'permissions',
      'username', 'full_name', 'department', 'position',
      'email_verified', 'login_count', 'last_login',
    ];

    let hasChanges = false;
    for (const key of keysToSync) {
      if (JSON.stringify(local[key]) !== JSON.stringify(remote[key])) {
        hasChanges = true;
        break;
      }
    }

    if (hasChanges) {
      const currentUserInfo = authService.getUserInfo();
      if (currentUserInfo) {
        authService.setUserInfo({
          ...currentUserInfo,
          role: remote.role ?? currentUserInfo.role,
          is_admin: remote.is_admin,
          is_active: remote.is_active,
          permissions: remote.permissions,
          username: remote.username,
          full_name: remote.full_name,
          department: remote.department,
          position: remote.position,
          email_verified: remote.email_verified ?? currentUserInfo.email_verified,
          login_count: remote.login_count ?? currentUserInfo.login_count,
          last_login: remote.last_login,
        });
        logger.info('已同步本地使用者資訊');
      }
    }
  };

  /** Update profile via API */
  const handleUpdateProfile = async (values: ProfileUpdatePayload) => {
    setSaving(true);
    try {
      const updatedProfile = await apiClient.post<User>(
        API_ENDPOINTS.AUTH.PROFILE_UPDATE,
        {
          username: values.username,
          full_name: values.full_name,
          department: values.department || null,
          position: values.position || null,
        }
      );

      queryClient.setQueryData<User | null>(['profile'], updatedProfile);
      setEditing(false);
      message.success('個人資料更新成功');

      const currentUserInfo = authService.getUserInfo();
      if (currentUserInfo) {
        authService.setUserInfo({
          ...currentUserInfo,
          username: updatedProfile.username,
          full_name: updatedProfile.full_name,
          department: updatedProfile.department,
          position: updatedProfile.position,
        });
      }
    } catch (error) {
      const detail = (error as { detail?: string })?.detail;
      message.error(detail || '更新失敗');
    } finally {
      setSaving(false);
    }
  };

  /** Change password via API */
  const handlePasswordChange = async (values: PasswordChangeFormValues) => {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.PASSWORD_CHANGE, {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      setPasswordModalVisible(false);
      message.success('密碼修改成功');
    } catch (error) {
      const detail = (error as { detail?: string })?.detail;
      message.error(detail || '密碼修改失敗');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: pagePadding }}>
        <Card loading size={isMobile ? 'small' : 'medium'} />
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <div style={{ padding: pagePadding, maxWidth: '800px', margin: '0 auto' }}>
      <Title level={isMobile ? 4 : 2} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <UserOutlined style={{ marginRight: 8 }} />
        個人設定
      </Title>

      <Tabs
        defaultActiveKey="profile"
        size={isMobile ? 'small' : 'middle'}
        items={[
          {
            key: 'profile',
            label: <span><SafetyOutlined /> 個人資料</span>,
            children: (
              <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
                <Col span={24}>
                  <ProfileInfoCard
                    profile={profile}
                    isMobile={isMobile}
                    editing={editing}
                    saving={saving}
                    onToggleEdit={() => setEditing(!editing)}
                    onSave={handleUpdateProfile}
                    onCancelEdit={() => setEditing(false)}
                  />
                </Col>
                <Col span={24}>
                  <AccountInfoCard profile={profile} isMobile={isMobile} />
                </Col>
                {profile.auth_provider === 'email' && (
                  <Col span={24}>
                    <Card title="安全設定" size={isMobile ? 'small' : 'medium'}>
                      <Button
                        type="primary"
                        icon={<KeyOutlined />}
                        size={isMobile ? 'small' : 'middle'}
                        onClick={() => setPasswordModalVisible(true)}
                      >
                        修改密碼
                      </Button>
                    </Card>
                  </Col>
                )}
              </Row>
            ),
          },
          {
            key: 'login-history',
            label: <span><HistoryOutlined /> 登入紀錄</span>,
            children: (
              <Card size={isMobile ? 'small' : 'medium'}>
                <LoginHistoryTab isMobile={isMobile} />
              </Card>
            ),
          },
          {
            key: 'devices',
            label: <span><LaptopOutlined /> 裝置管理</span>,
            children: (
              <Card size={isMobile ? 'small' : 'medium'}>
                <SessionManagementTab isMobile={isMobile} />
              </Card>
            ),
          },
          {
            key: 'mfa',
            label: <span><SafetyOutlined /> 雙因素認證</span>,
            children: (
              <Card size={isMobile ? 'small' : 'medium'}>
                <MFASettingsTab />
              </Card>
            ),
          },
        ]}
      />

      <PasswordChangeModal
        open={passwordModalVisible}
        isMobile={isMobile}
        onCancel={() => setPasswordModalVisible(false)}
        onSubmit={handlePasswordChange}
      />
    </div>
  );
};
