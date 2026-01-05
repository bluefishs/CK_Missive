/**
 * API 模組統一匯出
 *
 * 提供統一的 API 存取介面
 */

// 新版統一 API Client 和型別
export * from './types';
export * from './client';

// 統一 API 服務模組（新版 POST-only 資安機制）
export * from './vendors';
export * from './projectsApi';
export * from './usersApi';
export * from './documentsApi';
export * from './agenciesApi';

// 舊版 API 服務（逐步淘汰，請改用上述新版模組）
export * from './documents';
export * from './projects';

// 主要匯出
export { apiClient, API_BASE_URL } from './client';

/**
 * @deprecated 請改用 apiClient from './client'
 * 此別名保留是為了向後相容
 */
export { apiClient as legacyApiClient } from './client';
