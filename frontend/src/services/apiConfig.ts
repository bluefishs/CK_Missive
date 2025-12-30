/**
 * API 配置管理
 * 統一管理所有 API 端點和配置
 * 
 * @version 2.0
 * @author Claude Desktop
 * @date 2024-09-04
 */

import type { EnvironmentConfig } from '@/types';

/** API 環境配置 */
interface ApiEnvironment {
  readonly name: string;
  readonly baseUrl: string;
  readonly timeout: number;
  readonly retryCount: number;
}

/** API 配置類 */
class ApiConfig {
  private readonly environments: Record<string, ApiEnvironment> = {
    development: {
      name: 'Development',
      baseUrl: 'http://localhost:8001/api',
      timeout: 10000,
      retryCount: 3
    },
    optimized: {
      name: 'Optimized',
      baseUrl: 'http://localhost:8001/api',
      timeout: 5000,
      retryCount: 3
    },
    network: {
      name: 'Network',
      baseUrl: 'http://192.168.50.119:8001/api',
      timeout: 15000,
      retryCount: 2
    },
    production: {
      name: 'Production',
      baseUrl: '/api',
      timeout: 8000,
      retryCount: 3
    }
  };

  private currentEnv: string = 'development';

  /** 獲取當前環境配置 */
  getCurrentConfig(): ApiEnvironment {
    const config = this.environments[this.currentEnv];
    if (!config) {
      throw new Error(`Environment configuration not found: ${this.currentEnv}`);
    }
    return config;
  }

  /** 設定當前環境 */
  setEnvironment(env: string): void {
    if (this.environments[env]) {
      this.currentEnv = env;
    } else {
      console.warn(`Unknown environment: ${env}`);
    }
  }

  /** 獲取所有可用環境 */
  getAvailableEnvironments(): string[] {
    return Object.keys(this.environments);
  }

  /** 檢查 API 端點可用性 */
  async checkEndpoint(env?: string): Promise<boolean> {
    const config = env ? this.environments[env] : this.getCurrentConfig();
    
    if (!config) return false;

    try {
      const response = await fetch(`${config.baseUrl}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: AbortSignal.timeout(config.timeout)
      });
      
      return response.ok;
    } catch {
      return false;
    }
  }

  /** 自動選擇最佳環境 */
  async selectBestEnvironment(): Promise<string> {
    const preferences = ['optimized', 'development', 'network'];
    
    for (const env of preferences) {
      const isAvailable = await this.checkEndpoint(env);
      if (isAvailable) {
        this.setEnvironment(env);
        return env;
      }
    }

    // 如果都不可用，使用預設環境
    return this.currentEnv;
  }
}

/** API 配置實例 */
export const apiConfig = new ApiConfig();

/** API 端點常數 */
export const API_ENDPOINTS = {
  HEALTH: '/health',
  DOCUMENTS: '/documents',
  USERS: '/users',
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh'
  }
} as const;

export type { ApiEnvironment };
export { ApiConfig };

// Ensure this file is treated as a module
export {};