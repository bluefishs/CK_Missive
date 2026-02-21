/**
 * 統一 API Client
 *
 * 提供統一的 HTTP 請求處理、錯誤處理和型別支援。
 *
 * 模組拆分 (v2.0.0):
 * - errors.ts    — ApiException 錯誤類
 * - throttler.ts — RequestThrottler 熔斷器 + 重試配置
 * - client.ts    — 本檔案：Axios 實例 + ApiClient 類
 */

import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';
import {
  ErrorCode,
  ErrorResponse,
  PaginatedResponse,
  PaginationParams,
  SortParams,
  normalizePaginatedResponse,
  LegacyListResponse,
} from './types';

// 從拆分模組匯入
import { ApiException } from './errors';
import { RequestThrottler, RETRY_CONFIG, isRetryableNetworkError } from './throttler';

// 向後相容 re-export（現有 import { ApiException } from './client' 仍可運作）
export { ApiException } from './errors';
export { RequestThrottler, THROTTLE_CONFIG, RETRY_CONFIG, isRetryableNetworkError } from './throttler';

// ============================================================================
// 配置常量
// ============================================================================

import { isInternalIPAddress } from '../config/env';
import { AUTH_ENDPOINTS } from './endpoints';
import { logger } from '../services/logger';

// ============================================================================
// Cookie 工具函數
// ============================================================================

/**
 * 從 document.cookie 中讀取指定名稱的 cookie 值
 *
 * @param name cookie 名稱
 * @returns cookie 值，或 null（若不存在）
 */
export function getCookie(name: string): string | null {
  const nameEq = `${name}=`;
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(nameEq)) {
      return decodeURIComponent(trimmed.substring(nameEq.length));
    }
  }
  return null;
}

/**
 * 動態 API URL 計算
 * 根據存取來源自動選擇正確的後端位址
 *
 * 內網 IP 判斷使用 config/env.ts 的共用常數 (SSOT)
 */
function getDynamicApiBaseUrl(): string {
  const hostname = window.location.hostname;
  const defaultPort = '8001';

  // 1. localhost 或 127.0.0.1 → 使用 localhost 後端
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://localhost:${defaultPort}/api`;
  }

  // 2. 內網 IP → 使用相同 IP 的後端（使用 config/env.ts 共用函數）
  if (isInternalIPAddress(hostname)) {
    return `http://${hostname}:${defaultPort}/api`;
  }

  // 3. ngrok 或其他公網域名 → 使用環境變數或相對路徑
  // ngrok 需要後端也有隧道，這裡使用環境變數或 fallback
  if (import.meta.env.VITE_API_BASE_URL) {
    return `${import.meta.env.VITE_API_BASE_URL}/api`;
  }

  // 4. 預設使用相對路徑（適用於同源部署）
  return '/api';
}

/** API 基礎 URL（動態計算，包含 /api） */
export const API_BASE_URL = getDynamicApiBaseUrl();

/** 伺服器基礎 URL（動態計算，不含 /api） */
export const SERVER_BASE_URL = API_BASE_URL.replace(/\/api$/, '');

// 開發模式下輸出 API URL 資訊
if (import.meta.env.DEV) {
  logger.log('Dynamic API URL:', API_BASE_URL);
  logger.log('Hostname:', window.location.hostname);
}

/** 預設請求超時時間（毫秒） */
const DEFAULT_TIMEOUT = 30000;

/** 認證是否禁用（開發模式） */
const AUTH_DISABLED = import.meta.env['VITE_AUTH_DISABLED'] === 'true';

const requestThrottler = new RequestThrottler();

// ============================================================================
// 建立 Axios 實例
// ============================================================================

/**
 * 建立並配置 Axios 實例
 */
function createAxiosInstance(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    withCredentials: true,  // 啟用 cookie 跨域傳送（httpOnly cookie 認證）
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Token Key 常數（與 authService 統一）
  const ACCESS_TOKEN_KEY = 'access_token';
  const REFRESH_TOKEN_KEY = 'refresh_token';

  // 標記是否正在刷新 token
  let isRefreshing = false;
  let refreshSubscribers: Array<(token: string) => void> = [];

  const subscribeTokenRefresh = (cb: (token: string) => void) => {
    refreshSubscribers.push(cb);
  };

  const onTokenRefreshed = (token: string) => {
    refreshSubscribers.forEach((cb) => cb(token));
    refreshSubscribers = [];
  };

  // 請求節流攔截器（防止無限迴圈造成請求風暴）
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const result = requestThrottler.check(config.method, config.url);

      if (result.action === 'cache') {
        // 返回快取：透過自訂 adapter 直接返回上次結果
        const cachedData = result.data;
        config.adapter = () => Promise.resolve({
          data: cachedData,
          status: 200,
          statusText: 'OK (throttled cache)',
          headers: {},
          config,
        } as AxiosResponse);
      } else if (result.action === 'reject') {
        return Promise.reject(new ApiException(
          ErrorCode.TOO_MANY_REQUESTS,
          `請求被熔斷器攔截: ${result.reason}`,
          429
        ));
      }

      return config;
    }
  );

  // 請求攔截器（認證 Token - 向後相容過渡期）
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // 向後相容：仍從 localStorage 讀取 token 附加到 header
      // 當完全遷移到 cookie 後，此段可移除
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 請求攔截器（CSRF Token）
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const method = config.method?.toUpperCase() || '';
      // 非安全方法才需要附加 CSRF token
      if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const csrfToken = getCookie('csrf_token');
        if (csrfToken && config.headers) {
          config.headers['X-CSRF-Token'] = csrfToken;
        }
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 回應攔截器（含 Token 自動刷新機制）
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // 記錄成功回應供節流快取使用
      requestThrottler.recordResponse(
        response.config?.method,
        response.config?.url,
        response.data
      );
      return response;
    },
    async (error: AxiosError<ErrorResponse>) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
        _retryCount?: number;
      };

      // 網路錯誤自動重試（後端重啟期間的 ERR_CONNECTION_REFUSED）
      if (isRetryableNetworkError(error) && originalRequest) {
        const retryCount = originalRequest._retryCount || 0;
        if (retryCount < RETRY_CONFIG.MAX_RETRIES) {
          originalRequest._retryCount = retryCount + 1;
          const delay = Math.min(
            RETRY_CONFIG.BASE_DELAY_MS * Math.pow(RETRY_CONFIG.BACKOFF_MULTIPLIER, retryCount),
            RETRY_CONFIG.MAX_DELAY_MS
          );
          logger.warn(
            `[Retry] 網路錯誤，${delay}ms 後重試 (${retryCount + 1}/${RETRY_CONFIG.MAX_RETRIES}): ${originalRequest.url}`
          );
          await new Promise(resolve => setTimeout(resolve, delay));
          return instance(originalRequest);
        }
        // 重試耗盡，繼續走正常錯誤處理
        logger.error(`[Retry] 重試耗盡 (${RETRY_CONFIG.MAX_RETRIES}次)，後端可能未啟動: ${originalRequest.url}`);
      }

      // 處理 401 未授權
      if (error.response?.status === 401 && !AUTH_DISABLED) {
        // 檢查是否有 refresh token 可用於刷新
        // 支援 localStorage（向後相容）和 cookie（新機制，由 withCredentials 自動帶上）
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        // cookie 中的 refresh_token 是 httpOnly，JS 無法讀取，
        // 但 withCredentials 會自動附帶到 /api/auth/refresh 路徑
        const hasRefreshCookie = !!getCookie('csrf_token');  // csrf_token 存在表示有認證 cookies

        if ((refreshToken || hasRefreshCookie) && !originalRequest._retry) {
          if (isRefreshing) {
            // 如果正在刷新，等待刷新完成後重試
            return new Promise((resolve) => {
              subscribeTokenRefresh(() => {
                // cookie 認證模式下，重試時不需要手動設定 header
                resolve(instance(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          isRefreshing = true;

          try {
            // 嘗試刷新 token
            // 同時發送 body（向後相容）和依賴 cookie（新機制）
            const refreshPayload = refreshToken ? { refresh_token: refreshToken } : {};
            const response = await axios.post(
              `${API_BASE_URL}${AUTH_ENDPOINTS.REFRESH}`,
              refreshPayload,
              { withCredentials: true }
            );

            const { access_token, refresh_token: newRefreshToken } = response.data;

            // 向後相容：更新 localStorage（過渡期）
            if (access_token) {
              localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
            }
            if (newRefreshToken) {
              localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
            }

            // 通知所有等待的請求
            onTokenRefreshed(access_token || '');
            isRefreshing = false;

            // 重試原始請求（cookie 會自動附帶新的 access_token）
            if (access_token && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }
            return instance(originalRequest);
          } catch (refreshError) {
            // 刷新失敗，清除認證資訊並跳轉登入
            isRefreshing = false;
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            localStorage.removeItem('user_info');
            // 清除前端可寫入的 cookie
            document.cookie = 'csrf_token=; Path=/; Max-Age=0';

            if (!window.location.pathname.includes('/login')) {
              window.location.href = '/login';
            }
            throw ApiException.fromAxiosError(error);
          }
        } else {
          // 沒有 refresh token，直接清除並跳轉
          localStorage.removeItem(ACCESS_TOKEN_KEY);
          localStorage.removeItem(REFRESH_TOKEN_KEY);
          localStorage.removeItem('user_info');
          document.cookie = 'csrf_token=; Path=/; Max-Age=0';

          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
      }

      // 轉換為 ApiException
      throw ApiException.fromAxiosError(error);
    }
  );

  return instance;
}

// 建立單例實例
const axiosInstance = createAxiosInstance();

// ============================================================================
// API Client 類
// ============================================================================

/**
 * 統一 API Client
 *
 * 提供型別安全的 HTTP 請求方法
 */
class ApiClient {
  private axios: AxiosInstance;

  constructor(instance: AxiosInstance) {
    this.axios = instance;
  }

  /**
   * GET 請求
   */
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axios.get<T>(url, config);
    return response.data;
  }

  /**
   * POST 請求
   */
  async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.axios.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUT 請求
   */
  async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.axios.put<T>(url, data, config);
    return response.data;
  }

  /**
   * PATCH 請求
   */
  async patch<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.axios.patch<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETE 請求
   */
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axios.delete<T>(url, config);
    return response.data;
  }

  /**
   * 分頁列表請求（GET）
   *
   * 自動處理分頁參數並標準化回應格式
   */
  async getList<T>(
    url: string,
    params?: PaginationParams & SortParams & Record<string, unknown>
  ): Promise<PaginatedResponse<T>> {
    const response = await this.axios.get<
      PaginatedResponse<T> | LegacyListResponse<T>
    >(url, { params });
    return normalizePaginatedResponse<T>(
      response.data,
      params?.page,
      params?.limit
    );
  }

  /**
   * 分頁列表請求（POST）
   *
   * 用於需要在 body 傳遞複雜查詢參數的情況
   */
  async postList<T>(
    url: string,
    data?: PaginationParams & SortParams & Record<string, unknown>
  ): Promise<PaginatedResponse<T>> {
    const response = await this.axios.post<
      PaginatedResponse<T> | LegacyListResponse<T>
    >(url, data);
    return normalizePaginatedResponse<T>(
      response.data,
      data?.page,
      data?.limit
    );
  }

  /**
   * 上傳檔案（單檔）
   */
  async upload<T>(
    url: string,
    file: File,
    fieldName = 'file',
    additionalData?: Record<string, string>
  ): Promise<T> {
    const formData = new FormData();
    formData.append(fieldName, file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const response = await this.axios.post<T>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * 上傳檔案（含進度追蹤）
   *
   * @param url API 路徑
   * @param files 檔案列表
   * @param fieldName 表單欄位名稱
   * @param onProgress 進度回調 (percent: 0-100, loaded: bytes, total: bytes)
   * @param additionalData 額外表單資料
   * @returns Promise<T>
   */
  async uploadWithProgress<T>(
    url: string,
    files: File | File[],
    fieldName = 'files',
    onProgress?: (percent: number, loaded: number, total: number) => void,
    additionalData?: Record<string, string>
  ): Promise<T> {
    const formData = new FormData();

    // 支援單檔或多檔
    const fileArray = Array.isArray(files) ? files : [files];
    fileArray.forEach((file) => {
      formData.append(fieldName, file);
    });

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const response = await this.axios.post<T>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round(
            (progressEvent.loaded / progressEvent.total) * 100
          );
          onProgress(percent, progressEvent.loaded, progressEvent.total);
        }
      },
    });

    return response.data;
  }

  /**
   * 下載檔案（GET 方式）
   */
  async download(url: string, filename?: string): Promise<void> {
    const response = await this.axios.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download =
      filename ||
      this.extractFilename(response.headers['content-disposition']) ||
      'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  /**
   * 下載檔案（POST 方式 - 用於 POST-only 資安機制）
   */
  async downloadPost(
    url: string,
    data?: unknown,
    filename?: string
  ): Promise<void> {
    const response = await this.axios.post(url, data, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download =
      filename ||
      this.extractFilename(response.headers['content-disposition']) ||
      'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  /**
   * 從 Content-Disposition 標頭提取檔名
   */
  private extractFilename(contentDisposition?: string): string | null {
    if (!contentDisposition) return null;

    const filenameMatch = contentDisposition.match(
      /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
    );
    if (filenameMatch && filenameMatch[1]) {
      return filenameMatch[1].replace(/['"]/g, '');
    }

    return null;
  }

  /**
   * POST 請求（FormData）
   *
   * 用於上傳檔案或提交 FormData
   */
  async postForm<T>(url: string, formData: FormData): Promise<T> {
    const response = await this.axios.post<T>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * POST 請求（取得 Blob 回應）
   *
   * 用於下載二進位檔案
   */
  async postBlob(url: string, data?: unknown): Promise<Blob> {
    const response = await this.axios.post(url, data, {
      responseType: 'blob',
    });
    return response.data;
  }
}

// ============================================================================
// 匯出
// ============================================================================

/** API Client 單例 */
export const apiClient = new ApiClient(axiosInstance);

/** 原始 Axios 實例（用於需要直接存取的情況） */
export const axiosClient = axiosInstance;

/** 預設匯出 */
export default apiClient;
