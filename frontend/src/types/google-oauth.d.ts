/**
 * Google OAuth 型別定義
 *
 * 解決 window.google 的 @ts-ignore 問題
 *
 * @version 1.0.0
 * @date 2026-02-02
 */

interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
  clientId?: string;
}

interface GoogleButtonConfiguration {
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  logo_alignment?: 'left' | 'center';
  width?: number;
  locale?: string;
}

interface GoogleIdConfiguration {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  auto_select?: boolean;
  login_uri?: string;
  native_callback?: (response: GoogleCredentialResponse) => void;
  cancel_on_tap_outside?: boolean;
  prompt_parent_id?: string;
  nonce?: string;
  context?: 'signin' | 'signup' | 'use';
  state_cookie_domain?: string;
  ux_mode?: 'popup' | 'redirect';
  allowed_parent_origin?: string | string[];
  intermediate_iframe_close_callback?: () => void;
  itp_support?: boolean;
  // v6.10.4 (2026-05-21) FedCM 遷移：opt-in Chrome FedCM（強制 mandatory 預估 2026 Q3-Q4）
  // 文件：https://developers.google.com/identity/gsi/web/guides/fedcm-migration
  use_fedcm_for_prompt?: boolean;
}

/**
 * @deprecated FedCM 強制後（2026 Q3-Q4）以下 prompt UI status methods 會 always-return-false：
 *   isDisplayMoment, isDisplayed, isNotDisplayed, isSkippedMoment, isDismissedMoment,
 *   getNotDisplayedReason, getSkippedReason, getDismissedReason, getMomentType
 * FedCM 模式下不需 polling notification，UI 由 Chrome 系統級 dialog handle。
 * 應 always renderButton 作為 fallback，prompt() 僅作主動觸發補強。
 */

interface GoogleAccountsId {
  initialize: (config: GoogleIdConfiguration) => void;
  prompt: (momentListener?: (notification: PromptMomentNotification) => void) => void;
  renderButton: (parent: HTMLElement | null, options: GoogleButtonConfiguration) => void;
  disableAutoSelect: () => void;
  storeCredential: (credential: { id: string; password: string }, callback?: () => void) => void;
  cancel: () => void;
  revoke: (hint: string, callback?: (response: { successful: boolean; error?: string }) => void) => void;
}

interface PromptMomentNotification {
  isDisplayMoment: () => boolean;
  isDisplayed: () => boolean;
  isNotDisplayed: () => boolean;
  getNotDisplayedReason: () =>
    | 'browser_not_supported'
    | 'invalid_client'
    | 'missing_client_id'
    | 'opt_out_or_no_session'
    | 'secure_http_required'
    | 'suppressed_by_user'
    | 'unregistered_origin'
    | 'unknown_reason';
  isSkippedMoment: () => boolean;
  getSkippedReason: () => 'auto_cancel' | 'user_cancel' | 'tap_outside' | 'issuing_failed';
  isDismissedMoment: () => boolean;
  getDismissedReason: () => 'credential_returned' | 'cancel_called' | 'flow_restarted';
  getMomentType: () => 'display' | 'skipped' | 'dismissed';
}

interface GoogleAccounts {
  id: GoogleAccountsId;
}

interface Google {
  accounts: GoogleAccounts;
}

declare global {
  interface Window {
    google?: Google;
  }
}

export {};
