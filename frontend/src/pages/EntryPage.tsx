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
 * @version 3.0.1
 * @date 2026-05-27 — 修正自動 SSO Bridge 成功後 SPA navigate() 的 cookie 競態，改用 window.location.replace 強制整頁刷新
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
// v5.9.4 (2026-04-24) 資安考量：關閉帳密登入機制
// ─────────────────────────────────────────────────────────────────
// 理由：避免暴力破解、credential stuffing、憑證洩漏風險
// 替代方案：Google OAuth / LINE Login SSO（無密碼，由 IdP 處理認證）
// 後端 /api/auth/login endpoint 同步回 410 Gone（見 oauth.py）
// 相關 ADR: docs/adr/0033-disable-password-authentication.md
// 如需重啟帳密登入，請先經資安評估並取消下行註記
const SHOW_PASSWORD_LOGIN = false;
const SHOW_GOOGLE_LOGIN = Boolean(GOOGLE_LOGIN_ENABLED);
const SHOW_LINE_LOGIN = Boolean(LINE_LOGIN_CHANNEL_ID);

const ENV_HINT = IS_AUTH_DISABLED
  ? '開發模式 - 認證已停用，點擊任意處進入'
  : IS_LOCALHOST
    ? '本機開發模式 - 透過 SSO 登入'
    : IS_INTERNAL
      ? '內網環境 - 快速進入'
      : '請使用 Google / LINE 帳號登入';

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
      // 所有登入使用者一律進 /dashboard（admin 要管理請從側邊欄導覽）
      void response;
      navigate(ROUTES.DASHBOARD);
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
      void result;
      // 與 handlePasswordLogin / handleDevModeEntry 一致：
      // 必須 dispatch 通知 useNavigationData 重新讀 localStorage.user_info，
      // 否則 SPA navigate 不會觸發 Layout re-mount，currentUser 永遠保持 null
      // → Header 持續顯示「訪客」（v6.8 5/04 認證鏈漏修一環）
      window.dispatchEvent(new CustomEvent('user-logged-in'));
      navigate(ROUTES.DASHBOARD);
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
          // v6.10.4 (2026-05-21)：opt-in Chrome FedCM 強制（預估 2026 Q3-Q4 後 mandatory）
          // 抑制 GSI_LOGGER warning + 提前適應；副作用：prompt UI 改用 Chrome 系統級 dialog
          use_fedcm_for_prompt: true,
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
    // L48 (2026-05-27)：useEffect 順序顛倒 — 先試 SSO bridge，後看自家 isAuthenticated()
    // 真因：owner 之前在 missive 自己 Google login 過，localStorage.user_info + csrf_token cookie 殘留
    //       → isAuthenticated() 返 true → 跳過 ssoBridge → navigate dashboard → token 過期 → /auth/check 401 → 踢回 login
    // 修法：SSO ck_employee cookie 存在時優先用 SSO（ssoBridge 200 → 取代 missive 自家 token）
    //       SSO 不存在或失敗才看 isAuthenticated()
    //
    // L49.14 (2026-05-28) 內網優化：IS_INTERNAL 或 IS_LOCALHOST 無 SSO 流程，直接跳過 ssoBridge
    //   避免 owner 內網 192.168.50.210:8001/entry 卡 ssoBridge round-trip
    //   (內網沒 ck_employee cookie，呼叫必返 401，純浪費)
    let mounted = true;
    void (async () => {
      // 內網/本機跳過 SSO bridge，直接看 missive 自家 auth state
      const skipSsoBridge = IS_LOCALHOST || IS_INTERNAL;
      const ssoResult = skipSsoBridge ? null : await authService.ssoBridge();
      if (!mounted) return;
      if (ssoResult) {
        logger.info('[SSO-BRIDGE] auto-login succeeded via www.cksurvey.tw cookie');
        window.dispatchEvent(new CustomEvent('user-logged-in'));
        // 🔒 v3.0.1 (2026-05-27) 安全修法：
        // 避免使用 React Router 的 SPA navigate()，因為 cookie 寫入是異步的，
        // 且 SPA 導向不會觸發頁面刷新，容易造成 Zustand store 異步 rehydrate 的 race condition，
        // 從而觸發 useAuthGuard 啟動驗證失敗（/auth/check 返回 401）而被踢回登入頁。
        // 改用 window.location.replace() 強制頁面重載，保證 cookie 同步註冊。
        window.location.replace('/dashboard');
        return;
      }

      // SSO 失敗 / 無 SSO cookie → fallback 看 missive 自家 auth state
      if (authService.isAuthenticated()) {
        navigate(ROUTES.DASHBOARD);
        return;
      }

      // 走原本登入 UI 初始化
      if (SHOW_GOOGLE_LOGIN) {
        initializeGoogleSignIn();
      } else {
        setGoogleReady(true);
      }
      logger.debug('🔐 EntryPage 環境配置:', {
        ENV_TYPE, SHOW_QUICK_ENTRY, SHOW_PASSWORD_LOGIN, SHOW_GOOGLE_LOGIN,
      });
    })();

    return () => { mounted = false; };
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
    if (!window.google) return;

    // v6.10.4 (2026-05-21) FedCM 完整遷移：
    //   1. always render button 作為永久 fallback（FedCM 下舊 isNotDisplayed/isSkippedMoment
    //      會 always return false，不能再依賴 polling）
    //   2. prompt() 仍主動觸發 Chrome FedCM 系統級 dialog 嘗試自動登入
    //   3. callback 內不再 branch 任何 deprecated status method
    const btnContainer = document.getElementById('google-signin-btn');
    if (btnContainer && !btnContainer.hasChildNodes()) {
      window.google.accounts.id.renderButton(btnContainer, {
        theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill',
      });
    }
    // 主動嘗試 FedCM prompt（成功即自動登入；失敗用戶仍能點上面的 button）
    window.google.accounts.id.prompt();
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

        {/* v5.8.0 坤哥意識體入口提示（對齊 Muse 風格對外展示）*/}
        <p
          style={{
            color: '#b8c5d4',
            fontSize: 14,
            textAlign: 'center',
            marginTop: -8,
            marginBottom: 16,
            letterSpacing: 1,
            cursor: 'pointer',
          }}
          onClick={(e) => {
            e.stopPropagation();
            navigate('/kunge');
          }}
        >
          ✨ <strong style={{ color: '#ffd700' }}>坤哥</strong> — Missive 意識體 · 記憶、學習、質疑、進化 →
        </p>

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
