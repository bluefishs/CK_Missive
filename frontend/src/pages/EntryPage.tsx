/**
 * EntryPage.tsx - 系統入口頁面
 *
 * 設計風格：深藍星空背景、金色強調
 * 功能：智慧環境偵測登入機制
 *   - localhost / 公網域名：Google OAuth 登入
 *   - 內網 IP：開發模式快速進入
 *   - ngrok 隧道：Google OAuth 登入
 *
 * @version 2.2.0
 * @date 2026-01-11
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button, Spin, App, Tag } from 'antd';
import { GoogleOutlined, LoadingOutlined, LoginOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import { detectEnvironment, isAuthDisabled, GOOGLE_CLIENT_ID } from '../config/env';
import './EntryPage.css';

// 使用共用的環境偵測
const ENV_TYPE = detectEnvironment();

// Google OAuth 啟用條件：有效的 Client ID + 非內網環境
const GOOGLE_LOGIN_ENABLED =
  GOOGLE_CLIENT_ID &&
  GOOGLE_CLIENT_ID !== 'your-actual-google-client-id.apps.googleusercontent.com' &&
  ENV_TYPE !== 'internal';

// 是否為內網開發模式
const IS_INTERNAL_DEV = ENV_TYPE === 'internal';

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
  const handleGoogleCallback = useCallback(async (response: any) => {
    if (response.credential) {
      setLoading(true);
      try {
        const result = await authService.googleLogin(response.credential);
        message.success('登入成功！');

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
            message.error('您的帳戶尚未通過管理者驗證，請聯絡管理者。');
          } else if (errorMessage.includes('停用') || errorMessage.includes('suspended')) {
            message.error('您的帳戶已被停用，請聯絡管理者。');
          } else {
            message.error('登入被拒絕：' + errorMessage);
          }
        } else {
          message.error(errorMessage);
        }
      } finally {
        setLoading(false);
      }
    }
  }, [message, navigate]);

  useEffect(() => {
    // 使用共用的認證停用判斷（已包含內網 IP 檢測）
    const authDisabled = isAuthDisabled();

    // 內網開發模式或認證停用：直接顯示快速進入按鈕
    if (authDisabled) {
      setGoogleReady(true);
      return;
    }

    // 檢查是否已登入
    if (authService.isAuthenticated()) {
      navigate('/dashboard');
      return;
    }

    // 初始化 Google 登入（僅限 localhost、公網域名、ngrok）
    if (GOOGLE_LOGIN_ENABLED) {
      initializeGoogleSignIn();
    } else {
      setGoogleReady(true);
    }
  }, [navigate]);

  const initializeGoogleSignIn = async () => {
    try {
      // 載入 Google Identity Services API
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

  // 內網快速進入（開發模式）
  const handleDevModeEntry = () => {
    message.info('內網開發模式 - 快速進入系統');
    navigate('/dashboard');
  };

  // 觸發 Google 登入
  const handleGoogleLogin = () => {
    // 使用共用的認證停用判斷
    const authDisabled = isAuthDisabled();

    // 內網開發模式或認證停用：快速進入
    if (authDisabled) {
      handleDevModeEntry();
      return;
    }

    if (!GOOGLE_LOGIN_ENABLED) {
      message.warning('Google 登入尚未設定，請聯絡管理員');
      return;
    }

    // @ts-ignore
    if (window.google) {
      // @ts-ignore
      window.google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed()) {
          // 如果 One Tap 無法顯示，使用按鈕模式
          // @ts-ignore
          window.google.accounts.id.renderButton(
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
    <div className="entry-page" onClick={googleReady && !loading ? handleGoogleLogin : undefined}>
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
              {IS_INTERNAL_DEV ? (
                // 內網開發模式：顯示快速進入按鈕
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
              ) : (
                // 其他環境：Google 登入
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
              <p className="entry-hint">
                {IS_INTERNAL_DEV
                  ? '內網開發模式 - 點擊進入系統'
                  : '點擊畫面任意處或按鈕開始'}
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
