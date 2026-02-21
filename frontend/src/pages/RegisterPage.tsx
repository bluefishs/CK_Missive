import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  Alert,
  Space,
  Row,
  Col,
  message,
  Checkbox,
  Divider
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
  ArrowLeftOutlined,
  GoogleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import { logger } from '../services/logger';

const { Title, Text } = Typography;

import type { RegisterFormValues } from '../types/forms';

type RegisterForm = RegisterFormValues;

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleSubmit = async (values: RegisterForm) => {
    setLoading(true);
    try {
      const { confirmPassword, agreement, ...registerData } = values;

      // 呼叫註冊 API
      await authService.register(registerData);

      setRegistered(true);
      message.success('註冊成功！請等待管理員審核您的帳號');
    } catch (error: unknown) {
      logger.error('Registration failed:', error);
      const err = error as { response?: { data?: { message?: string } } };
      const errorMessage = err?.response?.data?.message || '註冊失敗，請稍後再試';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (registered) {
    return (
      <Row
        justify="center"
        align="middle"
        style={{
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '20px'
        }}
      >
        <Col xs={24} sm={20} md={16} lg={12} xl={10}>
          <Card
            style={{
              borderRadius: '12px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
              border: 'none'
            }}
          >
            <Space
              direction="vertical"
              size="large"
              style={{ width: '100%', textAlign: 'center' }}
            >
              <div>
                <Title level={2} style={{ color: '#52c41a', marginBottom: 8 }}>
                  🎉 註冊成功
                </Title>
                <Text type="secondary">
                  您的帳號已成功建立，請等待管理員審核
                </Text>
              </div>

              <Alert
                type="success"
                showIcon
                message="帳號創建成功"
                description={
                  <div>
                    <p>您的帳號已成功建立並送出審核申請。</p>
                    <p>管理員將會在 1-2 個工作天內審核您的申請。</p>
                    <p>審核通過後，您將收到電子郵件通知，屆時即可使用您的帳號登入系統。</p>
                  </div>
                }
                style={{ textAlign: 'left' }}
              />

              <div>
                <Button
                  type="primary"
                  size="large"
                  onClick={() => navigate('/login')}
                >
                  返回登入頁面
                </Button>
              </div>

              <Text type="secondary" style={{ fontSize: '12px' }}>
                如有任何問題，請聯繫系統管理員
              </Text>
            </Space>
          </Card>
        </Col>
      </Row>
    );
  }

  return (
    <Row
      justify="center"
      align="middle"
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '20px'
      }}
    >
      <Col xs={24} sm={20} md={16} lg={12} xl={10}>
        <Card
          style={{
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
            border: 'none'
          }}
        >
          <Space
            direction="vertical"
            size="large"
            style={{ width: '100%' }}
          >
            <div style={{ textAlign: 'center' }}>
              <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
                👋 建立新帳號
              </Title>
              <Text type="secondary">
                歡迎加入乾坤測繪公文管理系統
              </Text>
            </div>

            <Form
              form={form}
              name="register"
              onFinish={handleSubmit}
              autoComplete="off"
              layout="vertical"
              size="large"
              scrollToFirstError
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="使用者名稱"
                    name="username"
                    rules={[
                      { required: true, message: '請輸入使用者名稱！' },
                      { min: 3, message: '使用者名稱至少需要 3 個字元！' },
                      { max: 20, message: '使用者名稱不能超過 20 個字元！' }
                    ]}
                  >
                    <Input
                      prefix={<UserOutlined />}
                      placeholder="請輸入使用者名稱"
                      autoComplete="username"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="真實姓名"
                    name="full_name"
                    rules={[
                      { required: true, message: '請輸入真實姓名！' },
                      { max: 50, message: '姓名不能超過 50 個字元！' }
                    ]}
                  >
                    <Input
                      prefix={<UserOutlined />}
                      placeholder="請輸入真實姓名"
                      autoComplete="name"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="電子郵件"
                name="email"
                rules={[
                  { required: true, message: '請輸入電子郵件！' },
                  { type: 'email', message: '請輸入有效的電子郵件格式！' }
                ]}
              >
                <Input
                  prefix={<MailOutlined />}
                  placeholder="請輸入電子郵件"
                  autoComplete="email"
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="密碼"
                    name="password"
                    rules={[
                      { required: true, message: '請輸入密碼！' },
                      { min: 6, message: '密碼至少需要 6 個字元！' },
                      {
                        pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                        message: '密碼需包含大小寫字母和數字！'
                      }
                    ]}
                    hasFeedback
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="請輸入密碼"
                      autoComplete="new-password"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="確認密碼"
                    name="confirmPassword"
                    dependencies={['password']}
                    rules={[
                      { required: true, message: '請確認密碼！' },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('password') === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error('兩次輸入的密碼不一致！'));
                        },
                      }),
                    ]}
                    hasFeedback
                  >
                    <Input.Password
                      prefix={<LockOutlined />}
                      placeholder="請再次輸入密碼"
                      autoComplete="new-password"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="agreement"
                valuePropName="checked"
                rules={[
                  {
                    validator: (_, value) =>
                      value ? Promise.resolve() : Promise.reject(new Error('請閱讀並同意使用條款')),
                  },
                ]}
              >
                <Checkbox>
                  我已閱讀並同意{' '}
                  <Button type="link" style={{ padding: 0, height: 'auto' }}>
                    使用條款
                  </Button>{' '}
                  和{' '}
                  <Button type="link" style={{ padding: 0, height: 'auto' }}>
                    隱私政策
                  </Button>
                </Checkbox>
              </Form.Item>

              <Form.Item style={{ marginBottom: 16 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  style={{ width: '100%' }}
                >
                  {loading ? '創建中...' : '創建帳號'}
                </Button>
              </Form.Item>

              <Divider>或</Divider>

              <Button
                icon={<GoogleOutlined />}
                style={{ width: '100%', marginBottom: 16 }}
                disabled
              >
                使用 Google 帳號註冊 (暫時停用)
              </Button>

              <div style={{ textAlign: 'center' }}>
                <Space size="middle">
                  <Button
                    type="link"
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate('/login')}
                    style={{ padding: 0 }}
                  >
                    返回登入
                  </Button>
                  <span style={{ color: '#d9d9d9' }}>|</span>
                  <Button
                    type="link"
                    onClick={() => navigate('/forgot-password')}
                    style={{ padding: 0 }}
                  >
                    忘記密碼？
                  </Button>
                </Space>
              </div>
            </Form>

            <Alert
              type="info"
              showIcon
              message="帳號審核說明"
              description="為了確保系統安全，所有新註冊的帳號都需要經過管理員審核。審核通過後，您將收到電子郵件通知。"
              style={{ marginTop: 16 }}
            />
          </Space>
        </Card>
      </Col>
    </Row>
  );
};

export default RegisterPage;