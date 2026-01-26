/**
 * 案件功能模組配置
 *
 * 定義各承攬案件的專屬功能模組，支援：
 * - 條件式 Tab 顯示
 * - 專屬功能開關
 * - 未來擴展新案件
 *
 * 擴展方式：
 * 1. 在 PROJECT_MODULE_REGISTRY 新增案件配置
 * 2. 設定該案件需要的 documentTabs 和 features
 * 3. DocumentDetailPage 會自動根據配置顯示對應 Tab
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';

// ============================================================================
// 型別定義
// ============================================================================

/** 公文詳情頁可用的 Tab 類型 */
export type DocumentTabKey =
  | 'info'           // 公文資訊 (通用)
  | 'date-status'    // 日期狀態 (通用)
  | 'case-staff'     // 承案人資 (通用)
  | 'attachments'    // 附件紀錄 (通用)
  | 'dispatch'       // 派工安排 (專屬)
  | 'project-link';  // 工程關聯 (專屬)

/** 功能特性類型 */
export type FeatureKey =
  | 'dispatch-management'    // 派工管理功能
  | 'project-linking'        // 工程關聯功能
  | 'taoyuan-projects'       // 桃園工程清單
  | 'document-preview';      // 公文預覽抽屜

/** 案件模組配置 */
export interface ProjectModuleConfig {
  /** 案件 ID (對應 contract_projects.id) */
  projectId: number;
  /** 案件代碼 */
  projectCode: string;
  /** 案件名稱 */
  projectName: string;
  /** 公文詳情頁額外顯示的 Tab */
  documentTabs: DocumentTabKey[];
  /** 啟用的功能特性 */
  features: FeatureKey[];
  /** 說明 */
  description?: string;
}

// ============================================================================
// 通用 Tab 配置 (所有公文都顯示)
// ============================================================================

export const COMMON_DOCUMENT_TABS: DocumentTabKey[] = [
  'info',
  'date-status',
  'case-staff',
  'attachments',
];

// ============================================================================
// 案件模組註冊表
// ============================================================================

/**
 * 案件功能模組註冊表
 *
 * 以 contract_project_id 為 key，配置該案件的專屬功能
 *
 * 擴展範例：
 * ```typescript
 * // 新增苗栗案件
 * [MIAOLI_CONTRACT.PROJECT_ID]: {
 *   projectId: MIAOLI_CONTRACT.PROJECT_ID,
 *   projectCode: 'CK2025_01_03_002',
 *   projectName: '115年度苗栗縣...',
 *   documentTabs: ['dispatch'],  // 只需要派工，不需工程關聯
 *   features: ['dispatch-management'],
 * },
 * ```
 */
export const PROJECT_MODULE_REGISTRY: Record<number, ProjectModuleConfig> = {
  // -------------------------------------------------------------------------
  // 115 年度桃園查估派工
  // -------------------------------------------------------------------------
  [TAOYUAN_CONTRACT.PROJECT_ID]: {
    projectId: TAOYUAN_CONTRACT.PROJECT_ID,
    projectCode: TAOYUAN_CONTRACT.CODE,
    projectName: TAOYUAN_CONTRACT.NAME,
    documentTabs: ['dispatch', 'project-link'],
    features: [
      'dispatch-management',
      'project-linking',
      'taoyuan-projects',
      'document-preview',
    ],
    description: '桃園市政府工務局委託案件，包含派工管理與工程關聯功能',
  },

  // -------------------------------------------------------------------------
  // 未來案件擴展區 (範例)
  // -------------------------------------------------------------------------
  // [MIAOLI_CONTRACT.PROJECT_ID]: {
  //   projectId: MIAOLI_CONTRACT.PROJECT_ID,
  //   projectCode: 'CK2025_01_03_002',
  //   projectName: '115年度苗栗縣...',
  //   documentTabs: ['dispatch'],
  //   features: ['dispatch-management'],
  // },
};

// ============================================================================
// 工具函數
// ============================================================================

/**
 * 取得案件的模組配置
 *
 * @param projectId - 承攬案件 ID (contract_project_id)
 * @returns 模組配置，若無則返回 null
 */
export const getProjectModuleConfig = (
  projectId: number | null | undefined
): ProjectModuleConfig | null => {
  if (!projectId) return null;
  return PROJECT_MODULE_REGISTRY[projectId] ?? null;
};

/**
 * 檢查案件是否有特定功能
 *
 * @param projectId - 承攬案件 ID
 * @param feature - 功能特性
 */
export const hasProjectFeature = (
  projectId: number | null | undefined,
  feature: FeatureKey
): boolean => {
  const config = getProjectModuleConfig(projectId);
  return config?.features.includes(feature) ?? false;
};

/**
 * 取得案件的公文詳情頁 Tab 列表
 *
 * @param projectId - 承攬案件 ID
 * @returns 完整的 Tab 列表 (通用 + 專屬)
 */
export const getDocumentTabs = (
  projectId: number | null | undefined
): DocumentTabKey[] => {
  const config = getProjectModuleConfig(projectId);
  if (!config) {
    return [...COMMON_DOCUMENT_TABS];
  }
  return [...COMMON_DOCUMENT_TABS, ...config.documentTabs];
};

/**
 * 檢查 Tab 是否應該顯示
 *
 * @param projectId - 承攬案件 ID
 * @param tabKey - Tab 鍵值
 */
export const shouldShowTab = (
  projectId: number | null | undefined,
  tabKey: DocumentTabKey
): boolean => {
  // 通用 Tab 永遠顯示
  if (COMMON_DOCUMENT_TABS.includes(tabKey)) {
    return true;
  }
  // 專屬 Tab 需要檢查案件配置
  const config = getProjectModuleConfig(projectId);
  return config?.documentTabs.includes(tabKey) ?? false;
};

/**
 * 取得所有已註冊的案件 ID 列表
 */
export const getRegisteredProjectIds = (): number[] => {
  return Object.keys(PROJECT_MODULE_REGISTRY).map(Number);
};

/**
 * 檢查是否為已註冊的專案案件
 */
export const isRegisteredProject = (
  projectId: number | null | undefined
): boolean => {
  if (!projectId) return false;
  return projectId in PROJECT_MODULE_REGISTRY;
};
