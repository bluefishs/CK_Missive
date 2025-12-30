/**
 * 環境變數配置
 * 統一管理所有環境變數存取，避免 TypeScript 索引簽名錯誤
 */

// 安全獲取環境變數的輔助函數
const getEnvVar = (key: string): string | undefined => {
  return import.meta.env[key] as string | undefined;
};

// API 配置
export const API_BASE_URL = (getEnvVar('VITE_API_BASE_URL') || 'http://localhost:8001') + '/api';
export const VITE_API_BASE_URL = getEnvVar('VITE_API_BASE_URL') || 'http://localhost:8001';

// 認證配置
export const AUTH_DISABLED = getEnvVar('VITE_AUTH_DISABLED') === 'true';
export const GOOGLE_CLIENT_ID = getEnvVar('VITE_GOOGLE_CLIENT_ID') || '';

// 開發環境配置
export const IS_DEV = import.meta.env.DEV === true;
export const NODE_ENV = getEnvVar('NODE_ENV') || 'development';

// 環境變數對象（用於調試）
export const ENV_CONFIG = {
  VITE_AUTH_DISABLED: getEnvVar('VITE_AUTH_DISABLED'),
  VITE_API_BASE_URL: getEnvVar('VITE_API_BASE_URL'),
  VITE_GOOGLE_CLIENT_ID: getEnvVar('VITE_GOOGLE_CLIENT_ID'),
  NODE_ENV: getEnvVar('NODE_ENV'),
  DEV: import.meta.env.DEV,
};

export default {
  API_BASE_URL,
  VITE_API_BASE_URL,
  AUTH_DISABLED,
  GOOGLE_CLIENT_ID,
  IS_DEV,
  NODE_ENV,
  ENV_CONFIG,
};
