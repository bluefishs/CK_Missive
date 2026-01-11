/**
 * 安全 API 服務
 *
 * 提供統一的 POST 方法 API 調用，包含 CSRF 保護
 * 重構版本：使用統一的 apiClient
 *
 * @version 2.1.0
 * @date 2026-01-11
 */

import { apiClient, API_BASE_URL } from '../api/client';
import { isAuthDisabled } from '../config/env';

// ============================================================================
// 型別定義
// ============================================================================

interface SecureRequest {
  action: string;
  csrf_token: string;
  data?: unknown;
}

interface SecureResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  csrf_token?: string;
}

// ============================================================================
// SecureApiService 類
// ============================================================================

class SecureApiService {
  private csrfToken: string | null = null;

  /** 檢查是否停用認證（環境變數或內網 IP） */
  private get authDisabled(): boolean {
    return isAuthDisabled();
  }

  /**
   * 獲取 CSRF 令牌
   */
  async getCsrfToken(): Promise<string> {
    try {
      const result = await apiClient.post<SecureResponse>(
        '/secure-site-management/csrf-token',
        {}
      );

      if (result.success && result.csrf_token) {
        this.csrfToken = result.csrf_token;
        return result.csrf_token;
      } else {
        throw new Error('Invalid CSRF token response');
      }
    } catch (error) {
      console.error('Error getting CSRF token:', error);
      throw error;
    }
  }

  /**
   * 確保有效的 CSRF 令牌
   */
  private async ensureCsrfToken(): Promise<string> {
    if (!this.csrfToken) {
      return await this.getCsrfToken();
    }
    return this.csrfToken;
  }

  /**
   * 發送安全請求（含 CSRF 保護）
   */
  private async secureRequest<T = unknown>(
    endpoint: string,
    action: string,
    data?: unknown,
    retryOnCsrfError = true
  ): Promise<T> {
    // 確保 endpoint 是相對路徑（apiClient 會自動加上 base URL）
    const relativeEndpoint = endpoint.startsWith(API_BASE_URL)
      ? endpoint.replace(API_BASE_URL, '')
      : endpoint.startsWith('/api')
      ? endpoint.replace('/api', '')
      : endpoint;

    // 在開發模式下跳過 CSRF 檢查
    if (this.authDisabled) {
      console.log(`🔒 Auth disabled - skipping CSRF for secure request: ${action}`);
      const requestBody: SecureRequest = {
        action,
        csrf_token: 'dev-mode-skip',
        data: data || {},
      };

      try {
        const result = await apiClient.post<SecureResponse<T>>(relativeEndpoint, requestBody);

        if (!result.success) {
          throw new Error(result.message || 'Request failed');
        }

        return result.data as T;
      } catch (error) {
        console.error('Secure request error:', error);
        throw error;
      }
    }

    // 正式模式：使用 CSRF 令牌
    const csrfToken = await this.ensureCsrfToken();
    const requestBody: SecureRequest = {
      action,
      csrf_token: csrfToken,
      data: data || {},
    };

    try {
      const result = await apiClient.post<SecureResponse<T>>(relativeEndpoint, requestBody);

      // 更新 CSRF 令牌
      if (result.csrf_token) {
        this.csrfToken = result.csrf_token;
      }

      if (!result.success) {
        throw new Error(result.message || 'Request failed');
      }

      return result.data as T;
    } catch (error: unknown) {
      // CSRF 令牌過期，重新獲取並重試
      if (retryOnCsrfError && error && typeof error === 'object' && 'statusCode' in error) {
        const apiError = error as { statusCode: number };
        if (apiError.statusCode === 403) {
          await this.getCsrfToken();
          return this.secureRequest(endpoint, action, data, false);
        }
      }
      console.error('Secure request error:', error);
      throw error;
    }
  }

  // ==========================================================================
  // 導覽列管理 API
  // ==========================================================================

  async getNavigationItems(): Promise<unknown> {
    return this.secureRequest('/secure-site-management/navigation/action', 'list');
  }

  async createNavigationItem(data: unknown): Promise<unknown> {
    return this.secureRequest('/secure-site-management/navigation/action', 'create', data);
  }

  async updateNavigationItem(data: unknown): Promise<unknown> {
    return this.secureRequest('/secure-site-management/navigation/action', 'update', data);
  }

  async deleteNavigationItem(id: number): Promise<unknown> {
    return this.secureRequest('/secure-site-management/navigation/action', 'delete', { id });
  }

  // ==========================================================================
  // 配置管理 API
  // ==========================================================================

  async getConfigurations(filters?: { search?: string; category?: string }): Promise<unknown> {
    return this.secureRequest('/secure-site-management/config/action', 'list', filters);
  }

  async createConfiguration(data: unknown): Promise<unknown> {
    return this.secureRequest('/secure-site-management/config/action', 'create', data);
  }

  async updateConfiguration(data: unknown): Promise<unknown> {
    return this.secureRequest('/secure-site-management/config/action', 'update', data);
  }

  async deleteConfiguration(configKey: string): Promise<unknown> {
    return this.secureRequest('/secure-site-management/config/action', 'delete', { config_key: configKey });
  }

  // ==========================================================================
  // 通用方法
  // ==========================================================================

  /**
   * 通用 POST 方法 - 用於通知系統等其他 API 調用
   *
   * @param endpoint API 端點（相對路徑）
   * @param action 操作動作
   * @param data 請求資料
   */
  async post<T = unknown>(endpoint: string, action: string, data?: unknown): Promise<T> {
    return this.secureRequest<T>(endpoint, action, data);
  }
}

// 創建單例實例
export const secureApiService = new SecureApiService();
export default secureApiService;
