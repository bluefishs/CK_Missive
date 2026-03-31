/**
 * 統一 API Client
 *
 * 提供統一的 HTTP 請求處理、錯誤處理和型別支援。
 *
 * 模組拆分 (v3.0.0):
 * - errors.ts        — ApiException 錯誤類
 * - throttler.ts     — RequestThrottler 熔斷器 + 重試配置
 * - interceptors.ts  — Axios 實例 + 攔截器 + URL 配置 + Cookie 工具
 * - client.ts        — 本檔案：ApiClient 類
 */

import {
  AxiosRequestConfig,
} from 'axios';
import {
  PaginatedResponse,
  PaginationParams,
  SortParams,
  normalizePaginatedResponse,
  LegacyListResponse,
} from './types';

// 從 interceptors 匯入 Axios 實例與配置
import { axiosInstance } from './interceptors';

// 向後相容 re-export — 所有現有 import from './client' 仍可運作
export { ApiException, apiErrorBus } from './errors';
export { RequestThrottler, THROTTLE_CONFIG, RETRY_CONFIG, isRetryableNetworkError } from './throttler';
export { getCookie, API_BASE_URL, SERVER_BASE_URL } from './interceptors';

// ============================================================================
// API Client 類
// ============================================================================

/**
 * 統一 API Client
 *
 * 提供型別安全的 HTTP 請求方法
 */
class ApiClient {
  private axios: typeof axiosInstance;

  constructor(instance: typeof axiosInstance) {
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
   * 靜默 POST 請求 — 錯誤不觸發 GlobalApiErrorNotifier
   * 適用於內部 catch 處理錯誤並返回 fallback 的 AI API 函式
   */
  async silentPost<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<T> {
    return this.post<T>(url, data, { ...config, _silent: true } as AxiosRequestConfig);
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
