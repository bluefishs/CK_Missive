/**
 * API 模組統一匯出
 *
 * 提供統一的 API 存取介面（POST-only 資安機制）
 */

// API Client 與共用型別
export * from './types';
export * from './client';
export * from './endpoints';

// ============================================================================
// 統一 API 服務模組
// ============================================================================

// 核心業務
export * from './documentsApi';
// documentNumbersApi 已棄用並移除，請使用 documentsApi.getNextSendNumber()
export * from './projectsApi';
export * from './filesApi';

// 關聯管理
export * from './projectStaffApi';
export * from './projectVendorsApi';
export * from './projectAgencyContacts';

// 基礎資料
export * from './vendorsApi';
export * from './agenciesApi';
export * from './usersApi';

// 桃園派工管理
export * from './taoyuanDispatchApi';

// AI 服務 (v1.37.0)
export * from './aiApi';

// 主要匯出
export { apiClient, API_BASE_URL } from './client';

