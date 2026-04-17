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
 * @version 2.5.0
 * @date 2026-01-13
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button, Spin, App, Tag } from 'antd';
import { GoogleOutlined, LoadingOutlined, LoginOutlined, UserOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import authService from '../services/authService';
import { detectEnvironment, isAuthDisabled, GOOGLE_CLIENT_ID, LINE_LOGIN_CHANNEL_ID } from '../config/env';
import { useLineLogin } from '../hooks';
import { logger } from '../utils/logger';
import './EntryPage.css';

// 使用共用的環境偵測
const ENV_TYPE = detectEnvironment();

// Google OAuth 啟用條件：有效的 Client ID
const GOOGLE_LOGIN_ENABLED =
  GOOGLE_CLIENT_ID &&
  GOOGLE_CLIENT_ID !== 'your-actual-google-client-id.apps.googleusercontent.com';

// 是否為認證停用模式（VITE_AUTH_DISABLED=true）
const IS_AUTH_DISABLED = isAuthDisabled();

// 環境類型判斷
const IS_LOCALHOST = ENV_TYPE === 'localhost';      // 本機開發
const IS_INTERNAL = ENV_TYPE === 'internal';        // 內網 IP
const IS_NGROK_OR_PUBLIC = ENV_TYPE === 'ngrok' || ENV_TYPE === 'public';  // ngrok 或公網

/**
 * 登入選項配置（依環境決定）
 *
 * | 環境          | 快速進入 | 帳密登入 | Google登入 |
 * |--------------|---------|---------|-----------|
 * | localhost    | ✅      | ✅      | ✅        |
 * | internal     | ✅      | ✅      | ❌        |
 * | ngrok/public | ❌      | ✅      | ✅        |
 */
const SHOW_QUICK_ENTRY = IS_AUTH_DISABLED || IS_LOCALHOST || IS_INTERNAL;  // localhost + 內網 顯示快速進入
const SHOW_PASSWORD_LOGIN = true;                                          // 所有環境都有帳密登入
const SHOW_GOOGLE_LOGIN = GOOGLE_LOGIN_ENABLED && (IS_LOCALHOST || IS_NGROK_OR_PUBLIC);  // localhost/ngrok/public 顯示 Google 登入
const SHOW_LINE_LOGIN = Boolean(LINE_LOGIN_CHANNEL_ID);  // LINE Login 已配置即顯示

// 星星組件
interface StarProps {
  className: string;
  style: React.CSSProperties;
}

const Star: React.FC<StarProps> = ({ className, style }) => <div className={`star ${className}`} style={style} />;

// 生成隨機星星
const generateStars = (count: number, className: string): StarProps[] => {
  return Array.from({ length: count }, () => ({
    className,
    style: {
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      animationDelay: `${Math.random() * 3}s`,
      animationDuration: `${2 + Math.random() * 2}s`,
    },
  }));
};

const EntryPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const navigate = useNavigate();

  // LINE Login hook
  const { lineLoading, handleLineLogin } = useLineLogin(null);

  // 預先生成星星
  const stars = useMemo(
    () => ({
      small: generateStars(60, 'star-small'),
      medium: generateStars(35, 'star-medium'),
      large: generateStars(20, 'star-large'),
    }),
    []
  );

  // Google 登入回調處理
  interface GoogleCredentialResponse {
    credential?: string;
  }

  const handleGoogleCallback = useCallback(async (response: GoogleCredentialResponse) => {
    if (response.credential) {
      setLoading(true);
      try {
        const result = await authService.googleLogin(response.credential);
        message.success('登入成功！');

        if (result.user_info.is_admin) {
          navigate(ROUTES.ADMIN_DASHBOARD);
        } else {
          navigate(ROUTES.DASHBOARD);
        }
      } catch (error: unknown) {
        logger.error('Google login failed:', error);
        const errorMessage = error instanceof Error ? error.message : 'Google 登入失敗';
        message.error(errorMessage);
      } finally {
        setLoading(false);
      }
    }
  }, [message, navigate]);

  useEffect(() => {
    // 檢查是否已登入
    if (authService.isAuthenticated()) {
      navigate(ROUTES.DASHBOARD);
      return;
    }

    // 根據環境初始化登入選項
    if (SHOW_GOOGLE_LOGIN) {
      // localhost / ngrok / public：初始化 Google 登入
      initializeGoogleSignIn();
    } else {
      // internal（內網）：不需要 Google 登入，直接準備就緒
      setGoogleReady(true);
    }

    // 日誌：顯示當前環境和登入選項
    logger.debug('🔐 EntryPage 環境配置:', {
      ENV_TYPE,
      SHOW_QUICK_ENTRY,
      SHOW_PASSWORD_LOGIN,
      SHOW_GOOGLE_LOGIN,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps -- initializeGoogleSignIn is stable, adding it causes re-initialization
  }, [navigate]);

  const initializeGoogleSignIn = async () => {
    try {
      // 載入 Google Identity Services API
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

  // 快速進入（localhost、內網 IP 或 AUTH_DISABLED）
  const handleDevModeEntry = async () => {
    if (IS_AUTH_DISABLED) {
      message.info('開發模式 - 快速進入系統（認證已停用）');
    } else if (IS_LOCALHOST) {
      message.info('本機開發模式 - 快速進入系統');
    } else if (IS_INTERNAL) {
      message.info('內網環境 - 快速進入系統');
    }

    setLoading(true);
    try {
      // 從後端獲取當前用戶資訊並儲存到 localStorage
      const userInfo = await authService.getCurrentUser();
      authService.setUserInfo(userInfo);

      // 觸發登入事件
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

  // 觸發 Google 登入
  const handleGoogleLogin = () => {
    if (!SHOW_GOOGLE_LOGIN) {
      message.warning('此環境不支援 Google 登入');
      return;
    }

    if (window.google) {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed()) {
          // 如果 One Tap 無法顯示，使用按鈕模式
          window.google?.accounts.id.renderButton(
            document.getElementById('google-signin-btn'),
            { theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill' }
          );
        }
      });
    }
  };

  // 取得環境標籤顯示
  const getEnvLabel = () => {
    switch (ENV_TYPE) {
      case 'localhost': return { text: 'localhost', color: 'blue' };
      case 'internal': return { text: '內網開發', color: 'orange' };
      case 'ngrok': return { text: 'ngrok', color: 'green' };
      case 'public': return { text: '正式環境', color: 'purple' };
      default: return null;
    }
  };

  const envLabel = getEnvLabel();

  return (
    <div className="entry-page" onClick={SHOW_QUICK_ENTRY && googleReady && !loading ? handleDevModeEntry : undefined}>
      {/* 星空背景 */}
      <div className="stars-container">
        {stars.small.map((star, i) => (
          <Star key={`small-${i}`} {...star} />
        ))}
        {stars.medium.map((star, i) => (
          <Star key={`medium-${i}`} {...star} />
        ))}
        {stars.large.map((star, i) => (
          <Star key={`large-${i}`} {...star} />
        ))}

        {/* 四角星裝飾 */}
        <div className="star-decoration star-decoration-1" />
        <div className="star-decoration star-decoration-2" />
        <div className="star-decoration star-decoration-3" />

        {/* 幾何弧線裝飾 */}
        <svg className="arc-decoration" viewBox="0 0 800 400" preserveAspectRatio="xMidYMid meet">
          <path
            className="arc-line"
            d="M 50 350 Q 400 50 750 350"
            fill="none"
          />
          <path
            className="arc-line arc-line-2"
            d="M 100 320 Q 400 100 700 320"
            fill="none"
          />
        </svg>

        {/* 星座點裝飾 */}
        <svg className="constellation-dots" viewBox="0 0 1000 600">
          {/* 左上星座 */}
          <circle cx="150" cy="120" r="2" className="dot" />
          <circle cx="180" cy="100" r="3" className="dot" />
          <circle cx="220" cy="130" r="2" className="dot" />
          <circle cx="200" cy="160" r="2" className="dot" />
          <line x1="150" y1="120" x2="180" y2="100" className="constellation-line" />
          <line x1="180" y1="100" x2="220" y2="130" className="constellation-line" />
          <line x1="220" y1="130" x2="200" y2="160" className="constellation-line" />

          {/* 右上星座 */}
          <circle cx="750" cy="80" r="2" className="dot" />
          <circle cx="800" cy="120" r="3" className="dot" />
          <circle cx="850" cy="90" r="2" className="dot" />
          <circle cx="820" cy="150" r="2" className="dot" />
          <line x1="750" y1="80" x2="800" y2="120" className="constellation-line" />
          <line x1="800" y1="120" x2="850" y2="90" className="constellation-line" />
          <line x1="800" y1="120" x2="820" y2="150" className="constellation-line" />

          {/* 右下星座 */}
          <circle cx="880" cy="450" r="2" className="dot" />
          <circle cx="920" cy="480" r="3" className="dot" />
          <circle cx="900" cy="520" r="2" className="dot" />
          <line x1="880" y1="450" x2="920" y2="480" className="constellation-line" />
          <line x1="920" y1="480" x2="900" y2="520" className="constellation-line" />
        </svg>
      </div>

      {/* 主內容 */}
      <div className="entry-content">
        {/* 標題 */}
        <h1 className="entry-title">
          <span className="title-white">乾坤測繪</span>
          <span className="title-gold">公文系統入口</span>
        </h1>

        {/* 環境標籤 */}
        {envLabel && (
          <Tag color={envLabel.color} className="env-tag">
            {envLabel.text}
          </Tag>
        )}

        {/* 登入按鈕區域 */}
        <div className="entry-action">
          {loading ? (
            <Spin indicator={<LoadingOutlined style={{ fontSize: 32, color: '#c9a962' }} spin />} />
          ) : googleReady ? (
            <>
              {/* 動態顯示登入選項 */}
              <div className="internal-login-options">
                {/* 快速進入：localhost + internal */}
                {SHOW_QUICK_ENTRY && (
                  <Button
                    className="dev-entry-btn"
                    icon={<LoginOutlined />}
                    size="large"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDevModeEntry();
                    }}
                  >
                    快速進入系統
                  </Button>
                )}

                {/* 帳密登入：所有環境 */}
                {SHOW_PASSWORD_LOGIN && (
                  <Button
                    className="password-login-btn"
                    icon={<UserOutlined />}
                    size="large"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(ROUTES.LOGIN);
                    }}
                  >
                    帳號密碼登入
                  </Button>
                )}

                {/* Google 登入：localhost + ngrok + public */}
                {SHOW_GOOGLE_LOGIN && (
                  <Button
                    id="google-signin-btn"
                    className="google-login-btn"
                    icon={<GoogleOutlined />}
                    size="large"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleGoogleLogin();
                    }}
                  >
                    使用 Google 帳號登入
                  </Button>
                )}

                {/* LINE 登入：已配置即顯示 */}
                {SHOW_LINE_LOGIN && (
                  <Button
                    className="line-login-btn"
                    size="large"
                    loading={lineLoading}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleLineLogin();
                    }}
                  >
                    使用 LINE 帳號登入
                  </Button>
                )}
              </div>

              {/* 環境提示 */}
              <p className="entry-hint">
                {IS_AUTH_DISABLED
                  ? '開發模式 - 認證已停用，點擊任意處進入'
                  : IS_LOCALHOST
                    ? '本機開發模式 - 三種登入方式可用'
                    : IS_INTERNAL
                      ? '內網環境 - 快速進入或帳密登入'
                      : '請選擇登入方式'}
              </p>
            </>
          ) : (
            <Spin indicator={<LoadingOutlined style={{ fontSize: 24, color: '#c9a962' }} spin />}>
              <span style={{ color: '#c9a962', marginTop: 8, display: 'block' }}>載入中...</span>
            </Spin>
          )}
        </div>
      </div>
    </div>
  );
};

export default EntryPage;
