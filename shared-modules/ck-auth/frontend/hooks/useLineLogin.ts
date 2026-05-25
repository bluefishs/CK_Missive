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
    // 前置檢查 1：LINE_CHANNEL_ID 必須存在（production build 空值會導致 State mismatch）
    if (!LINE_LOGIN_CHANNEL_ID) {
      alert('LINE 登入尚未配置 Channel ID，請聯繫系統管理員。');
      return;
    }

    // 前置檢查 2：sessionStorage 跨 origin 隔離 — 若當前 origin ≠ callback origin，
    // 登入回調後讀不到 saved state，必然 mismatch
    try {
      const callbackOrigin = new URL(LINE_LOGIN_REDIRECT_URI).origin;
      if (callbackOrigin !== window.location.origin) {
        alert(
          `LINE 登入必須從 ${callbackOrigin} 發起\n`
          + `當前位址：${window.location.origin}\n\n`
          + `自動跳轉至正確網址。`
        );
        window.location.href = `${callbackOrigin}${window.location.pathname}${window.location.search}`;
        return;
      }
    } catch {
      // URL 解析失敗就放行，讓原流程走錯誤處理
    }

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
