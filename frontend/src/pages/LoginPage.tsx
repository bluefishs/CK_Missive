/**
 * LoginPage.tsx - 統一登入頁面
 *
 * 登入方式依環境決定：
 * ┌──────────────┬──────────┬──────────┬────────────┬────────────┐
 * │ 環境          │ 快速進入  │ 帳密登入  │ Google登入 │ LINE登入   │
 * ├──────────────┼──────────┼──────────┼────────────┼────────────┤
 * │ localhost    │ ✅       │ ✅       │ ✅         │ ✅         │
 * │ internal     │ ✅       │ ✅       │ ❌         │ ✅         │
 * │ ngrok/public │ ❌       │ ✅       │ ✅         │ ✅         │
 * └──────────────┴──────────┴──────────┴────────────┴────────────┘
 *
 * @version 2.2.0
 * @date 2026-03-22
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
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import authService, { MFARequiredError } from '../services/authService';
import { useResponsive } from '../hooks';
import { detectEnvironment, isAuthDisabled, GOOGLE_CLIENT_ID, LINE_LOGIN_CHANNEL_ID, LINE_LOGIN_REDIRECT_URI } from '../config/env';
import { logger } from '../utils/logger';

const { Title, Text } = Typography;

import type { LoginFormValues } from '../types/forms';

const LoginPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [lineLoading, setLineLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // RWD 響應式
  const { isMobile, responsiveValue } = useResponsive();
  const cardPadding = responsiveValue({ mobile: '24px 16px', tablet: '32px 24px', desktop: '40px 32px' });

  // 取得環境和 returnUrl
  const envType = detectEnvironment();
  const returnUrl = searchParams.get('returnUrl');

  // Google OAuth 啟用條件
  const googleLoginEnabled = Boolean(
    GOOGLE_CLIENT_ID &&
    GOOGLE_CLIENT_ID !== 'your-actual-google-client-id.apps.googleusercontent.com'
  );

  // LINE Login 啟用條件
  const lineLoginEnabled = Boolean(LINE_LOGIN_CHANNEL_ID);

  // 根據環境決定顯示哪些登入選項
  const showQuickEntry = isAuthDisabled() || envType === 'localhost' || envType === 'internal';
  const showGoogleLogin = googleLoginEnabled && (envType === 'localhost' || envType === 'ngrok' || envType === 'public');
  const showLineLogin = lineLoginEnabled;

  const [googleReady, setGoogleReady] = useState(!showGoogleLogin);

  // Google 登入回調處理
  interface GoogleCredentialResponse {
    credential?: string;
  }

  const handleGoogleCallback = useCallback(async (response: GoogleCredentialResponse) => {
    if (response.credential) {
      setGoogleLoading(true);
      setError('');
      try {
        const result = await authService.googleLogin(response.credential);
        message.success('Google 登入成功！');
        window.dispatchEvent(new CustomEvent('user-logged-in'));

        const targetUrl = returnUrl
          ? decodeURIComponent(returnUrl)
          : (result.user_info.is_admin ? '/admin/dashboard' : '/dashboard');
        navigate(targetUrl);
      } catch (error: unknown) {
        // MFA 流程：Google 認證成功但需要雙因素認證
        if (error instanceof MFARequiredError) {
          message.info('請完成雙因素認證');
          navigate('/mfa/verify', {
            state: { mfa_token: error.mfa_token, returnUrl: returnUrl || undefined },
          });
          return;
        }
        logger.error('Google login failed:', error);
        const errorMessage = error instanceof Error ? error.message : 'Google 登入失敗';
        setError(errorMessage);
      } finally {
        setGoogleLoading(false);
      }
    }
  }, [message, navigate, returnUrl]);

  useEffect(() => {
    logger.debug('🔐 LoginPage 載入 | 環境:', envType, '| 快速進入:', showQuickEntry, '| Google:', showGoogleLogin);

    // 檢查是否已登入
    if (authService.isAuthenticated()) {
      logger.debug('⚠️ 已登入，重導向到 dashboard');
      navigate('/dashboard');
      return;
    }

    // 初始化 Google 登入
    if (showGoogleLogin) {
      initializeGoogleSignIn();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- initializeGoogleSignIn is stable, adding it causes re-initialization
  }, [navigate, envType, showQuickEntry, showGoogleLogin]);

  const initializeGoogleSignIn = async () => {
    try {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        if (window.google) {
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
        if (window.google) {
          window.google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: handleGoogleCallback,
          });
          setGoogleReady(true);
        }
      }
    } catch (error) {
      logger.error('Failed to initialize Google Sign-In:', error);
      setGoogleReady(true);
    }
  };

  // 快速進入
  const handleQuickEntry = async () => {
    logger.debug('🔐 快速進入開始');
    message.loading({ content: '正在連接伺服器...', key: 'quickEntry' });
    setLoading(true);
    setError('');

    try {
      const userInfo = await authService.getCurrentUser();
      logger.debug('✅ 取得使用者資訊:', userInfo);

      // 儲存使用者資訊
      authService.setUserInfo(userInfo);

      // 觸發登入事件
      window.dispatchEvent(new CustomEvent('user-logged-in'));

      message.success({ content: `歡迎, ${userInfo.full_name || userInfo.username}!`, key: 'quickEntry' });

      // 導航到目標頁面
      const targetUrl = returnUrl
        ? decodeURIComponent(returnUrl)
        : '/dashboard';
      navigate(targetUrl);
    } catch (error: unknown) {
      logger.error('Quick entry failed:', error);
      const errorMsg = error instanceof Error ? error.message : '快速進入失敗，請確認後端服務是否啟動';
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
      const response = await authService.login({
        username: values.username,
        password: values.password,
      });
      message.success('登入成功！');
      window.dispatchEvent(new CustomEvent('user-logged-in'));

      const targetUrl = returnUrl
        ? decodeURIComponent(returnUrl)
        : (response.user_info.is_admin ? '/admin/dashboard' : '/dashboard');
      navigate(targetUrl);
    } catch (error: unknown) {
      // MFA 流程：密碼正確但需要雙因素認證
      if (error instanceof MFARequiredError) {
        message.info('請完成雙因素認證');
        navigate('/mfa/verify', {
          state: { mfa_token: error.mfa_token, returnUrl: returnUrl || undefined },
        });
        return;
      }
      logger.error('Login failed:', error);
      const errorMessage = error instanceof Error ? error.message : '登入失敗，請檢查帳號密碼';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Google 登入觸發
  const handleGoogleLogin = () => {
    if (window.google) {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed()) {
          window.google?.accounts.id.renderButton(
            document.getElementById('google-signin-container'),
            { theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill', width: 280 }
          );
        }
      });
    }
  };

  // LINE 登入觸發 — 重導向至 LINE Authorization URL
  const handleLineLogin = () => {
    setLineLoading(true);
    // crypto.randomUUID() 僅在 Secure Context (https/localhost) 可用
    // 內網 HTTP 環境使用 fallback
    const state = typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem('line_login_state', state);
    if (returnUrl) {
      sessionStorage.setItem('line_login_return_url', returnUrl);
    }

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: LINE_LOGIN_CHANNEL_ID,
      redirect_uri: LINE_LOGIN_REDIRECT_URI,
      state,
      scope: 'profile openid email',
    });

    window.location.href = `https://access.line.me/oauth2/v2.1/authorize?${params.toString()}`;
  };

  // 環境標籤
  const getEnvLabel = () => {
    switch (envType) {
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
      padding: isMobile ? '12px' : '20px'
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: isMobile ? '100%' : 420,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          borderRadius: isMobile ? '12px' : '16px',
          border: '1px solid rgba(201, 169, 98, 0.2)'
        }}
        styles={{ body: { padding: cardPadding } }}
      >
        {/* 標題區 */}
        <div style={{ textAlign: 'center', marginBottom: isMobile ? '16px' : '24px' }}>
          <Title level={isMobile ? 3 : 2} style={{ color: '#c9a962', marginBottom: '4px' }}>
            乾坤測繪
          </Title>
          <Text style={{ color: '#8c8c8c', fontSize: isMobile ? 13 : 14 }}>公文管理系統</Text>
          {envLabel && (
            <div style={{ marginTop: '8px' }}>
              <Tag color={envLabel.color}>{envLabel.text}</Tag>
            </div>
          )}
        </div>

        {/* 錯誤訊息 */}
        {error && (
          <Alert
            title={error}
            type="error"
            showIcon
            style={{ marginBottom: '20px' }}
            closable
            onClose={() => setError('')}
          />
        )}

        {/* 快速進入按鈕 */}
        {showQuickEntry && (
          <>
            <Button
              type="primary"
              icon={<LoginOutlined />}
              size={isMobile ? 'middle' : 'large'}
              block
              loading={loading}
              onClick={handleQuickEntry}
              style={{
                height: isMobile ? '40px' : '48px',
                backgroundColor: '#52c41a',
                borderColor: '#52c41a',
                marginBottom: isMobile ? '12px' : '16px'
              }}
            >
              快速進入系統
            </Button>
            <Divider style={{ margin: isMobile ? '12px 0' : '16px 0', color: '#8c8c8c', fontSize: isMobile ? 12 : 14 }}>
              或使用帳號登入
            </Divider>
          </>
        )}

        {/* 帳密登入表單 */}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleLogin}
          size={isMobile ? 'middle' : 'large'}
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

          <Form.Item style={{ marginBottom: isMobile ? '12px' : '16px' }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              size={isMobile ? 'middle' : 'large'}
              style={{ height: isMobile ? '40px' : '44px' }}
            >
              帳號密碼登入
            </Button>
          </Form.Item>
        </Form>

        {/* 第三方登入 */}
        {(showGoogleLogin || showLineLogin) && (
          <>
            <Divider style={{ margin: isMobile ? '12px 0' : '16px 0', color: '#8c8c8c', fontSize: isMobile ? 12 : 14 }}>或</Divider>

            {/* Google 登入 */}
            {showGoogleLogin && googleReady && (
              <div id="google-signin-container" style={{ display: 'flex', justifyContent: 'center', marginBottom: showLineLogin ? (isMobile ? 8 : 12) : 0 }}>
                <Button
                  icon={<GoogleOutlined />}
                  size={isMobile ? 'middle' : 'large'}
                  block
                  loading={googleLoading}
                  onClick={handleGoogleLogin}
                  style={{
                    height: isMobile ? '40px' : '44px',
                    backgroundColor: '#fff',
                    borderColor: '#d9d9d9',
                    color: '#333'
                  }}
                >
                  {isMobile ? 'Google 登入' : '使用 Google 帳號登入'}
                </Button>
              </div>
            )}

            {/* LINE 登入 */}
            {showLineLogin && (
              <Button
                size={isMobile ? 'middle' : 'large'}
                block
                loading={lineLoading}
                onClick={handleLineLogin}
                style={{
                  height: isMobile ? '40px' : '44px',
                  backgroundColor: '#06C755',
                  borderColor: '#06C755',
                  color: '#fff',
                  fontWeight: 600,
                }}
              >
                {isMobile ? 'LINE 登入' : '使用 LINE 帳號登入'}
              </Button>
            )}
          </>
        )}

        {/* 輔助連結 */}
        <Divider style={{ margin: isMobile ? '16px 0' : '20px 0' }} />
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: isMobile ? 13 : 14 }}>
            還沒有帳號？
            <Link to="/register" style={{ marginLeft: '8px', color: '#c9a962' }}>
              立即註冊
            </Link>
          </Text>
        </div>
        <div style={{ textAlign: 'center', marginTop: isMobile ? '8px' : '12px' }}>
          <Link to="/forgot-password">
            <Text type="secondary" style={{ fontSize: isMobile ? 12 : 13 }}>忘記密碼？</Text>
          </Link>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
