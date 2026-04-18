/**
 * LoginPanel — 登入按鈕 + 內嵌帳密表單
 *
 * 從 EntryPage.tsx 拆分（v1.0 2026-04-18）
 * 純 presentation，所有狀態/handler 由 parent 傳入。
 */
import React from 'react';
import { Button, Spin, Input, Form, type FormInstance } from 'antd';
import { GoogleOutlined, LoadingOutlined, LoginOutlined, UserOutlined, LockOutlined } from '@ant-design/icons';

export interface LoginFlags {
  quickEntry: boolean;
  password: boolean;
  google: boolean;
  line: boolean;
}

interface LoginPanelProps {
  loading: boolean;
  googleReady: boolean;
  googleAvailable: boolean;
  lineLoading: boolean;
  showLoginForm: boolean;
  loginError: string;
  form: FormInstance;
  flags: LoginFlags;
  envHint: string;
  onQuickEntry: () => void;
  onToggleLoginForm: () => void;
  onPasswordLogin: (values: { username: string; password: string }) => void;
  onGoogleLogin: () => void;
  onLineLogin: () => void;
}

const LoginPanel: React.FC<LoginPanelProps> = ({
  loading, googleReady, googleAvailable, lineLoading, showLoginForm, loginError, form,
  flags, envHint,
  onQuickEntry, onToggleLoginForm, onPasswordLogin, onGoogleLogin, onLineLogin,
}) => {
  if (loading) {
    return (
      <Spin indicator={<LoadingOutlined style={{ fontSize: 32, color: '#c9a962' }} spin />} />
    );
  }

  if (!googleReady) {
    return (
      <Spin indicator={<LoadingOutlined style={{ fontSize: 24, color: '#c9a962' }} spin />}>
        <span style={{ color: '#c9a962', marginTop: 8, display: 'block' }}>載入中...</span>
      </Spin>
    );
  }

  return (
    <>
      <div className="internal-login-options">
        {/* 快速進入：localhost + internal */}
        {flags.quickEntry && (
          <Button
            className="dev-entry-btn"
            icon={<LoginOutlined />}
            size="large"
            onClick={(e) => { e.stopPropagation(); onQuickEntry(); }}
          >
            快速進入系統
          </Button>
        )}

        {/* 帳密登入：按鈕 */}
        {flags.password && !showLoginForm && (
          <Button
            className="password-login-btn"
            icon={<UserOutlined />}
            size="large"
            onClick={(e) => { e.stopPropagation(); onToggleLoginForm(); }}
          >
            帳號密碼登入
          </Button>
        )}

        {/* 帳密登入：內嵌表單 */}
        {showLoginForm && (
          <div className="inline-login-form" onClick={(e) => e.stopPropagation()}>
            {loginError && (
              <div style={{ color: '#ff4d4f', fontSize: 13, marginBottom: 8, textAlign: 'center' }}>
                {loginError}
              </div>
            )}
            <Form form={form} onFinish={onPasswordLogin} layout="vertical" size="large">
              <Form.Item
                name="username"
                rules={[{ required: true, message: '請輸入帳號' }]}
                style={{ marginBottom: 12 }}
              >
                <Input
                  prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.5)' }} />}
                  placeholder="帳號或電子郵件"
                  autoComplete="username"
                  className="entry-input"
                />
              </Form.Item>
              <Form.Item
                name="password"
                rules={[{ required: true, message: '請輸入密碼' }]}
                style={{ marginBottom: 16 }}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.5)' }} />}
                  placeholder="密碼"
                  autoComplete="current-password"
                  className="entry-input"
                />
              </Form.Item>
              <Button className="dev-entry-btn" htmlType="submit" loading={loading} block size="large">
                登入
              </Button>
            </Form>
          </div>
        )}

        {/* Google 登入：僅在 API 可達時顯示 */}
        {flags.google && googleAvailable && (
          <Button
            id="google-signin-btn"
            className="google-login-btn"
            icon={<GoogleOutlined />}
            size="large"
            onClick={(e) => { e.stopPropagation(); onGoogleLogin(); }}
          >
            使用 Google 帳號登入
          </Button>
        )}

        {/* LINE 登入 */}
        {flags.line && (
          <Button
            className="line-login-btn"
            size="large"
            loading={lineLoading}
            onClick={(e) => { e.stopPropagation(); onLineLogin(); }}
          >
            使用 LINE 帳號登入
          </Button>
        )}
      </div>

      {/* 環境提示 */}
      <p className="entry-hint">{envHint}</p>
    </>
  );
};

export default LoginPanel;
