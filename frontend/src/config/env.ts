/**
 * 環境變數配置
 * 統一管理所有環境變數存取
 *
 * @version 2.1.0
 * @date 2026-01-13
 */

// 安全獲取環境變數的輔助函數
const getEnvVar = (key: string): string | undefined => {
  return import.meta.env[key] as string | undefined;
};

// ============================================================================
// API 配置
// ============================================================================
// 相對路徑 '/api' 瀏覽器自動用同 origin — 內網 / 公網 / CF Tunnel 皆通用
// 僅當明確設 VITE_API_BASE_URL 時才走絕對 URL（跨域 / SSR 情境）
const _explicitBase = getEnvVar('VITE_API_BASE_URL');
export const API_BASE_URL = _explicitBase ? `${_explicitBase}/api` : '/api';
export const VITE_API_BASE_URL = _explicitBase || '';

// ============================================================================
// 內網 IP 模式 (Single Source of Truth)
// ============================================================================
/**
 * 內網 IP 位址匹配模式
 * - 10.0.0.0 - 10.255.255.255 (Class A)
 * - 172.16.0.0 - 172.31.255.255 (Class B)
 * - 192.168.0.0 - 192.168.255.255 (Class C)
 *
 * 此常數為唯一來源，其他模組應從此處匯入使用
 */
export const INTERNAL_IP_PATTERNS: RegExp[] = [
  /^10\./,                           // 10.0.0.0 - 10.255.255.255
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,  // 172.16.0.0 - 172.31.255.255
  /^192\.168\./                       // 192.168.0.0 - 192.168.255.255
];

/**
 * 檢查 hostname 是否為內網 IP
 */
export const isInternalIPAddress = (hostname: string): boolean => {
  return INTERNAL_IP_PATTERNS.some(pattern => pattern.test(hostname));
};

// ============================================================================
// 認證配置
// ============================================================================
export const AUTH_DISABLED_ENV = getEnvVar('VITE_AUTH_DISABLED') === 'true';
export const GOOGLE_CLIENT_ID = getEnvVar('VITE_GOOGLE_CLIENT_ID') || '';
export const LINE_LOGIN_CHANNEL_ID = getEnvVar('VITE_LINE_LOGIN_CHANNEL_ID') || '';
export const LINE_LOGIN_REDIRECT_URI = getEnvVar('VITE_LINE_LOGIN_REDIRECT_URI') || `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/line/callback`;
export const LINE_BIND_REDIRECT_URI = `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/line/bind-callback`;

/**
 * 檢測環境類型
 * - localhost: 本機開發（支援快速進入、帳密、Google）
 * - internal: 內網存取（支援快速進入、帳密）
 * - ngrok: ngrok 隧道（帳密 + Google）
 * - public: 公網存取（帳密 + Google）
 */
export type EnvironmentType = 'localhost' | 'internal' | 'ngrok' | 'public';

export const detectEnvironment = (): EnvironmentType => {
  if (typeof window === 'undefined') return 'localhost';

  const hostname = window.location.hostname;

  // localhost/127.0.0.1
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'localhost';
  }

  // ngrok 隧道
  if (hostname.endsWith('.ngrok.io') || hostname.endsWith('.ngrok-free.app')) {
    return 'ngrok';
  }

  // 內網 IP 範圍（使用共用常數）
  if (isInternalIPAddress(hostname)) {
    return 'internal';
  }

  // 公網
  return 'public';
};

/**
 * 檢查是否為內網環境（localhost 或內網 IP）
 */
export const isInternalNetwork = (): boolean => {
  const env = detectEnvironment();
  return env === 'localhost' || env === 'internal';
};

/**
 * 檢查是否完全停用認證（僅當 VITE_AUTH_DISABLED=true）
 * 注意：這不同於「內網免認證」，內網模式仍需通過快速進入取得 user_info
 */
export const isAuthDisabled = (): boolean => {
  return AUTH_DISABLED_ENV;
};

/**
 * P-58 (2026-05-07)：判斷「是否套用 dev superuser mock」。
 *
 * 改寫：只有「VITE_AUTH_DISABLED=true 且 localStorage 沒有真實 user_info」時才套 mock。
 * 一旦真用戶登入（即使是 dev 機台），他的 role / permissions 就要被尊重。
 *
 * Bug：先前 isAuthDisabled() 短路所有 hasPermission / filter / isAdmin，導致內網
 * 用戶以「一般使用者」帳號登入後仍看到全部選單（dev mode 強制 superuser 覆蓋）。
 */
export const shouldUseDevMockUser = (): boolean => {
  if (!AUTH_DISABLED_ENV) return false;
  if (typeof window === 'undefined') return AUTH_DISABLED_ENV;
  try {
    const stored = window.localStorage.getItem('user_info');
    return !stored;
  } catch {
    return AUTH_DISABLED_ENV;
  }
};

// 向後相容
export const AUTH_DISABLED = AUTH_DISABLED_ENV;
export const isInternalIP = isInternalNetwork;

// ============================================================================
// 開發環境配置
// ============================================================================
export const IS_DEV = import.meta.env.DEV === true;
export const NODE_ENV = getEnvVar('NODE_ENV') || 'development';

// 環境變數對象（用於調試）
export const ENV_CONFIG = {
  VITE_AUTH_DISABLED: getEnvVar('VITE_AUTH_DISABLED'),
  VITE_API_BASE_URL: getEnvVar('VITE_API_BASE_URL'),
  VITE_GOOGLE_CLIENT_ID: getEnvVar('VITE_GOOGLE_CLIENT_ID'),
  VITE_LINE_LOGIN_CHANNEL_ID: getEnvVar('VITE_LINE_LOGIN_CHANNEL_ID'),
  NODE_ENV: getEnvVar('NODE_ENV'),
  DEV: import.meta.env.DEV,
};

export default {
  API_BASE_URL,
  VITE_API_BASE_URL,
  AUTH_DISABLED,
  AUTH_DISABLED_ENV,
  GOOGLE_CLIENT_ID,
  LINE_LOGIN_CHANNEL_ID,
  LINE_LOGIN_REDIRECT_URI,
  LINE_BIND_REDIRECT_URI,
  IS_DEV,
  NODE_ENV,
  ENV_CONFIG,
  // 內網 IP 常數
  INTERNAL_IP_PATTERNS,
  // 函數
  isInternalNetwork,
  isInternalIP,
  isInternalIPAddress,
  isAuthDisabled,
  shouldUseDevMockUser,
  detectEnvironment,
};
