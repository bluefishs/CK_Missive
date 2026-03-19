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

// 行事曆
export * from './calendarApi';

// 認證管理
export * from './certificationsApi';

// 使用者管理 (Admin)
export * from './adminUsersApi';

// 儀表板
export * from './dashboardApi';

// 部署管理
export * from './deploymentApi';

// 知識庫
export * from './knowledgeBaseApi';

// PM 專案管理 (v1.85.0) - root-level files kept for direct import compatibility

// AI 服務 (v1.37.0)
export * from './aiApi';

// 認證服務
export * from './authApi';

// Session 管理 (v1.44.0)
export * from './sessionApi';

// 專案管理 (PM)
export * from './pm';

// 財務管理 (ERP)
export * from './erp';

// 主要匯出
export { apiClient, API_BASE_URL } from './client';

