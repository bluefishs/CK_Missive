import React from 'react';
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

const { Title, Text } = Typography;

interface ForgotPasswordForm {
  email: string;
}

const ForgotPasswordPage: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const handleSubmit = async (_values: ForgotPasswordForm) => {
    // 後端 API 尚未實現，顯示功能開發中訊息
    message.info('此功能尚在開發中，請聯繫系統管理員重設密碼');
  };

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

            <Alert
              type="warning"
              showIcon
              message="功能開發中"
              description="密碼重設功能尚在開發中。如需重設密碼，請聯繫系統管理員協助處理。"
              style={{ marginTop: 16 }}
            />
          </Space>
        </Card>
      </Col>
    </Row>
  );
};

export default ForgotPasswordPage;