/**
 * 案件功能模組配置
 *
 * v2.0.0: 改為資料庫驅動 — 承攬案件管理頁勾選「啟用派工管理」即可。
 * 前端透過 useDispatchProjectIds() hook 取得已啟用的案件 ID 列表。
 *
 * @version 2.0.0
 * @date 2026-03-05
 */

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

// ============================================================================
// 通用 Tab 配置 (所有公文都顯示)
// ============================================================================

export const COMMON_DOCUMENT_TABS: DocumentTabKey[] = [
  'info',
  'date-status',
  'case-staff',
  'attachments',
];

/** 派工案件額外啟用的 Tab */
const DISPATCH_DOCUMENT_TABS: DocumentTabKey[] = ['dispatch', 'project-link'];

/** 派工案件的完整功能列表 */
const DISPATCH_FEATURES: FeatureKey[] = [
  'dispatch-management',
  'project-linking',
  'taoyuan-projects',
  'document-preview',
];

// ============================================================================
// 派工案件 ID 快取（由 useDispatchProjectIds hook 填充）
// ============================================================================

/** 已啟用派工管理的案件 ID Set（從 API 載入後快取） */
let _dispatchProjectIds: Set<number> = new Set();

/**
 * 設定已啟用派工管理的案件 ID 列表
 * 由 useDispatchProjectIds hook 在初始化時呼叫
 */
export const setDispatchProjectIds = (ids: number[]): void => {
  _dispatchProjectIds = new Set(ids);
};

/**
 * 取得已啟用派工管理的案件 ID 列表
 */
export const getDispatchProjectIds = (): number[] => {
  return Array.from(_dispatchProjectIds);
};

// ============================================================================
// 工具函數（API 驅動版）
// ============================================================================

/**
 * 檢查案件是否有特定功能
 *
 * 依據 API 回傳的已啟用派工管理案件列表判斷。
 * 需先由 useDispatchProjectIds hook 初始化快取。
 */
export const hasProjectFeature = (
  projectId: number | null | undefined,
  feature: FeatureKey
): boolean => {
  if (!projectId) return false;
  if (!_dispatchProjectIds.has(projectId)) return false;
  return DISPATCH_FEATURES.includes(feature);
};

/**
 * 取得案件的公文詳情頁 Tab 列表
 */
export const getDocumentTabs = (
  projectId: number | null | undefined
): DocumentTabKey[] => {
  if (!projectId || !_dispatchProjectIds.has(projectId)) {
    return [...COMMON_DOCUMENT_TABS];
  }
  return [...COMMON_DOCUMENT_TABS, ...DISPATCH_DOCUMENT_TABS];
};

/**
 * 檢查 Tab 是否應該顯示
 */
export const shouldShowTab = (
  projectId: number | null | undefined,
  tabKey: DocumentTabKey
): boolean => {
  if (COMMON_DOCUMENT_TABS.includes(tabKey)) return true;
  if (!projectId || !_dispatchProjectIds.has(projectId)) return false;
  return DISPATCH_DOCUMENT_TABS.includes(tabKey);
};

/**
 * 取得所有已註冊的案件 ID 列表
 */
export const getRegisteredProjectIds = (): number[] => {
  return Array.from(_dispatchProjectIds);
};

/**
 * 檢查是否為已啟用派工管理的案件
 */
export const isRegisteredProject = (
  projectId: number | null | undefined
): boolean => {
  if (!projectId) return false;
  return _dispatchProjectIds.has(projectId);
};

