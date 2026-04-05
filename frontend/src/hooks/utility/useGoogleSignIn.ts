/**
 * useGoogleSignIn - Google OAuth 登入邏輯
 *
 * 從 LoginPage.tsx 提取的 Google Sign-In 初始化與回調處理
 *
 * @version 1.0.0
 * @date 2026-04-05
 */
import { useState, useCallback } from 'react';
import { App } from 'antd';
import authService, { MFARequiredError } from '../../services/authService';
import { GOOGLE_CLIENT_ID } from '../../config/env';
import { logger } from '../../utils/logger';

interface GoogleCredentialResponse {
  credential?: string;
}

interface UseGoogleSignInOptions {
  onSuccess: (targetUrl: string) => void;
  onMFARequired: (mfa_token: string) => void;
  returnUrl: string | null;
}

export function useGoogleSignIn(options: UseGoogleSignInOptions) {
  const { message } = App.useApp();
  const { onSuccess, onMFARequired, returnUrl } = options;

  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const [error, setError] = useState<string>('');

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
        onSuccess(targetUrl);
      } catch (error: unknown) {
        // MFA 流程：Google 認證成功但需要雙因素認證
        if (error instanceof MFARequiredError) {
          message.info('請完成雙因素認證');
          onMFARequired(error.mfa_token);
          return;
        }
        logger.error('Google login failed:', error);
        const errorMessage = error instanceof Error ? error.message : 'Google 登入失敗';
        setError(errorMessage);
      } finally {
        setGoogleLoading(false);
      }
    }
  }, [message, onSuccess, onMFARequired, returnUrl]);

  const initializeGoogleSignIn = useCallback(async () => {
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
  }, [handleGoogleCallback]);

  const handleGoogleLogin = useCallback(() => {
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
  }, []);

  return {
    googleLoading,
    googleReady,
    googleError: error,
    setGoogleError: setError,
    initializeGoogleSignIn,
    handleGoogleLogin,
  };
}
