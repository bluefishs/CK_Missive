/**
 * useLineLogin - LINE OAuth 登入邏輯
 *
 * 從 LoginPage.tsx 提取的 LINE Login 重導向處理
 *
 * @version 1.0.0
 * @date 2026-04-05
 */
import { useState } from 'react';
import { LINE_LOGIN_CHANNEL_ID, LINE_LOGIN_REDIRECT_URI } from '../../config/env';

export function useLineLogin(returnUrl: string | null) {
  const [lineLoading, setLineLoading] = useState(false);

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

  return { lineLoading, handleLineLogin };
}
