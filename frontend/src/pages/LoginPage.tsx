/**
 * LoginPage.tsx - 統一登入頁面
 *
 * 整合環境感知登入機制 + 傳統帳密表單
 *
 * 登入方式依環境決定：
 * ┌──────────────┬──────────┬──────────┬────────────┐
 * │ 環境          │ 快速進入  │ 帳密登入  │ Google登入 │
 * ├──────────────┼──────────┼──────────┼────────────┤
 * │ localhost    │ ✅       │ ✅       │ ✅         │
 * │ internal     │ ✅       │ ✅       │ ❌         │
 * │ ngrok/public │ ❌       │ ✅       │ ✅         │
 * └──────────────┴──────────┴──────────┴────────────┘
 *
 * @version 2.0.0
 * @date 2026-01-13
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  Alert,
  Divider,
  Tag,
  App
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  GoogleOutlined,
  LoginOutlined
} from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import authService, { LoginRequest } from '../services/authService';
import { detectEnvironment, isAuthDisabled, GOOGLE_CLIENT_ID } from '../config/env';

const { Title, Text } = Typography;

// 使用共用的環境偵測
const ENV_TYPE = detectEnvironment();

// Google OAuth 啟用條件：有效的 Client ID
const GOOGLE_LOGIN_ENABLED =
  GOOGLE_CLIENT_ID &&
  GOOGLE_CLIENT_ID !== 'your-actual-google-client-id.apps.googleusercontent.com';

// 是否為認證停用模式（VITE_AUTH_DISABLED=true）
const IS_AUTH_DISABLED = isAuthDisabled();

// 環境類型判斷
const IS_LOCALHOST = ENV_TYPE === 'localhost';
const IS_INTERNAL = ENV_TYPE === 'internal';
const IS_NGROK_OR_PUBLIC = ENV_TYPE === 'ngrok' || ENV_TYPE === 'public';

/**
 * 登入選項配置（依環境決定）
 */
const SHOW_QUICK_ENTRY = IS_AUTH_DISABLED || IS_LOCALHOST || IS_INTERNAL;
const SHOW_GOOGLE_LOGIN = GOOGLE_LOGIN_ENABLED && (IS_LOCALHOST || IS_NGROK_OR_PUBLIC);

interface LoginFormValues {
  username: string;
  password: string;
}

const LoginPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [googleReady, setGoogleReady] = useState(!SHOW_GOOGLE_LOGIN);
  const navigate = useNavigate();

  // Google 登入回調處理
  const handleGoogleCallback = useCallback(async (response: any) => {
    if (response.credential) {
      setGoogleLoading(true);
      setError('');
      try {
        const result = await authService.googleLogin(response.credential);
        message.success('Google 登入成功！');

        // 觸發登入事件，通知 Layout 更新使用者資訊
        window.dispatchEvent(new CustomEvent('user-logged-in'));

        if (result.user_info.is_admin) {
          navigate('/admin/dashboard');
        } else {
          navigate('/dashboard');
        }
      } catch (error: any) {
        console.error('Google login failed:', error);
        const errorMessage = error.response?.data?.detail || 'Google 登入失敗';

        if (error.response?.status === 403) {
          if (errorMessage.includes('未驗證') || errorMessage.includes('unverified')) {
            setError('您的帳戶尚未通過管理者驗證，請聯絡管理者。');
          } else if (errorMessage.includes('停用') || errorMessage.includes('suspended')) {
            setError('您的帳戶已被停用，請聯絡管理者。');
          } else {
            setError('登入被拒絕：' + errorMessage);
          }
        } else {
          setError(errorMessage);
        }
      } finally {
        setGoogleLoading(false);
      }
    }
  }, [message, navigate]);

  useEffect(() => {
    // 調試：確認組件載入和環境配置
    console.log('========================================');
    console.log('🔐 LoginPage 組件已載入');
    console.log('📍 ENV_TYPE:', ENV_TYPE);
    console.log('📍 IS_LOCALHOST:', IS_LOCALHOST);
    console.log('📍 IS_INTERNAL:', IS_INTERNAL);
    console.log('📍 IS_AUTH_DISABLED:', IS_AUTH_DISABLED);
    console.log('📍 SHOW_QUICK_ENTRY:', SHOW_QUICK_ENTRY);
    console.log('📍 SHOW_GOOGLE_LOGIN:', SHOW_GOOGLE_LOGIN);
    console.log('📍 googleReady (初始):', !SHOW_GOOGLE_LOGIN);
    console.log('========================================');

    // 檢查是否已登入
    if (authService.isAuthenticated()) {
      console.log('⚠️ 已登入，重導向到 dashboard');
      navigate('/dashboard');
      return;
    }

    // 根據環境初始化登入選項
    if (SHOW_GOOGLE_LOGIN) {
      initializeGoogleSignIn();
    }
  }, [navigate]);

  const initializeGoogleSignIn = async () => {
    try {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        // @ts-ignore
        if (window.google) {
          // @ts-ignore
          window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: handleGoogleCallback,
            auto_select: false,
            cancel_on_tap_outside: true,
          });
          setGoogleReady(true);
        }
      };

      if (!document.querySelector('script[src="https://accounts.google.com/gsi/client"]')) {
        document.head.appendChild(script);
      } else {
        // @ts-ignore
        if (window.google) {
          // @ts-ignore
          window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: handleGoogleCallback,
          });
          setGoogleReady(true);
        }
      }
    } catch (error) {
      console.error('Failed to initialize Google Sign-In:', error);
      setGoogleReady(true);
    }
  };

  // 快速進入（localhost、內網 IP 或 AUTH_DISABLED）
  const handleQuickEntry = async () => {
    console.log('🔐 handleQuickEntry 開始執行');
    message.loading({ content: '正在連接伺服器...', key: 'quickEntry' });
    setLoading(true);
    setError('');

    try {
      // 從後端取得開發者帳戶資訊（AUTH_DISABLED 模式會回傳 mock admin）
      console.log('📡 呼叫 /api/auth/me ...');
      const userInfo = await authService.getCurrentUser();
      console.log('✅ 取得使用者資訊:', userInfo);
      message.success({ content: `歡迎, ${userInfo.full_name || userInfo.username}!`, key: 'quickEntry' });

      // 儲存使用者資訊到 localStorage
      authService.setUserInfo(userInfo);

      // 觸發登入事件，通知 Layout 更新使用者資訊
      window.dispatchEvent(new CustomEvent('user-logged-in'));

      if (IS_AUTH_DISABLED) {
        message.success(`開發模式 - 以 ${userInfo.full_name || userInfo.username} 身份進入`);
      } else if (IS_LOCALHOST) {
        message.success(`本機模式 - 以 ${userInfo.full_name || userInfo.username} 身份進入`);
      } else if (IS_INTERNAL) {
        message.success(`內網模式 - 以 ${userInfo.full_name || userInfo.username} 身份進入`);
      }

      // 根據權限導向不同頁面
      if (userInfo.is_admin) {
        navigate('/admin/dashboard');
      } else {
        navigate('/dashboard');
      }
    } catch (error: any) {
      console.error('Quick entry failed:', error);
      const errorMsg = error?.message || '快速進入失敗，請確認後端服務是否啟動';
      message.error({ content: errorMsg, key: 'quickEntry', duration: 5 });
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 帳密登入
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

      // 觸發登入事件，通知 Layout 更新使用者資訊
      window.dispatchEvent(new CustomEvent('user-logged-in'));

      if (response.user_info.is_admin) {
        navigate('/admin/user-management');
      } else {
        navigate('/dashboard');
      }
    } catch (error: any) {
      console.error('Login failed:', error);
      const errorMessage = error.response?.data?.detail || '登入失敗，請檢查帳號密碼';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Google 登入觸發
  const handleGoogleLogin = () => {
    // @ts-ignore
    if (window.google) {
      // @ts-ignore
      window.google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed()) {
          // @ts-ignore
          window.google.accounts.id.renderButton(
            document.getElementById('google-signin-container'),
            { theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill', width: 280 }
          );
        }
      });
    }
  };

  // 取得環境標籤顯示
  const getEnvLabel = () => {
    switch (ENV_TYPE) {
      case 'localhost': return { text: 'localhost', color: 'blue' };
      case 'internal': return { text: '內網環境', color: 'orange' };
      case 'ngrok': return { text: 'ngrok', color: 'green' };
      case 'public': return { text: '正式環境', color: 'purple' };
      default: return null;
    }
  };

  const envLabel = getEnvLabel();

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '20px'
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: 420,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          borderRadius: '16px',
          border: '1px solid rgba(201, 169, 98, 0.2)'
        }}
        styles={{ body: { padding: '40px 32px' } }}
      >
        {/* 標題區 */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <Title level={2} style={{ color: '#c9a962', marginBottom: '4px' }}>
            乾坤測繪
          </Title>
          <Text style={{ color: '#8c8c8c' }}>公文管理系統</Text>
          {envLabel && (
            <div style={{ marginTop: '8px' }}>
              <Tag color={envLabel.color}>{envLabel.text}</Tag>
            </div>
          )}
        </div>

        {/* 錯誤訊息 */}
        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: '20px' }}
            closable
            onClose={() => setError('')}
          />
        )}

        {/* 快速進入按鈕 (localhost / internal) */}
        {SHOW_QUICK_ENTRY && (
          <>
            <Button
              type="primary"
              icon={<LoginOutlined />}
              size="large"
              block
              loading={loading}
              onClick={(e) => {
                e.preventDefault();
                console.log('🚀 快速進入按鈕被點擊');
                handleQuickEntry();
              }}
              style={{
                height: '48px',
                backgroundColor: '#52c41a',
                borderColor: '#52c41a',
                marginBottom: '16px'
              }}
            >
              快速進入系統
            </Button>
            <Divider style={{ margin: '16px 0', color: '#8c8c8c' }}>或使用帳號登入</Divider>
          </>
        )}

        {/* 帳密登入表單 */}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleLogin}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '請輸入帳號或電子郵件' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="帳號或電子郵件"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '請輸入密碼' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
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
              style={{ height: '44px' }}
            >
              帳號密碼登入
            </Button>
          </Form.Item>
        </Form>

        {/* Google 登入 (localhost / ngrok / public) */}
        {SHOW_GOOGLE_LOGIN && googleReady && (
          <>
            <Divider style={{ margin: '16px 0', color: '#8c8c8c' }}>或</Divider>
            <div id="google-signin-container" style={{ display: 'flex', justifyContent: 'center' }}>
              <Button
                icon={<GoogleOutlined />}
                size="large"
                block
                loading={googleLoading}
                onClick={handleGoogleLogin}
                style={{
                  height: '44px',
                  backgroundColor: '#fff',
                  borderColor: '#d9d9d9',
                  color: '#333'
                }}
              >
                使用 Google 帳號登入
              </Button>
            </div>
          </>
        )}

        {/* 輔助連結 */}
        <Divider style={{ margin: '20px 0' }} />
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            還沒有帳號？
            <Link to="/register" style={{ marginLeft: '8px', color: '#c9a962' }}>
              立即註冊
            </Link>
          </Text>
        </div>
        <div style={{ textAlign: 'center', marginTop: '12px' }}>
          <Link to="/forgot-password">
            <Text type="secondary" style={{ fontSize: '13px' }}>忘記密碼？</Text>
          </Link>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
