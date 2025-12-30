/**
 * 安全 API 服務
 * 提供統一的 POST 方法 API 調用，包含 CSRF 保護
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const API_PREFIX = '/api';

interface SecureRequest {
  action: string;
  csrf_token: string;
  data?: any;
}

interface SecureResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  csrf_token?: string;
}

class SecureApiService {
  private csrfToken: string | null = null;

  /**
   * 獲取 CSRF 令牌
   */
  async getCsrfToken(): Promise<string> {
    try {
      const response = await fetch(`${API_BASE_URL}${API_PREFIX}/secure-site-management/csrf-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to get CSRF token');
      }

      const result: SecureResponse = await response.json();
      
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
   * 發送安全請求
   */
  private async secureRequest<T = any>(
    endpoint: string,
    action: string,
    data?: any,
    retryOnCsrfError: boolean = true
  ): Promise<T> {
    // 在開發模式下跳過 CSRF 檢查，但仍然調用實際 API
    const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';
    if (authDisabled) {
      console.log(`🔒 Auth disabled - skipping CSRF for secure request: ${action}`);
      // 跳過 CSRF 檢查，直接調用 API
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            action,
            data: data || {},
            csrf_token: 'dev-mode-skip', // 開發模式用的假 token
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result: SecureResponse<T> = await response.json();

        if (!result.success) {
          throw new Error(result.message || 'Request failed');
        }

        return result.data;
      } catch (error) {
        console.error('Secure request error:', error);
        throw error;
      }
    }

    const csrfToken = await this.ensureCsrfToken();

    const requestBody: SecureRequest = {
      action,
      csrf_token: csrfToken,
      data: data || {},
    };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        if (response.status === 403 && retryOnCsrfError) {
          // CSRF 令牌可能過期，重新獲取並重試
          await this.getCsrfToken();
          return this.secureRequest(endpoint, action, data, false);
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: SecureResponse<T> = await response.json();

      // 更新 CSRF 令牌
      if (result.csrf_token) {
        this.csrfToken = result.csrf_token;
      }

      if (!result.success) {
        throw new Error(result.message || 'Request failed');
      }

      return result.data;
    } catch (error) {
      console.error('Secure request error:', error);
      throw error;
    }
  }

  // 導覽列管理 API
  async getNavigationItems(): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/navigation/action`, 'list');
  }

  async createNavigationItem(data: any): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/navigation/action`, 'create', data);
  }

  async updateNavigationItem(data: any): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/navigation/action`, 'update', data);
  }

  async deleteNavigationItem(id: number): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/navigation/action`, 'delete', { id });
  }

  // 配置管理 API
  async getConfigurations(filters?: { search?: string; category?: string }): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/config/action`, 'list', filters);
  }

  async createConfiguration(data: any): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/config/action`, 'create', data);
  }

  async updateConfiguration(data: any): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/config/action`, 'update', data);
  }

  async deleteConfiguration(configKey: string): Promise<any> {
    return this.secureRequest(`${API_BASE_URL}${API_PREFIX}/secure-site-management/config/action`, 'delete', { config_key: configKey });
  }

  /**
   * 通用 POST 方法 - 用於通知系統等其他 API 調用
   * 自動處理相對路徑，添加 API_BASE_URL
   */
  async post<T = any>(endpoint: string, action: string, data?: any): Promise<T> {
    // 如果 endpoint 是相對路徑，添加 API_BASE_URL
    const fullEndpoint = endpoint.startsWith('/') ? `${API_BASE_URL}${endpoint}` : endpoint;
    return this.secureRequest<T>(fullEndpoint, action, data);
  }
}

// 創建單例實例
export const secureApiService = new SecureApiService();
export default secureApiService;