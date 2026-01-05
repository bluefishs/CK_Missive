/**
 * 統一 API Client
 *
 * 提供統一的 HTTP 請求處理、錯誤處理和型別支援
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

// ============================================================================
// 配置常量
// ============================================================================

/** API 基礎 URL */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api';

/** 預設請求超時時間（毫秒） */
const DEFAULT_TIMEOUT = 30000;

/** 認證是否禁用（開發模式） */
const AUTH_DISABLED = import.meta.env['VITE_AUTH_DISABLED'] === 'true';

// ============================================================================
// API 錯誤類
// ============================================================================

/**
 * API 錯誤類
 *
 * 統一封裝 API 錯誤，提供一致的錯誤處理介面
 */
export class ApiException extends Error {
  public readonly code: ErrorCode | string;
  public readonly statusCode: number;
  public readonly details: { field?: string; message: string; value?: unknown }[];
  public readonly timestamp: Date;

  constructor(
    code: ErrorCode | string,
    message: string,
    statusCode = 500,
    details?: { field?: string; message: string; value?: unknown }[]
  ) {
    super(message);
    this.name = 'ApiException';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details || [];
    this.timestamp = new Date();
  }

  /** 從錯誤回應建立 ApiException */
  static fromResponse(response: ErrorResponse, statusCode = 500): ApiException {
    return new ApiException(
      response.error.code,
      response.error.message,
      statusCode,
      response.error.details
    );
  }

  /** 從 Axios 錯誤建立 ApiException */
  static fromAxiosError(error: AxiosError<ErrorResponse>): ApiException {
    // 網路錯誤
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        return new ApiException(
          ErrorCode.TIMEOUT,
          '請求超時，請檢查網路連線後重試',
          0
        );
      }
      return new ApiException(
        ErrorCode.NETWORK_ERROR,
        '網路連線失敗，請檢查網路狀態',
        0
      );
    }

    const { status, data } = error.response;

    // 後端回傳統一格式的錯誤
    if (data && typeof data === 'object' && 'error' in data) {
      return ApiException.fromResponse(data as ErrorResponse, status);
    }

    // 根據 HTTP 狀態碼建立錯誤
    const statusMessages: Record<number, [ErrorCode, string]> = {
      400: [ErrorCode.BAD_REQUEST, '請求參數錯誤'],
      401: [ErrorCode.UNAUTHORIZED, '請先登入'],
      403: [ErrorCode.FORBIDDEN, '您沒有權限執行此操作'],
      404: [ErrorCode.NOT_FOUND, '找不到請求的資源'],
      409: [ErrorCode.CONFLICT, '資源衝突'],
      422: [ErrorCode.VALIDATION_ERROR, '輸入資料驗證失敗'],
      500: [ErrorCode.INTERNAL_ERROR, '伺服器內部錯誤'],
      502: [ErrorCode.SERVICE_UNAVAILABLE, '服務暫時無法使用'],
      503: [ErrorCode.SERVICE_UNAVAILABLE, '服務暫時無法使用'],
    };

    const [code, message] = statusMessages[status] || [
      ErrorCode.INTERNAL_ERROR,
      '發生未知錯誤',
    ];

    return new ApiException(code, message, status);
  }

  /** 取得使用者友善的錯誤訊息 */
  getUserMessage(): string {
    return this.message;
  }

  /** 取得欄位錯誤（用於表單驗證） */
  getFieldErrors(): Record<string, string> {
    if (!this.details) return {};

    return this.details.reduce((acc, detail) => {
      if (detail.field) {
        acc[detail.field] = detail.message;
      }
      return acc;
    }, {} as Record<string, string>);
  }
}

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
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // 請求攔截器
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // 添加認證 Token
      const token = localStorage.getItem('auth_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 回應攔截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // 直接返回資料（不做自動解包，由各 API 方法處理）
      return response;
    },
    (error: AxiosError<ErrorResponse>) => {
      // 處理 401 未授權
      if (error.response?.status === 401 && !AUTH_DISABLED) {
        localStorage.removeItem('auth_token');
        // 避免在登入頁面重複跳轉
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
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
   * 上傳檔案
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
   * 下載檔案
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
