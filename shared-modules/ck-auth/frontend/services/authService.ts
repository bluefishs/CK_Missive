/**
 * 認證服務 - 處理使用者登入、登出、權限檢查等功能
 *
 * @version 2.0.0
 * @date 2026-02-07
 *
 * 變更記錄：
 * - v2.0.0: httpOnly cookie 認證遷移
 *   - access_token 不再存入 localStorage（由後端 Set-Cookie 設定 httpOnly cookie）
 *   - user_info 仍保留在 localStorage（非敏感資料）
 *   - refresh_token 仍保留在 localStorage（向後相容過渡期）
 *   - isAuthenticated() 改為檢查 user_info + /auth/check 端點
 *   - axios 實例啟用 withCredentials
 * - v1.3.0: 統一使用 types/api.ts 的 User 型別 (SSOT 架構)
 * - v1.2.0: 初版
 */
import axios, { AxiosError, AxiosResponse } from 'axios';
import { isAuthDisabled } from '../config/env';
import { API_BASE_URL, getCookie } from '../api/client';
import { AUTH_ENDPOINTS, ADMIN_USER_MANAGEMENT_ENDPOINTS } from '../api/endpoints';
import { logger } from '../utils/logger';
import { User } from '../types/api';

// Token 相關常數
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_INFO_KEY = 'user_info';

// 類型定義
export interface LoginRequest {
  username: string;
  password: string;
}

export interface GoogleAuthRequest {
  credential: string;
}

export interface LineAuthRequest {
  code: string;
  state?: string;
  redirect_uri?: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

/**
 * 使用者資訊型別
 *
 * 基於 types/api.ts 的 User 型別，擴展認證相關欄位
 * 這確保了 SSOT (Single Source of Truth) 架構
 */
export interface UserInfo extends User {
  // 認證特定欄位（可能由後端 TokenResponse 提供）
  role: string;           // 覆寫為必填
  login_count: number;    // 覆寫為必填
  email_verified: boolean; // 覆寫為必填
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  user_info: UserInfo;
  // MFA 相關欄位
  mfa_required?: boolean;
  mfa_token?: string;
}

/**
 * MFA 需要驗證的錯誤
 * 當登入成功但需要 MFA 驗證時拋出
 */
export class MFARequiredError extends Error {
  public readonly mfa_token: string;

  constructor(mfaToken: string) {
    super('MFA 驗證必要');
    this.name = 'MFARequiredError';
    this.mfa_token = mfaToken;
  }
}

export interface JwtPayload {
  sub: string;
  email: string;
  exp: number;
  iat: number;
  jti: string;
}

class AuthService {
  private static instance: AuthService;
  private axios = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    withCredentials: true,  // 啟用 cookie 跨域傳送（httpOnly cookie 認證）
  });

  constructor() {
    // 跨分頁認證同步：監聽其他分頁的 localStorage 變化
    if (typeof window !== 'undefined') {
      window.addEventListener('storage', (event) => {
        if (event.key === USER_INFO_KEY) {
          if (event.newValue === null) {
            // 其他分頁已登出
            logger.info('[Auth] 偵測到其他分頁登出，同步清除認證');
            window.location.href = '/login';
          }
        }
      });
    }

    // 添加請求攔截器：向後相容 Authorization header + CSRF token
    this.axios.interceptors.request.use(
      config => {
        // 向後相容：仍從 localStorage 讀取 token（過渡期）
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // 附加 CSRF token（非安全方法）
        const method = config.method?.toUpperCase() || '';
        if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
          const csrfToken = getCookie('csrf_token');
          if (csrfToken) {
            config.headers['X-CSRF-Token'] = csrfToken;
          }
        }

        return config;
      },
      error => {
        return Promise.reject(error);
      }
    );

    // 添加回應攔截器，處理 401 錯誤
    this.axios.interceptors.response.use(
      response => response,
      async error => {
        if (error.response?.status === 401) {
          const authDisabled = isAuthDisabled();

          if (!authDisabled) {
            // 只有在非開發模式下才清除認證資訊和重導向
            this.clearAuth();
            window.location.href = '/login';
          } else {
            logger.debug('Development mode: Ignoring 401 error for auth bypass');
          }
        }
        return Promise.reject(error);
      }
    );
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  /**
   * 傳統帳密登入
   *
   * v2.1.0: 支援 MFA 流程
   * 當後端回傳 mfa_required: true 時，拋出 MFARequiredError，
   * 呼叫端需攔截此錯誤並導向 MFA 驗證頁面。
   */
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response: AxiosResponse<TokenResponse> = await this.axios.post(AUTH_ENDPOINTS.LOGIN, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    // MFA 流程：密碼正確但需要 TOTP 驗證
    if (response.data.mfa_required && response.data.mfa_token) {
      throw new MFARequiredError(response.data.mfa_token);
    }

    this.saveAuthData(response.data);
    return response.data;
  }

  /**
   * Google OAuth 登入
   *
   * v2.1.0: 支援 MFA 流程
   */
  async googleLogin(credential: string): Promise<TokenResponse> {
    const response: AxiosResponse<TokenResponse> = await this.axios.post(AUTH_ENDPOINTS.GOOGLE, {
      credential,
    });

    // MFA 流程：Google 認證成功但需要 TOTP 驗證
    if (response.data.mfa_required && response.data.mfa_token) {
      throw new MFARequiredError(response.data.mfa_token);
    }

    this.saveAuthData(response.data);
    return response.data;
  }

  /**
   * LINE Login OAuth callback
   *
   * 將 authorization code 傳送至後端交換 token
   */
  async lineLogin(code: string, redirectUri?: string): Promise<TokenResponse> {
    const response: AxiosResponse<TokenResponse> = await this.axios.post(AUTH_ENDPOINTS.LINE_CALLBACK, {
      code,
      redirect_uri: redirectUri,
    });

    // MFA 流程
    if (response.data.mfa_required && response.data.mfa_token) {
      throw new MFARequiredError(response.data.mfa_token);
    }

    this.saveAuthData(response.data);
    return response.data;
  }

  /**
   * 綁定 LINE 帳號 (已登入狀態)
   */
  async bindLine(code: string, redirectUri?: string): Promise<{ success: boolean; message: string }> {
    const response = await this.axios.post(AUTH_ENDPOINTS.LINE_BIND, {
      code,
      redirect_uri: redirectUri,
    });
    return response.data;
  }

  /**
   * 解除 LINE 帳號綁定
   */
  async unbindLine(): Promise<{ success: boolean; message: string }> {
    const response = await this.axios.post(AUTH_ENDPOINTS.LINE_UNBIND, {});
    return response.data;
  }

  /**
   * 使用者註冊
   */
  async register(userData: RegisterRequest): Promise<UserInfo> {
    const response: AxiosResponse<UserInfo> = await this.axios.post(AUTH_ENDPOINTS.REGISTER, userData);

    return response.data;
  }

  /**
   * 登出
   */
  async logout(): Promise<void> {
    // 在開發模式下仍然嘗試調用 API，但不處理錯誤
    const authDisabled = isAuthDisabled();

    try {
      await this.axios.post(AUTH_ENDPOINTS.LOGOUT);
    } catch (error) {
      if (authDisabled) {
        logger.debug('🔒 Auth disabled - ignoring logout API error');
      } else {
        logger.error('Logout request failed:', error);
      }
    } finally {
      this.clearAuth();
    }
  }

  /**
   * 取得當前使用者資訊 (POST-only 安全模式)
   */
  async getCurrentUser(): Promise<UserInfo> {
    const response: AxiosResponse<UserInfo> = await this.axios.post(AUTH_ENDPOINTS.ME, {});
    return response.data;
  }

  /**
   * 檢查認證狀態 (POST-only 安全模式)
   */
  async checkAuthStatus(): Promise<{ authenticated: boolean; user?: UserInfo }> {
    const response = await this.axios.post(AUTH_ENDPOINTS.CHECK, {});
    return response.data;
  }

  /**
   * 檢查權限
   */
  async checkPermission(permission: string, resource?: string): Promise<boolean> {
    try {
      const response = await this.axios.post(ADMIN_USER_MANAGEMENT_ENDPOINTS.PERMISSIONS_CHECK, {
        permission,
        resource,
      });
      return response.data.granted;
    } catch (error) {
      logger.error('Permission check failed:', error);
      return false;
    }
  }

  /**
   * 儲存認證資料
   *
   * v2.0.0 變更:
   * - access_token 不再存入 localStorage（由後端 Set-Cookie 設定 httpOnly cookie）
   * - user_info 仍保留在 localStorage（非敏感資料，供前端 UI 使用）
   * - refresh_token 仍保留在 localStorage（向後相容過渡期）
   */
  private saveAuthData(tokenResponse: TokenResponse): void {
    // access_token 由後端 httpOnly cookie 管理，不再存入 localStorage
    // 保留 user_info（非敏感資料）
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(tokenResponse.user_info));

    // 向後相容過渡期：仍保留 refresh_token
    if (tokenResponse.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokenResponse.refresh_token);
    }
  }

  /**
   * 清除認證資料
   *
   * v2.0.0: 同時清除 localStorage 和可讀取的 cookies
   * httpOnly cookies (access_token, refresh_token) 由後端 /auth/logout 清除
   */
  private clearAuth(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_INFO_KEY);

    // 清除前端可寫入的 cookies（csrf_token 是 non-httpOnly）
    document.cookie = 'csrf_token=; Path=/; Max-Age=0';

    // 通知啟動驗證旗標需要重置（避免循環引用，使用動態 import）
    import('../hooks/utility/useAuthGuard').then(m => m.resetStartupValidation());
  }

  /**
   * 取得存取令牌
   *
   * v2.0.0: access_token 現在儲存在 httpOnly cookie 中，JS 無法讀取。
   * 此方法保留向後相容（過渡期仍嘗試從 localStorage 讀取），
   * axios withCredentials 會自動附帶 cookie。
   *
   * @returns localStorage 中的 token（過渡期），或 null
   */
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  /**
   * 取得刷新令牌
   */
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  /**
   * 取得使用者資訊
   */
  getUserInfo(): UserInfo | null {
    const userInfoStr = localStorage.getItem(USER_INFO_KEY);
    if (userInfoStr) {
      try {
        return JSON.parse(userInfoStr) as UserInfo;
      } catch (error) {
        logger.error('Failed to parse user info:', error);
        return null;
      }
    }
    return null;
  }

  /**
   * 設定使用者資訊
   */
  setUserInfo(userInfo: UserInfo): void {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));
  }

  /**
   * 取得存取令牌 (getAccessToken 的別名，向後相容)
   */
  getToken(): string | null {
    return this.getAccessToken();
  }

  /**
   * 檢查是否已登入
   *
   * v2.0.0 認證判斷邏輯：
   * 1. 檢查 user_info 是否存在於 localStorage（登入時儲存）
   * 2. 檢查 csrf_token cookie 是否存在（表示已通過後端認證設定 cookie）
   * 3. 內網/開發模式下的快速進入
   *
   * 注意: access_token 現在是 httpOnly cookie，JS 無法直接讀取。
   * 實際的 token 有效性由後端在每次 API 請求時驗證。
   */
  isAuthenticated(): boolean {
    const userInfo = this.getUserInfo();

    // 無 user_info，視為未登入
    if (!userInfo) {
      return false;
    }

    // 檢查 csrf_token cookie 存在（表示後端已設定認證 cookies）
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
      return true;
    }

    // 向後相容：檢查 localStorage 中的 access_token（過渡期）
    const token = this.getAccessToken();
    if (token) {
      return true;
    }

    // 內網/開發模式下的快速進入
    const authDisabled = isAuthDisabled();
    if (authDisabled || userInfo.auth_provider === 'internal') {
      return true;
    }

    return false;
  }

  /**
   * 檢查是否為管理員
   */
  isAdmin(): boolean {
    const userInfo = this.getUserInfo();
    return (
      userInfo?.is_admin || userInfo?.role === 'admin' || userInfo?.role === 'superuser' || false
    );
  }

  /**
   * 檢查使用者角色
   */
  hasRole(role: string): boolean {
    const userInfo = this.getUserInfo();
    return userInfo?.role === role;
  }

  /**
   * 取得認證標頭
   *
   * v2.0.0: 向後相容。新機制透過 withCredentials cookie 自動附帶認證。
   */
  getAuthHeader(): Record<string, string> {
    const headers: Record<string, string> = {};

    // 向後相容：仍附加 Authorization header（過渡期）
    const token = this.getAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    // 附加 CSRF token
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
  }

  /**
   * 初始化 Google 登入
   */
  initGoogleSignIn(clientId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // 檢查是否為有效的 Google Client ID
      if (!clientId || clientId === 'your-actual-google-client-id.apps.googleusercontent.com') {
        logger.warn('Google OAuth disabled: Invalid or placeholder client ID');
        resolve(); // 不拋出錯誤，允許正常進行
        return;
      }

      // 載入 Google Identity Services API
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
                if (window.google) {
                    window.google.accounts.id.initialize({
            client_id: clientId,
            callback: this.handleGoogleResponse.bind(this),
          });
          resolve();
        } else {
          reject(new Error('Google Identity Services not loaded'));
        }
      };
      script.onerror = () => {
        reject(new Error('Failed to load Google Identity Services'));
      };

      // 檢查是否已經載入過腳本
      if (!document.querySelector('script[src="https://accounts.google.com/gsi/client"]')) {
        document.head.appendChild(script);
      } else {
        // 腳本已存在，直接初始化
        setTimeout(() => {
                    if (window.google) {
                        window.google.accounts.id.initialize({
              client_id: clientId,
              callback: this.handleGoogleResponse.bind(this),
            });
            resolve();
          } else {
            reject(new Error('Google Identity Services not available'));
          }
        }, 100);
      }
    });
  }

  /**
   * 顯示 Google 登入按鈕
   */
  renderGoogleSignInButton(elementId: string): void {
        if (window.google) {
            window.google.accounts.id.renderButton(document.getElementById(elementId), {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: 250,
      });
    }
  }

  /**
   * 處理 Google 登入回應
   */
  private async handleGoogleResponse(response: { credential: string }): Promise<void> {
    try {
      await this.googleLogin(response.credential);
      // 登入成功，可以重新導向或更新 UI
      window.location.href = '/dashboard';
    } catch (error) {
      logger.error('Google login failed:', error);

      // 根據錯誤類型顯示不同的提醒
      if (axios.isAxiosError(error)) {
        const errorResponse = (error as AxiosError<{ detail?: string }>).response;
        const errorMessage = errorResponse?.data?.detail || error.message;

        if (errorResponse?.status === 403) {
          // 權限相關錯誤
          if (errorMessage.includes('未驗證') || errorMessage.includes('unverified')) {
            alert('您的帳戶尚未通過管理者驗證，無法登入系統。請聯絡管理者進行帳戶驗證。');
          } else if (errorMessage.includes('停用') || errorMessage.includes('suspended')) {
            alert('您的帳戶已被停用，無法登入系統。如有疑問請聯絡管理者。');
          } else {
            alert('登入被拒絕：' + errorMessage);
          }
        } else if (errorResponse?.status === 500) {
          alert('系統內部錯誤，請稍後再試或聯絡管理者。');
        } else {
          alert('Google 登入失敗：' + errorMessage);
        }
      } else {
        alert('Google 登入過程中發生未知錯誤，請稍後再試。');
      }

      throw error;
    }
  }

  /**
   * 啟動時驗證 Token 有效性
   *
   * 向後端 /auth/check 確認認證是否仍有效。
   * v2.0.0: 支援 httpOnly cookie 認證（無需讀取 token）
   *
   * @returns true 表示認證有效，false 表示已清除
   */
  async validateTokenOnStartup(): Promise<boolean> {
    // 如果沒有 user_info，直接返回 false
    const userInfo = this.getUserInfo();
    if (!userInfo) return false;

    try {
      await this.checkAuthStatus();
      return true;
    } catch {
      logger.warn('[Auth] 啟動驗證失敗，清除本地認證資料');
      this.clearAuth();
      return false;
    }
  }

  /**
   * 公開清除認證方法（供外部 hook 使用）
   */
  clearAuthData(): void {
    this.clearAuth();
  }

  /**
   * 取得已配置認證標頭的 axios 實例
   */
  getAxiosInstance() {
    return this.axios;
  }
}

// 匯出單例實例
export const authService = AuthService.getInstance();
export default authService;
