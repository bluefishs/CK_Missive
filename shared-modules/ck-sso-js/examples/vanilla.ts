/**
 * Example: 純 TS / Vue / Svelte / vanilla 整合 ck-sso-js
 */
import { attemptSSOBridge, resetSSOBridgeState } from 'ck-sso-js';

const API_BASE_URL = 'https://lvrland.cksurvey.tw/api';

export async function tryAutoLogin(): Promise<boolean> {
  const result = await attemptSSOBridge({
    apiBaseURL: API_BASE_URL,
    onSuccess: () => {
      // 不要預設 reload — 給 SPA 路由用
      window.dispatchEvent(new CustomEvent('user-logged-in'));
      window.location.href = '/dashboard';
    },
  });

  if (!result.ok) {
    console.log('[SSO] auto-login failed:', result.reason, result.status);
    // 顯示原本 LINE/Google 登入 UI
  }
  return result.ok;
}

// 「重試 SSO」按鈕 handler
export function onClickRetrySSO(): void {
  resetSSOBridgeState();
  void tryAutoLogin();
}
