/**
 * 個人資料頁面
 *
 * 顯示與編輯當前使用者的個人資訊、帳戶狀態、安全設定、登入紀錄。
 * 使用 apiClient 統一 API 呼叫，型別從 types/api.ts 匯入 (SSOT)。
 *
 * @version 2.2.0
 * @date 2026-02-08
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Typography,
  Row,
  Col,
  App,
  Modal,
  Space,
  Tag,
  Tabs
} from 'antd';
import { logger } from '../utils/logger';
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
  GoogleOutlined,
  EditOutlined,
  KeyOutlined,
  BankOutlined,
  IdcardOutlined,
  HistoryOutlined,
  SafetyOutlined,
  LaptopOutlined,
} from '@ant-design/icons';
import { LoginHistoryTab } from '../components/auth/LoginHistoryTab';
import { SessionManagementTab } from '../components/auth/SessionManagementTab';
import { MFASettingsTab } from '../components/auth/MFASettingsTab';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useResponsive } from '../hooks';
import type { User } from '../types/api';

const { Title, Text } = Typography;

interface ProfileUpdatePayload {
  username: string;
  full_name: string;
  department?: string;
  position?: string;
}

interface PasswordChangeForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export const ProfilePage = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();

  // RWD 響應式
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 載入用戶資料
  useEffect(() => {
    loadUserProfile();
  }, []);

  /**
   * 載入使用者資料
   * 1. 先從 localStorage 取得快取資料（快速顯示）
   * 2. 再從 /auth/me API 取得完整最新資料
   * 3. 比對差異並同步 localStorage（解決管理員變更不即時問題）
   */
  const loadUserProfile = async () => {
    try {
      setLoading(true);
      const userInfo = authService.getUserInfo();
      if (!userInfo) {
        navigate('/login');
        return;
      }

      // 先顯示 localStorage 快取
      setProfile(userInfo as User);

      // 從後端 API 取得最新完整資料
      try {
        const fullProfile = await apiClient.post<User>(API_ENDPOINTS.AUTH.ME, {});
        setProfile(fullProfile);
        setFormValues(fullProfile);

        // 同步 localStorage：管理員可能已變更 role/permissions 等欄位
        syncLocalStorage(userInfo, fullProfile);
      } catch {
        // API 不可用時使用 localStorage 資料
        logger.debug('使用本地用戶資訊');
        setFormValues(userInfo as User);
      }
    } catch (error) {
      logger.error('載入用戶資料失敗:', error);
      message.error('載入用戶資料失敗');
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  /** 設定表單欄位值 */
  const setFormValues = (data: User) => {
    form.setFieldsValue({
      username: data.username,
      full_name: data.full_name,
      email: data.email,
      department: data.department,
      position: data.position,
    });
  };

  /**
   * 同步 localStorage
   * 當後端資料與本地快取有差異時（如管理員修改了角色/權限），自動更新
   */
  const syncLocalStorage = (local: Partial<User>, remote: User) => {
    const keysToSync: (keyof User)[] = [
      'role', 'is_admin', 'is_active', 'permissions',
      'username', 'full_name', 'department', 'position',
      'email_verified', 'login_count', 'last_login',
    ];

    let hasChanges = false;
    for (const key of keysToSync) {
      const localVal = JSON.stringify(local[key]);
      const remoteVal = JSON.stringify(remote[key]);
      if (localVal !== remoteVal) {
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

  // 更新個人資料
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

      setProfile(updatedProfile);
      setEditing(false);
      message.success('個人資料更新成功');

      // 同步 localStorage
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

  // 修改密碼
  const handlePasswordChange = async (values: PasswordChangeForm) => {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.PASSWORD_CHANGE, {
        current_password: values.current_password,
        new_password: values.new_password,
      });

      setPasswordModalVisible(false);
      passwordForm.resetFields();
      message.success('密碼修改成功');
    } catch (error) {
      const detail = (error as { detail?: string })?.detail;
      message.error(detail || '密碼修改失敗');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: pagePadding }}>
        <Card loading size={isMobile ? 'small' : 'default'} />
      </div>
    );
  }

  if (!profile) {
    return null;
  }

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
            label: (
              <span>
                <SafetyOutlined />
                個人資料
              </span>
            ),
            children: (
              <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
                {/* 基本資訊卡片 */}
                <Col span={24}>
                  <Card
                    title="基本資訊"
                    size={isMobile ? 'small' : 'default'}
                    extra={
                      <Button
                        type="primary"
                        icon={<EditOutlined />}
                        size={isMobile ? 'small' : 'middle'}
                        onClick={() => setEditing(!editing)}
                      >
                        {isMobile ? (editing ? '取消' : '編輯') : (editing ? '取消編輯' : '編輯資料')}
                      </Button>
                    }
                  >
                    <Row gutter={[isMobile ? 12 : 24, isMobile ? 12 : 16]} align="middle">
                      <Col xs={24} sm={6} style={{ textAlign: 'center', marginBottom: isMobile ? 12 : 0 }}>
                        <Avatar
                          size={isMobile ? 64 : 80}
                          src={profile.avatar_url}
                          icon={<UserOutlined />}
                        />
                      </Col>
                      <Col xs={24} sm={18}>
                        <Form
                          form={form}
                          layout="vertical"
                          onFinish={handleUpdateProfile}
                          initialValues={{
                            username: profile.username,
                            full_name: profile.full_name,
                            email: profile.email,
                            department: profile.department,
                            position: profile.position,
                          }}
                        >
                          <Form.Item
                            label="使用者名稱"
                            name="username"
                            rules={[
                              { required: true, message: '請輸入使用者名稱' },
                              { min: 3, message: '使用者名稱至少需要 3 個字符' }
                            ]}
                          >
                            <Input
                              prefix={<UserOutlined />}
                              disabled={!editing}
                            />
                          </Form.Item>

                          <Form.Item
                            label="姓名"
                            name="full_name"
                            rules={[
                              { required: true, message: '請輸入姓名' }
                            ]}
                          >
                            <Input
                              disabled={!editing}
                            />
                          </Form.Item>

                          <Form.Item label="電子郵件" name="email">
                            <Input
                              prefix={<MailOutlined />}
                              disabled
                            />
                          </Form.Item>

                          <Row gutter={16}>
                            <Col xs={24} sm={12}>
                              <Form.Item label="部門" name="department">
                                <Input
                                  prefix={<BankOutlined />}
                                  placeholder="例：工程部"
                                  disabled={!editing}
                                />
                              </Form.Item>
                            </Col>
                            <Col xs={24} sm={12}>
                              <Form.Item label="職位" name="position">
                                <Input
                                  prefix={<IdcardOutlined />}
                                  placeholder="例：專案經理"
                                  disabled={!editing}
                                />
                              </Form.Item>
                            </Col>
                          </Row>

                          {editing && (
                            <Form.Item>
                              <Space>
                                <Button type="primary" htmlType="submit" loading={saving}>
                                  儲存變更
                                </Button>
                                <Button onClick={() => { setEditing(false); setFormValues(profile); }}>
                                  取消
                                </Button>
                              </Space>
                            </Form.Item>
                          )}
                        </Form>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 帳戶資訊卡片 */}
                <Col span={24}>
                  <Card title="帳戶資訊" size={isMobile ? 'small' : 'default'}>
                    <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
                      <Col xs={12} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>帳戶狀態：</Text>
                        <br />
                        {profile.is_active ?
                          <Tag color="green">已啟用</Tag> :
                          <Tag color="red">已停用</Tag>
                        }
                      </Col>
                      <Col xs={12} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>用戶角色：</Text>
                        <br />
                        {getRoleTag(profile.role, profile.is_admin)}
                      </Col>
                      <Col xs={12} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>驗證方式：</Text>
                        <br />
                        {profile.auth_provider === 'google' ? (
                          <Tag icon={<GoogleOutlined />} color="blue">Google</Tag>
                        ) : (
                          <Tag icon={<MailOutlined />} color="green">郵箱</Tag>
                        )}
                      </Col>
                      <Col xs={12} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>郵箱驗證：</Text>
                        <br />
                        {profile.email_verified ?
                          <Tag color="green">已驗證</Tag> :
                          <Tag color="orange">未驗證</Tag>
                        }
                      </Col>
                      <Col xs={12} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>登入次數：</Text>
                        <br />
                        <Text style={{ fontSize: isMobile ? 12 : 14 }}>{profile.login_count ?? 0} 次</Text>
                      </Col>
                      <Col xs={12} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>最後登入：</Text>
                        <br />
                        <Text style={{ fontSize: isMobile ? 12 : 14 }}>
                          {profile.last_login
                            ? new Date(profile.last_login).toLocaleString()
                            : '從未登入'
                          }
                        </Text>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>註冊時間：</Text>
                        <br />
                        <Text style={{ fontSize: isMobile ? 12 : 14 }}>
                          {new Date(profile.created_at).toLocaleString()}
                        </Text>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 安全設定卡片 */}
                {profile.auth_provider === 'email' && (
                  <Col span={24}>
                    <Card title="安全設定" size={isMobile ? 'small' : 'default'}>
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
            label: (
              <span>
                <HistoryOutlined />
                登入紀錄
              </span>
            ),
            children: (
              <Card size={isMobile ? 'small' : 'default'}>
                <LoginHistoryTab isMobile={isMobile} />
              </Card>
            ),
          },
          {
            key: 'devices',
            label: (
              <span>
                <LaptopOutlined />
                裝置管理
              </span>
            ),
            children: (
              <Card size={isMobile ? 'small' : 'default'}>
                <SessionManagementTab isMobile={isMobile} />
              </Card>
            ),
          },
          {
            key: 'mfa',
            label: (
              <span>
                <SafetyOutlined />
                雙因素認證
              </span>
            ),
            children: (
              <Card size={isMobile ? 'small' : 'default'}>
                <MFASettingsTab />
              </Card>
            ),
          },
        ]}
      />

      {/* 修改密碼彈窗 */}
      <Modal
        title="修改密碼"
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false);
          passwordForm.resetFields();
        }}
        footer={null}
        destroyOnHidden
        width={isMobile ? '95%' : 520}
      >
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handlePasswordChange}
        >
          <Form.Item
            label="目前密碼"
            name="current_password"
            rules={[{ required: true, message: '請輸入目前密碼' }]}
          >
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item
            label="新密碼"
            name="new_password"
            rules={[
              { required: true, message: '請輸入新密碼' },
              { min: 6, message: '密碼長度至少需要 6 個字符' }
            ]}
          >
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item
            label="確認新密碼"
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '請確認新密碼' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('兩次輸入的密碼不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setPasswordModalVisible(false);
                  passwordForm.resetFields();
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                確認修改
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
