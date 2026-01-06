/**
 * API 模組統一匯出
 *
 * 提供統一的 API 存取介面（POST-only 資安機制）
 */

// API Client 與共用型別
export * from './types';
export * from './client';

// ============================================================================
// 統一 API 服務模組
// ============================================================================

// 核心業務
export * from './documentsApi';
export * from './projectsApi';
export * from './filesApi';

// 關聯管理
export * from './projectStaffApi';
export * from './projectVendorsApi';
export * from './projectAgencyContacts';

// 基礎資料
export * from './vendors';
export * from './agenciesApi';
export * from './usersApi';

// 主要匯出
export { apiClient, API_BASE_URL } from './client';

