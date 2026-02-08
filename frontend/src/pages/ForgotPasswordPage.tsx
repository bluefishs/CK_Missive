import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  Result,
  Space,
  Row,
  Col,
  App,
} from 'antd';
import {
  MailOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { AUTH_ENDPOINTS } from '../api/endpoints';

const { Title, Text } = Typography;

interface ForgotPasswordForm {
  email: string;
}

const ForgotPasswordPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (values: ForgotPasswordForm) => {
    setLoading(true);
    try {
      await apiClient.post(AUTH_ENDPOINTS.PASSWORD_RESET, {
        email: values.email,
      });
      setSubmitted(true);
    } catch {
      // 即使 API 發生錯誤也顯示成功訊息（防帳號枚舉）
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <Row
        justify="center"
        align="middle"
        style={{
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '20px',
        }}
      >
        <Col xs={24} sm={20} md={16} lg={12} xl={8}>
          <Card
            style={{
              borderRadius: '12px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
              border: 'none',
            }}
          >
            <Result
              status="success"
              title="重設連結已發送"
              subTitle="如果此 email 已註冊，您將收到密碼重設信件。請檢查您的收件匣（含垃圾郵件資料夾）。"
              extra={[
                <Button
                  type="primary"
                  key="login"
                  onClick={() => navigate('/login')}
                >
                  返回登入
                </Button>,
                <Button
                  key="retry"
                  onClick={() => {
                    setSubmitted(false);
                    form.resetFields();
                  }}
                >
                  重新發送
                </Button>,
              ]}
            />
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
        padding: '20px',
      }}
    >
      <Col xs={24} sm={20} md={16} lg={12} xl={8}>
        <Card
          style={{
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
            border: 'none',
          }}
        >
          <Space
            direction="vertical"
            size="large"
            style={{ width: '100%' }}
          >
            <div style={{ textAlign: 'center' }}>
              <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
                忘記密碼
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
                  { type: 'email', message: '請輸入有效的電子郵件格式！' },
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
                  發送重設連結
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
          </Space>
        </Card>
      </Col>
    </Row>
  );
};

export default ForgotPasswordPage;
