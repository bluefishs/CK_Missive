/**
 * 認證服務 - 處理使用者登入、登出、權限檢查等功能
 *
 * @version 1.2.0
 * @date 2026-01-11
 */
import axios, { AxiosResponse } from 'axios';
import { jwtDecode } from 'jwt-decode';
import { isAuthDisabled, API_BASE_URL } from '../config/env';

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

export interface RegisterRequest {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

export interface UserInfo {
  id: number;
  email: string;
  username?: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  auth_provider?: string;
  avatar_url?: string;
  permissions?: string | string[];  // 權限列表 (JSON 字串或陣列)
  role: string;
  created_at: string;
  last_login?: string;
  login_count: number;
  email_verified: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  user_info: UserInfo;
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
  });

  constructor() {
    // 添加請求攔截器，自動加入 Authorization header
    this.axios.interceptors.request.use(
      config => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
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
            console.log('🔧 Development mode: Ignoring 401 error for auth bypass');
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
   */
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response: AxiosResponse<TokenResponse> = await this.axios.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    this.saveAuthData(response.data);
    return response.data;
  }

  /**
   * Google OAuth 登入
   */
  async googleLogin(credential: string): Promise<TokenResponse> {
    const response: AxiosResponse<TokenResponse> = await this.axios.post('/auth/google', {
      credential,
    });

    this.saveAuthData(response.data);
    return response.data;
  }

  /**
   * 使用者註冊
   */
  async register(userData: RegisterRequest): Promise<UserInfo> {
    const response: AxiosResponse<UserInfo> = await this.axios.post('/auth/register', userData);

    return response.data;
  }

  /**
   * 登出
   */
  async logout(): Promise<void> {
    // 在開發模式下仍然嘗試調用 API，但不處理錯誤
    const authDisabled = isAuthDisabled();

    try {
      await this.axios.post('/auth/logout');
    } catch (error) {
      if (authDisabled) {
        console.log('🔒 Auth disabled - ignoring logout API error');
      } else {
        console.error('Logout request failed:', error);
      }
    } finally {
      this.clearAuth();
    }
  }

  /**
   * 取得當前使用者資訊
   */
  async getCurrentUser(): Promise<UserInfo> {
    const response: AxiosResponse<UserInfo> = await this.axios.get('/auth/me');
    return response.data;
  }

  /**
   * 檢查認證狀態
   */
  async checkAuthStatus(): Promise<any> {
    const response = await this.axios.get('/auth/check');
    return response.data;
  }

  /**
   * 檢查權限
   */
  async checkPermission(permission: string, resource?: string): Promise<boolean> {
    try {
      const response = await this.axios.post('/admin/user-management/permissions/check', {
        permission,
        resource,
      });
      return response.data.granted;
    } catch (error) {
      console.error('Permission check failed:', error);
      return false;
    }
  }

  /**
   * 儲存認證資料
   */
  private saveAuthData(tokenResponse: TokenResponse): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokenResponse.access_token);
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(tokenResponse.user_info));

    if (tokenResponse.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokenResponse.refresh_token);
    }
  }

  /**
   * 清除認證資料
   */
  private clearAuth(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_INFO_KEY);
  }

  /**
   * 取得存取令牌
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
        console.error('Failed to parse user info:', error);
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
   */
  isAuthenticated(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;

    try {
      const decoded = jwtDecode<JwtPayload>(token);
      // 檢查 token 是否過期
      const currentTime = Date.now() / 1000;
      return decoded.exp > currentTime;
    } catch (error) {
      console.error('Token decode failed:', error);
      return false;
    }
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
   */
  getAuthHeader(): Record<string, string> {
    const token = this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * 初始化 Google 登入
   */
  initGoogleSignIn(clientId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // 檢查是否為有效的 Google Client ID
      if (!clientId || clientId === 'your-actual-google-client-id.apps.googleusercontent.com') {
        console.warn('Google OAuth disabled: Invalid or placeholder client ID');
        resolve(); // 不拋出錯誤，允許正常進行
        return;
      }

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
          // @ts-ignore
          if (window.google) {
            // @ts-ignore
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
    // @ts-ignore
    if (window.google) {
      // @ts-ignore
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
  private async handleGoogleResponse(response: any): Promise<void> {
    try {
      await this.googleLogin(response.credential);
      // 登入成功，可以重新導向或更新 UI
      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Google login failed:', error);

      // 根據錯誤類型顯示不同的提醒
      if (error instanceof Error || (error as any)?.response) {
        const errorResponse = (error as any)?.response;
        const errorMessage = errorResponse?.data?.detail || (error as any).message;

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
   * 取得已配置認證標頭的 axios 實例
   */
  getAxiosInstance() {
    return this.axios;
  }
}

// 匯出單例實例
export const authService = AuthService.getInstance();
export default authService;
