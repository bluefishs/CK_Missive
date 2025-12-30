import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Typography, 
  Alert, 
  Divider, 
  Space,
  Row,
  Col,
  App
} from 'antd';
import { 
  UserOutlined, 
  LockOutlined, 
  GoogleOutlined,
  MailOutlined
} from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import authService, { LoginRequest } from '../services/authService';

const { Title, Text } = Typography;

// Google Client ID - 需要從環境變數或配置中取得
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GOOGLE_LOGIN_ENABLED = GOOGLE_CLIENT_ID && GOOGLE_CLIENT_ID !== 'your-actual-google-client-id.apps.googleusercontent.com';

interface LoginFormValues {
  username: string;
  password: string;
}

const LoginPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    // 如果認證已停用，直接重定向到儀表板
    const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';
    if (authDisabled) {
      navigate('/dashboard');
      return;
    }

    // 檢查是否已登入
    if (authService.isAuthenticated()) {
      navigate('/dashboard');
      return;
    }

    // 僅在有效 Google Client ID 時初始化 Google 登入
    if (GOOGLE_LOGIN_ENABLED) {
      initializeGoogleSignIn();
    }
  }, [navigate]);

  const initializeGoogleSignIn = async () => {
    try {
      await authService.initGoogleSignIn(GOOGLE_CLIENT_ID);
      // 延遲渲染 Google 按鈕，確保 DOM 元素已存在
      setTimeout(() => {
        authService.renderGoogleSignInButton('google-signin-button');
      }, 100);
    } catch (error) {
      console.error('Failed to initialize Google Sign-In:', error);
    }
  };

  const handleLogin = async (values: LoginFormValues) => {
    setLoading(true);
    setError('');

    try {
      const loginRequest: LoginRequest = {
        username: values.username,
        password: values.password,
      };

      const response = await authService.login(loginRequest);
      
      message.success('登入成功！');
      
      // 根據使用者角色導向不同頁面
      if (response.user_info.is_admin) {
        navigate('/admin/user-management');
      } else {
        navigate('/dashboard');
      }
    } catch (error: any) {
      console.error('Login failed:', error);
      const errorMessage = error.response?.data?.detail || '登入失敗，請檢查帳號密碼';
      setError(errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '20px'
    }}>
      <Card 
        style={{ 
          width: '100%', 
          maxWidth: 400,
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
          borderRadius: '12px'
        }}
        styles={{ body: { padding: '40px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Title level={2} style={{ color: '#1976d2', marginBottom: '8px' }}>
            乾坤測繪
          </Title>
          <Text type="secondary">公文管理系統</Text>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: '24px' }}
            closable
            onClose={() => setError('')}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleLogin}
          size="large"
        >
          <Form.Item
            name="username"
            label="帳號"
            rules={[
              { required: true, message: '請輸入帳號或電子郵件' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="帳號或電子郵件"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="密碼"
            rules={[
              { required: true, message: '請輸入密碼' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密碼"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: '16px' }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              size="large"
            >
              登入
            </Button>
          </Form.Item>
        </Form>

        <Divider>或</Divider>

        {GOOGLE_LOGIN_ENABLED ? (
          <div style={{ width: '100%' }}>
            {/* Google 官方登入按鈕容器 */}
            <div
              id="google-signin-button"
              style={{
                display: 'flex',
                justifyContent: 'center',
                marginBottom: '16px'
              }}
            />
          </div>
        ) : (
          <div style={{ width: '100%', marginBottom: '16px' }}>
            <Button
              icon={<GoogleOutlined />}
              size="large"
              block
              disabled
              style={{
                backgroundColor: '#f5f5f5',
                borderColor: '#d9d9d9',
                color: '#8c8c8c'
              }}
            >
              Google 登入 (暫時停用)
            </Button>
          </div>
        )}

        <Divider />

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            還沒有帳號？ 
            <Link to="/register" style={{ marginLeft: '8px' }}>
              立即註冊
            </Link>
          </Text>
        </div>

        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <Link to="/forgot-password">
            <Text type="secondary">忘記密碼？</Text>
          </Link>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;