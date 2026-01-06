/**
 * 服務統一導出
 *
 * @version 3.0
 * @date 2026-01-06
 *
 * 架構說明：
 * - API 服務已遷移至 src/api/ 目錄
 * - 請使用 import { documentsApi, apiClient } from '../api'
 * - 此目錄僅保留非 API 類型的服務
 */

// 認證相關服務
export * from './authService';

// 快取服務
export * from './cacheService';

// 導覽服務
export * from './navigationService';

// 安全 API 服務（CSRF 保護）
export { secureApiService } from './secureApiService';

// Ensure this file is treated as a module
export {};
