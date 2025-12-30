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
  message
} from 'antd';
import {
  MailOutlined,
  ArrowLeftOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';

const { Title, Text } = Typography;

interface ForgotPasswordForm {
  email: string;
}

const ForgotPasswordPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleSubmit = async (values: ForgotPasswordForm) => {
    setLoading(true);
    try {
      // 這裡應該呼叫重設密碼 API
      // await authService.forgotPassword(values.email);

      // 暫時模擬成功
      await new Promise(resolve => setTimeout(resolve, 1000));

      setEmailSent(true);
      message.success('重設密碼郵件已發送');
    } catch (error: any) {
      console.error('Forgot password failed:', error);
      message.error(error?.response?.data?.message || '發送重設郵件失敗，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  if (emailSent) {
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
        <Col xs={24} sm={20} md={16} lg={12} xl={8}>
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
                <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
                  📧 郵件已發送
                </Title>
                <Text type="secondary">
                  我們已發送重設密碼的連結到您的信箱
                </Text>
              </div>

              <Alert
                type="success"
                showIcon
                message="請檢查您的信箱"
                description={
                  <div>
                    <p>我們已發送包含重設密碼連結的郵件到您的信箱。</p>
                    <p>請點擊郵件中的連結來重設您的密碼。</p>
                    <p style={{ marginTop: 12, color: '#666' }}>
                      <small>如果您沒有收到郵件，請檢查垃圾郵件資料夾。</small>
                    </p>
                  </div>
                }
                style={{ textAlign: 'left' }}
              />

              <Space size="middle">
                <Button
                  type="default"
                  icon={<ArrowLeftOutlined />}
                  onClick={() => navigate('/login')}
                >
                  返回登入
                </Button>
                <Button
                  type="primary"
                  onClick={() => {
                    setEmailSent(false);
                    form.resetFields();
                  }}
                >
                  重新發送
                </Button>
              </Space>
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
      <Col xs={24} sm={20} md={16} lg={12} xl={8}>
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
                🔐 忘記密碼
              </Title>
              <Text type="secondary">
                請輸入您的電子郵件地址，我們將發送重設密碼的連結給您
              </Text>
            </div>

            <Form
              form={form}
              name="forgotPassword"
              onFinish={handleSubmit}
              autoComplete="off"
              layout="vertical"
              size="large"
            >
              <Form.Item
                label="電子郵件"
                name="email"
                rules={[
                  { required: true, message: '請輸入您的電子郵件！' },
                  { type: 'email', message: '請輸入有效的電子郵件格式！' }
                ]}
              >
                <Input
                  prefix={<MailOutlined />}
                  placeholder="請輸入您的電子郵件"
                  autoComplete="email"
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 16 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  style={{ width: '100%' }}
                >
                  {loading ? '發送中...' : '發送重設連結'}
                </Button>
              </Form.Item>

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
                    onClick={() => navigate('/register')}
                    style={{ padding: 0 }}
                  >
                    建立新帳號
                  </Button>
                </Space>
              </div>
            </Form>

            <Alert
              type="info"
              showIcon
              message="小提示"
              description="如果您記起密碼了，可以直接返回登入頁面。重設密碼連結將在 24 小時後過期。"
              style={{ marginTop: 16 }}
            />
          </Space>
        </Card>
      </Col>
    </Row>
  );
};

export default ForgotPasswordPage;