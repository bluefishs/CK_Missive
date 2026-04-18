/**
 * EntryPage.tsx - 系統入口頁面
 *
 * 設計風格：深藍星空背景、金色強調
 * 功能：智慧環境偵測登入機制
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
 * @version 3.0.0
 * @date 2026-04-18 — 從 506L 拆分為 3 子檔（StarrySky / LoginPanel / 本檔），邏輯保持不動
 */

import React, { useState, useEffect, useCallback } from 'react';
import { App, Tag, Form } from 'antd';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import authService, { MFARequiredError } from '../services/authService';
import { detectEnvironment, isAuthDisabled, GOOGLE_CLIENT_ID, LINE_LOGIN_CHANNEL_ID } from '../config/env';
import { useLineLogin } from '../hooks';
import { logger } from '../utils/logger';
import StarrySky from './entry/StarrySky';
import LoginPanel from './entry/LoginPanel';
import './EntryPage.css';

// ── 環境偵測（常數） ──

const ENV_TYPE = detectEnvironment();

const GOOGLE_LOGIN_ENABLED =
  GOOGLE_CLIENT_ID &&
  GOOGLE_CLIENT_ID !== 'your-actual-google-client-id.apps.googleusercontent.com';

const IS_AUTH_DISABLED = isAuthDisabled();
const IS_LOCALHOST = ENV_TYPE === 'localhost';
const IS_INTERNAL = ENV_TYPE === 'internal';
const IS_NGROK_OR_PUBLIC = ENV_TYPE === 'ngrok' || ENV_TYPE === 'public';

const SHOW_QUICK_ENTRY = IS_AUTH_DISABLED || IS_LOCALHOST || IS_INTERNAL;
const SHOW_PASSWORD_LOGIN = true;
const SHOW_GOOGLE_LOGIN = Boolean(GOOGLE_LOGIN_ENABLED) && (IS_LOCALHOST || IS_NGROK_OR_PUBLIC);
const SHOW_LINE_LOGIN = Boolean(LINE_LOGIN_CHANNEL_ID);

const ENV_HINT = IS_AUTH_DISABLED
  ? '開發模式 - 認證已停用，點擊任意處進入'
  : IS_LOCALHOST
    ? '本機開發模式 - 三種登入方式可用'
    : IS_INTERNAL
      ? '內網環境 - 快速進入或帳密登入'
      : '請選擇登入方式';

const getEnvLabel = () => {
  switch (ENV_TYPE) {
    case 'localhost': return { text: 'localhost', color: 'blue' };
    case 'internal': return { text: '內網開發', color: 'orange' };
    case 'ngrok': return { text: 'ngrok', color: 'green' };
    case 'public': return { text: '正式環境', color: 'purple' };
    default: return null;
  }
};

const EntryPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const [googleAvailable, setGoogleAvailable] = useState(true);
  // 公網/ngrok 預設展開帳密表單（主要登入方式）；localhost/internal 預設收合（有快速進入）
  const [showLoginForm, setShowLoginForm] = useState(IS_NGROK_OR_PUBLIC);
  const [loginError, setLoginError] = useState('');
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const { lineLoading, handleLineLogin } = useLineLogin(null);

  // ── Handlers ──

  const handlePasswordLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    setLoginError('');
    try {
      const response = await authService.login(values);
      message.success('登入成功！');
      window.dispatchEvent(new CustomEvent('user-logged-in'));
      navigate(response.user_info.is_admin ? ROUTES.ADMIN_DASHBOARD : ROUTES.DASHBOARD);
    } catch (error: unknown) {
      if (error instanceof MFARequiredError) {
        message.info('請完成雙因素認證');
        navigate(ROUTES.MFA_VERIFY, { state: { mfa_token: error.mfa_token } });
        return;
      }
      const msg = error instanceof Error ? error.message : '登入失敗，請檢查帳號密碼';
      setLoginError(msg);
    } finally {
      setLoading(false);
    }
  };

  interface GoogleCredentialResponse { credential?: string }

  const handleGoogleCallback = useCallback(async (response: GoogleCredentialResponse) => {
    if (!response.credential) return;
    setLoading(true);
    try {
      const result = await authService.googleLogin(response.credential);
      message.success('登入成功！');
      navigate(result.user_info.is_admin ? ROUTES.ADMIN_DASHBOARD : ROUTES.DASHBOARD);
    } catch (error: unknown) {
      logger.error('Google login failed:', error);
      message.error(error instanceof Error ? error.message : 'Google 登入失敗');
    } finally {
      setLoading(false);
    }
  }, [message, navigate]);

  const initializeGoogleSignIn = useCallback(() => {
    // 5 秒超時 — Google API 不可達（防火牆/GFW）時自動降級
    const timeout = setTimeout(() => {
      logger.warn('Google Sign-In API timeout (5s), hiding Google button');
      setGoogleAvailable(false);
      setGoogleReady(true);
    }, 5000);

    const loadGoogle = () => {
      clearTimeout(timeout);
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

    try {
      if (document.querySelector('script[src="https://accounts.google.com/gsi/client"]')) {
        loadGoogle();
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = loadGoogle;
      script.onerror = () => {
        clearTimeout(timeout);
        logger.warn('Google Sign-In API failed to load, hiding Google button');
        setGoogleAvailable(false);
        setGoogleReady(true);
      };
      document.head.appendChild(script);
    } catch (error) {
      clearTimeout(timeout);
      logger.error('Failed to initialize Google Sign-In:', error);
      setGoogleAvailable(false);
      setGoogleReady(true);
    }
  }, [handleGoogleCallback]);

  useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate(ROUTES.DASHBOARD);
      return;
    }
    if (SHOW_GOOGLE_LOGIN) {
      initializeGoogleSignIn();
    } else {
      setGoogleReady(true);
    }
    logger.debug('🔐 EntryPage 環境配置:', {
      ENV_TYPE, SHOW_QUICK_ENTRY, SHOW_PASSWORD_LOGIN, SHOW_GOOGLE_LOGIN,
    });
  }, [navigate, initializeGoogleSignIn]);

  const handleDevModeEntry = async () => {
    if (IS_AUTH_DISABLED) message.info('開發模式 - 快速進入系統（認證已停用）');
    else if (IS_LOCALHOST) message.info('本機開發模式 - 快速進入系統');
    else if (IS_INTERNAL) message.info('內網環境 - 快速進入系統');

    setLoading(true);
    try {
      const userInfo = await authService.getCurrentUser();
      authService.setUserInfo(userInfo);
      window.dispatchEvent(new CustomEvent('user-logged-in'));
      message.success(`歡迎, ${userInfo.full_name || userInfo.username}!`);
      navigate(ROUTES.DASHBOARD);
    } catch (error: unknown) {
      logger.error('Quick entry failed:', error);
      message.error('快速進入失敗，請確認後端服務是否啟動');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    if (!SHOW_GOOGLE_LOGIN) {
      message.warning('此環境不支援 Google 登入');
      return;
    }
    if (window.google) {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed()) {
          window.google?.accounts.id.renderButton(
            document.getElementById('google-signin-btn'),
            { theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill' },
          );
        }
      });
    }
  };

  const envLabel = getEnvLabel();

  return (
    <div
      className="entry-page"
      onClick={SHOW_QUICK_ENTRY && googleReady && !loading ? handleDevModeEntry : undefined}
    >
      <StarrySky />

      <div className="entry-content">
        <h1 className="entry-title">
          <span className="title-white">乾坤測繪</span>
          <span className="title-gold">公文系統入口</span>
        </h1>

        {envLabel && (
          <Tag color={envLabel.color} className="env-tag">
            {envLabel.text}
          </Tag>
        )}

        <div className="entry-action">
          <LoginPanel
            loading={loading}
            googleReady={googleReady}
            googleAvailable={googleAvailable}
            lineLoading={lineLoading}
            showLoginForm={showLoginForm}
            loginError={loginError}
            form={form}
            flags={{
              quickEntry: SHOW_QUICK_ENTRY,
              password: SHOW_PASSWORD_LOGIN,
              google: SHOW_GOOGLE_LOGIN,
              line: SHOW_LINE_LOGIN,
            }}
            envHint={ENV_HINT}
            onQuickEntry={handleDevModeEntry}
            onToggleLoginForm={() => setShowLoginForm(true)}
            onPasswordLogin={handlePasswordLogin}
            onGoogleLogin={handleGoogleLogin}
            onLineLogin={handleLineLogin}
          />
        </div>
      </div>
    </div>
  );
};

export default EntryPage;
