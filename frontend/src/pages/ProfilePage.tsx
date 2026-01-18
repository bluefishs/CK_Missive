import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Typography,
  Divider,
  Row,
  Col,
  App,
  Modal,
  Space,
  Tag
} from 'antd';
import { logger } from '../utils/logger';
import { 
  UserOutlined, 
  MailOutlined, 
  LockOutlined, 
  GoogleOutlined,
  EditOutlined,
  KeyOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import { API_BASE_URL } from '../api/client';

const { Title, Text } = Typography;

interface UserProfile {
  id: number;
  email: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  auth_provider?: string;
  role: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  login_count: number;
  email_verified: boolean;
  permissions?: string | string[];
}

interface PasswordChangeForm {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export const ProfilePage = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();

  // 載入用戶資料
  useEffect(() => {
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      setLoading(true);
      const userInfo = authService.getUserInfo();
      if (userInfo) {
        // 從 localStorage 獲取基本資訊
        setProfile(userInfo);
        
        // 嘗試從後端 API 獲取完整資訊
        try {
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${authService.getToken()}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
          });
          if (response.ok) {
            const fullProfile = await response.json();
            setProfile(fullProfile);
            form.setFieldsValue({
              username: fullProfile.username,
              full_name: fullProfile.full_name,
              email: fullProfile.email
            });
          }
        } catch (apiError) {
          logger.debug('使用本地用戶資訊:', apiError);
          form.setFieldsValue({
            username: userInfo.username,
            full_name: userInfo.full_name,
            email: userInfo.email
          });
        }
      } else {
        navigate('/login');
      }
    } catch (error) {
      logger.error('載入用戶資料失敗:', error);
      message.error('載入用戶資料失敗');
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  // 更新個人資料
  const handleUpdateProfile = async (values: any) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authService.getToken()}`
        },
        body: JSON.stringify({
          username: values.username,
          full_name: values.full_name
        })
      });

      if (response.ok) {
        const updatedProfile = await response.json();
        setProfile(updatedProfile);
        setEditing(false);
        message.success('個人資料更新成功');
        
        // 更新 localStorage 中的用戶資訊
        const currentUserInfo = authService.getUserInfo();
        if (currentUserInfo) {
          authService.setUserInfo({
            ...currentUserInfo,
            username: values.username,
            full_name: values.full_name
          });
        }
      } else {
        const error = await response.json();
        message.error(error.detail || '更新失敗');
      }
    } catch (error) {
      logger.error('更新個人資料失敗:', error);
      message.error('更新失敗');
    }
  };

  // 修改密碼
  const handlePasswordChange = async (values: PasswordChangeForm) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/password/change`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authService.getToken()}`
        },
        body: JSON.stringify({
          current_password: values.current_password,
          new_password: values.new_password
        })
      });

      if (response.ok) {
        setPasswordModalVisible(false);
        passwordForm.resetFields();
        message.success('密碼修改成功');
      } else {
        const error = await response.json();
        message.error(error.detail || '密碼修改失敗');
      }
    } catch (error) {
      logger.error('密碼修改失敗:', error);
      message.error('密碼修改失敗');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '24px' }}>
        <Card loading />
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  const getRoleTag = (role: string, isAdmin: boolean) => {
    if (isAdmin) {
      return <Tag color="red">管理員</Tag>;
    }
    switch (role) {
      case 'admin':
        return <Tag color="red">管理員</Tag>;
      case 'user':
        return <Tag color="blue">一般用戶</Tag>;
      case 'unverified':
        return <Tag color="orange">未驗證</Tag>;
      default:
        return <Tag>{role}</Tag>;
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <Title level={2}>
        <UserOutlined /> 個人設定
      </Title>
      
      <Row gutter={[16, 16]}>
        {/* 基本資訊卡片 */}
        <Col span={24}>
          <Card
            title="基本資訊"
            extra={
              <Button 
                type="primary" 
                icon={<EditOutlined />}
                onClick={() => setEditing(!editing)}
              >
                {editing ? '取消編輯' : '編輯資料'}
              </Button>
            }
          >
            <Row gutter={[24, 16]} align="middle">
              <Col xs={24} sm={6} style={{ textAlign: 'center' }}>
                <Avatar 
                  size={80} 
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
                    email: profile.email
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

                  {editing && (
                    <Form.Item>
                      <Space>
                        <Button type="primary" htmlType="submit">
                          儲存變更
                        </Button>
                        <Button onClick={() => setEditing(false)}>
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
          <Card title="帳戶資訊">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Text strong>帳戶狀態：</Text>
                <br />
                {profile.is_active ? 
                  <Tag color="green">已啟用</Tag> : 
                  <Tag color="red">已停用</Tag>
                }
              </Col>
              <Col span={12}>
                <Text strong>用戶角色：</Text>
                <br />
                {getRoleTag(profile.role, profile.is_admin)}
              </Col>
              <Col span={12}>
                <Text strong>驗證方式：</Text>
                <br />
                {profile.auth_provider === 'google' ? (
                  <Tag icon={<GoogleOutlined />} color="blue">Google</Tag>
                ) : (
                  <Tag icon={<MailOutlined />} color="green">郵箱</Tag>
                )}
              </Col>
              <Col span={12}>
                <Text strong>郵箱驗證：</Text>
                <br />
                {profile.email_verified ? 
                  <Tag color="green">已驗證</Tag> : 
                  <Tag color="orange">未驗證</Tag>
                }
              </Col>
              <Col span={12}>
                <Text strong>註冊時間：</Text>
                <br />
                <Text>{new Date(profile.created_at).toLocaleString()}</Text>
              </Col>
              <Col span={12}>
                <Text strong>最後登入：</Text>
                <br />
                <Text>
                  {profile.last_login 
                    ? new Date(profile.last_login).toLocaleString()
                    : '從未登入'
                  }
                </Text>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 安全設定卡片 */}
        {profile.auth_provider === 'email' && (
          <Col span={24}>
            <Card title="安全設定">
              <Button
                type="primary"
                icon={<KeyOutlined />}
                onClick={() => setPasswordModalVisible(true)}
              >
                修改密碼
              </Button>
            </Card>
          </Col>
        )}
      </Row>

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
