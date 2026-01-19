/**
 * API 端點集中定義
 *
 * 所有 API 路徑統一在此管理，確保前後端一致性
 * 使用方式: import { API_ENDPOINTS } from './endpoints';
 *
 * @version 1.0.0
 * @date 2026-01-08
 */

// ============================================================================
// 核心功能模組端點
// ============================================================================

/** 儀表板 API 端點 */
export const DASHBOARD_ENDPOINTS = {
  /** 取得統計資料 POST /dashboard/stats */
  STATS: '/dashboard/stats',
  /** 取得摘要 POST /dashboard/summary */
  SUMMARY: '/dashboard/summary',
} as const;

/** 公文管理 API 端點 (增強版) */
export const DOCUMENTS_ENDPOINTS = {
  /** 公文列表 POST /documents-enhanced/list */
  LIST: '/documents-enhanced/list',
  /** 建立公文 POST /documents-enhanced/create */
  CREATE: '/documents-enhanced/create',
  /** 公文詳情 POST /documents-enhanced/:id/detail */
  DETAIL: (id: number) => `/documents-enhanced/${id}/detail`,
  /** 更新公文 POST /documents-enhanced/:id/update */
  UPDATE: (id: number) => `/documents-enhanced/${id}/update`,
  /** 刪除公文 POST /documents-enhanced/:id/delete */
  DELETE: (id: number) => `/documents-enhanced/${id}/delete`,
  /** 公文統計 POST /documents-enhanced/statistics */
  STATISTICS: '/documents-enhanced/statistics',
  /** 篩選後統計 POST /documents-enhanced/filtered-statistics */
  FILTERED_STATISTICS: '/documents-enhanced/filtered-statistics',
  /** 年度選項 POST /documents-enhanced/years */
  YEARS: '/documents-enhanced/years',
  /** 承攬案件下拉 POST /documents-enhanced/contract-projects-dropdown */
  CONTRACT_PROJECTS_DROPDOWN: '/documents-enhanced/contract-projects-dropdown',
  /** 機關下拉 POST /documents-enhanced/agencies-dropdown */
  AGENCIES_DROPDOWN: '/documents-enhanced/agencies-dropdown',
  /** 專案關聯公文 POST /documents-enhanced/by-project */
  BY_PROJECT: '/documents-enhanced/by-project',
  /** 匯出公文 POST /documents-enhanced/export */
  EXPORT: '/documents-enhanced/export',
  /** 審計日誌列表 POST /documents-enhanced/audit-logs */
  AUDIT_LOGS: '/documents-enhanced/audit-logs',
  /** 公文審計歷史 POST /documents-enhanced/:id/audit-history */
  AUDIT_HISTORY: (id: number) => `/documents-enhanced/${id}/audit-history`,
  /** 整合搜尋 POST /documents-enhanced/integrated-search */
  INTEGRATED_SEARCH: '/documents-enhanced/integrated-search',
  /** 取得下一個發文字號 POST /documents-enhanced/next-send-number */
  NEXT_SEND_NUMBER: '/documents-enhanced/next-send-number',
} as const;

/** 承攬案件 API 端點 */
export const PROJECTS_ENDPOINTS = {
  /** 專案列表 POST /projects/list */
  LIST: '/projects/list',
  /** 建立專案 POST /projects */
  CREATE: '/projects',
  /** 專案詳情 POST /projects/:id/detail */
  DETAIL: (id: number) => `/projects/${id}/detail`,
  /** 更新專案 POST /projects/:id/update */
  UPDATE: (id: number) => `/projects/${id}/update`,
  /** 刪除專案 POST /projects/:id/delete */
  DELETE: (id: number) => `/projects/${id}/delete`,
  /** 專案統計 POST /projects/statistics */
  STATISTICS: '/projects/statistics',
  /** 年度選項 POST /projects/years */
  YEARS: '/projects/years',
  /** 類別選項 POST /projects/categories */
  CATEGORIES: '/projects/categories',
  /** 狀態選項 POST /projects/statuses */
  STATUSES: '/projects/statuses',
} as const;

/** 機關單位 API 端點 */
export const AGENCIES_ENDPOINTS = {
  /** 機關列表 POST /agencies/list */
  LIST: '/agencies/list',
  /** 建立機關 POST /agencies */
  CREATE: '/agencies',
  /** 機關詳情 POST /agencies/:id/detail */
  DETAIL: (id: number) => `/agencies/${id}/detail`,
  /** 更新機關 POST /agencies/:id/update */
  UPDATE: (id: number) => `/agencies/${id}/update`,
  /** 刪除機關 POST /agencies/:id/delete */
  DELETE: (id: number) => `/agencies/${id}/delete`,
  /** 機關統計 POST /agencies/statistics */
  STATISTICS: '/agencies/statistics',
} as const;

/** 廠商管理 API 端點 */
export const VENDORS_ENDPOINTS = {
  /** 廠商列表 POST /vendors/list */
  LIST: '/vendors/list',
  /** 建立廠商 POST /vendors */
  CREATE: '/vendors',
  /** 廠商詳情 POST /vendors/:id/detail */
  DETAIL: (id: number) => `/vendors/${id}/detail`,
  /** 更新廠商 POST /vendors/:id/update */
  UPDATE: (id: number) => `/vendors/${id}/update`,
  /** 刪除廠商 POST /vendors/:id/delete */
  DELETE: (id: number) => `/vendors/${id}/delete`,
  /** 廠商統計 POST /vendors/statistics */
  STATISTICS: '/vendors/statistics',
} as const;

// ============================================================================
// 行事曆模組端點 (統一使用 /calendar)
// ============================================================================

/** 行事曆 API 端點 */
export const CALENDAR_ENDPOINTS = {
  /** 使用者事件列表 POST /calendar/users/calendar-events */
  USER_EVENTS: '/calendar/users/calendar-events',
  /** 事件列表 POST /calendar/events/list */
  EVENTS_LIST: '/calendar/events/list',
  /** 建立事件 POST /calendar/events */
  EVENTS_CREATE: '/calendar/events',
  /** 事件詳情 POST /calendar/events/:id/detail */
  EVENTS_DETAIL: (id: number) => `/calendar/events/${id}/detail`,
  /** 更新事件 POST /calendar/events/update */
  EVENTS_UPDATE: '/calendar/events/update',
  /** 刪除事件 POST /calendar/events/delete */
  EVENTS_DELETE: '/calendar/events/delete',
  /** 同步單一事件 POST /calendar/events/sync */
  EVENTS_SYNC: '/calendar/events/sync',
  /** 批次同步 POST /calendar/events/bulk-sync */
  EVENTS_BULK_SYNC: '/calendar/events/bulk-sync',
  /** 公文行事曆事件 POST /calendar/document/:docId/events */
  DOCUMENT_EVENTS: (docId: number) => `/calendar/document/${docId}/events`,
  /** 從公文建立事件 POST /calendar/document/:docId/create-event */
  DOCUMENT_CREATE_EVENT: (docId: number) => `/calendar/document/${docId}/create-event`,
} as const;

// ============================================================================
// 通知模組端點
// ============================================================================

/** 系統通知 API 端點 */
export const SYSTEM_NOTIFICATIONS_ENDPOINTS = {
  /** 通知列表 POST /system-notifications/list */
  LIST: '/system-notifications/list',
  /** 未讀數量 POST /system-notifications/unread-count */
  UNREAD_COUNT: '/system-notifications/unread-count',
  /** 標記已讀 POST /system-notifications/mark-read */
  MARK_READ: '/system-notifications/mark-read',
  /** 全部已讀 POST /system-notifications/mark-all-read */
  MARK_ALL_READ: '/system-notifications/mark-all-read',
} as const;

/** 專案通知 API 端點 */
export const PROJECT_NOTIFICATIONS_ENDPOINTS = {
  /** 通知列表 POST /project-notifications/list */
  LIST: '/project-notifications/list',
  /** 建立通知 POST /project-notifications */
  CREATE: '/project-notifications',
} as const;

// ============================================================================
// 檔案管理端點
// ============================================================================

/** 檔案管理 API 端點 */
export const FILES_ENDPOINTS = {
  /** 儲存資訊 POST /files/storage-info */
  STORAGE_INFO: '/files/storage-info',
  /** 上傳檔案 POST /files/upload?document_id=:docId */
  UPLOAD: (docId: number) => `/files/upload?document_id=${docId}`,
  /** 文件附件列表 POST /files/document/:docId */
  DOCUMENT_ATTACHMENTS: (docId: number) => `/files/document/${docId}`,
  /** 下載附件 POST /files/:id/download */
  DOWNLOAD: (id: number) => `/files/${id}/download`,
  /** 刪除附件 POST /files/:id/delete */
  DELETE: (id: number) => `/files/${id}/delete`,
  /** 驗證附件 POST /files/verify/:id */
  VERIFY: (id: number) => `/files/verify/${id}`,
  /** 檢查網路儲存 POST /files/check-network */
  CHECK_NETWORK: '/files/check-network',
} as const;

// ============================================================================
// 使用者與權限管理端點
// ============================================================================

/** 使用者 API 端點 */
export const USERS_ENDPOINTS = {
  /** 使用者列表 POST /users/list */
  LIST: '/users/list',
  /** 建立使用者 POST /users */
  CREATE: '/users',
  /** 使用者詳情 POST /users/:id/detail */
  DETAIL: (id: number) => `/users/${id}/detail`,
  /** 更新使用者 POST /users/:id/update */
  UPDATE: (id: number) => `/users/${id}/update`,
  /** 刪除使用者 POST /users/:id/delete */
  DELETE: (id: number) => `/users/${id}/delete`,
  /** 更新狀態 POST /users/:id/status */
  STATUS: (id: number) => `/users/${id}/status`,
} as const;

/** 證照管理 API 端點 */
export const CERTIFICATIONS_ENDPOINTS = {
  /** 新增證照 POST /certifications/create */
  CREATE: '/certifications/create',
  /** 使用者證照列表 POST /certifications/user/:userId/list */
  USER_LIST: (userId: number) => `/certifications/user/${userId}/list`,
  /** 證照詳情 POST /certifications/:id/detail */
  DETAIL: (id: number) => `/certifications/${id}/detail`,
  /** 更新證照 POST /certifications/:id/update */
  UPDATE: (id: number) => `/certifications/${id}/update`,
  /** 刪除證照 POST /certifications/:id/delete */
  DELETE: (id: number) => `/certifications/${id}/delete`,
  /** 使用者證照統計 POST /certifications/stats/:userId */
  STATS: (userId: number) => `/certifications/stats/${userId}`,
} as const;

/** 認證 API 端點 */
export const AUTH_ENDPOINTS = {
  /** 登入 POST /auth/login */
  LOGIN: '/auth/login',
  /** 登出 POST /auth/logout */
  LOGOUT: '/auth/logout',
  /** 刷新 Token POST /auth/refresh */
  REFRESH: '/auth/refresh',
  /** 當前使用者 POST /auth/me */
  ME: '/auth/me',
} as const;

/** 管理員使用者管理 API 端點 (POST-only) */
export const ADMIN_USER_MANAGEMENT_ENDPOINTS = {
  /** 使用者列表 POST /admin/user-management/users/list */
  USERS_LIST: '/admin/user-management/users/list',
  /** 建立使用者 POST /admin/user-management/users */
  USERS_CREATE: '/admin/user-management/users',
  /** 使用者詳情 POST /admin/user-management/users/:id/detail */
  USERS_DETAIL: (id: number) => `/admin/user-management/users/${id}/detail`,
  /** 更新使用者 POST /admin/user-management/users/:id/update */
  USERS_UPDATE: (id: number) => `/admin/user-management/users/${id}/update`,
  /** 刪除使用者 POST /admin/user-management/users/:id/delete */
  USERS_DELETE: (id: number) => `/admin/user-management/users/${id}/delete`,
  /** 使用者權限詳情 POST /admin/user-management/users/:id/permissions/detail */
  USERS_PERMISSIONS_DETAIL: (id: number) => `/admin/user-management/users/${id}/permissions/detail`,
  /** 更新使用者權限 POST /admin/user-management/users/:id/permissions/update */
  USERS_PERMISSIONS_UPDATE: (id: number) => `/admin/user-management/users/${id}/permissions/update`,
  /** 使用者會話列表 POST /admin/user-management/users/:id/sessions/list */
  USERS_SESSIONS_LIST: (id: number) => `/admin/user-management/users/${id}/sessions/list`,
  /** 撤銷會話 POST /admin/user-management/sessions/:id/revoke */
  SESSIONS_REVOKE: (id: number) => `/admin/user-management/sessions/${id}/revoke`,
  /** 可用權限 POST /admin/user-management/permissions/available */
  PERMISSIONS_AVAILABLE: '/admin/user-management/permissions/available',
} as const;

// ============================================================================
// 關聯模組端點
// ============================================================================

/** 案件廠商關聯 API 端點 */
export const PROJECT_VENDORS_ENDPOINTS = {
  /** 關聯列表 POST /project-vendors/list */
  LIST: '/project-vendors/list',
  /** 建立關聯 POST /project-vendors */
  CREATE: '/project-vendors',
  /** 刪除關聯 POST /project-vendors/:id/delete */
  DELETE: (id: number) => `/project-vendors/${id}/delete`,
} as const;

/** 案件承辦同仁 API 端點 */
export const PROJECT_STAFF_ENDPOINTS = {
  /** 同仁列表 POST /project-staff/list */
  LIST: '/project-staff/list',
  /** 建立關聯 POST /project-staff */
  CREATE: '/project-staff',
  /** 刪除關聯 POST /project-staff/:id/delete */
  DELETE: (id: number) => `/project-staff/${id}/delete`,
} as const;

/** 專案機關承辦 API 端點 */
export const PROJECT_AGENCY_CONTACTS_ENDPOINTS = {
  /** 承辦列表 POST /project-agency-contacts/list */
  LIST: '/project-agency-contacts/list',
  /** 建立承辦 POST /project-agency-contacts */
  CREATE: '/project-agency-contacts',
  /** 刪除承辦 POST /project-agency-contacts/:id/delete */
  DELETE: (id: number) => `/project-agency-contacts/${id}/delete`,
} as const;

// ============================================================================
// 系統管理端點
// ============================================================================

// DOCUMENT_NUMBERS_ENDPOINTS 已移除
// 請使用 DOCUMENTS_ENDPOINTS 並設定 category='send'
// 取得下一個發文字號請使用 DOCUMENTS_ENDPOINTS.NEXT_SEND_NUMBER

/** 提醒管理 API 端點 */
export const REMINDER_MANAGEMENT_ENDPOINTS = {
  /** 提醒列表 POST /reminder-management/list */
  LIST: '/reminder-management/list',
  /** 建立提醒 POST /reminder-management */
  CREATE: '/reminder-management',
  /** 更新提醒 POST /reminder-management/:id/update */
  UPDATE: (id: number) => `/reminder-management/${id}/update`,
  /** 刪除提醒 POST /reminder-management/:id/delete */
  DELETE: (id: number) => `/reminder-management/${id}/delete`,
} as const;

/** CSV 匯入 API 端點 */
export const CSV_IMPORT_ENDPOINTS = {
  /** 上傳並匯入 POST /csv-import/upload-and-import */
  UPLOAD_AND_IMPORT: '/csv-import/upload-and-import',
  /** 驗證檔案 POST /csv-import/validate */
  VALIDATE: '/csv-import/validate',
  /** 匯入歷史 POST /csv-import/history */
  HISTORY: '/csv-import/history',
} as const;

/** 公開 API 端點 */
export const PUBLIC_ENDPOINTS = {
  /** 行事曆狀態 GET /public/calendar-status */
  CALENDAR_STATUS: '/public/calendar-status',
  /** 系統健康 GET /public/health */
  HEALTH: '/public/health',
} as const;

/** 系統監控 API 端點 */
export const SYSTEM_ENDPOINTS = {
  /** 系統狀態 POST /system/status */
  STATUS: '/system/status',
  /** 系統指標 POST /system/metrics */
  METRICS: '/system/metrics',
} as const;

/** 管理員資料庫 API 端點 */
export const ADMIN_DATABASE_ENDPOINTS = {
  /** 資料庫資訊 POST /admin/database/info */
  INFO: '/admin/database/info',
  /** 資料表詳情 POST /admin/database/table/:tableName */
  TABLE: (tableName: string) => `/admin/database/table/${tableName}`,
  /** 執行查詢 POST /admin/database/query */
  QUERY: '/admin/database/query',
  /** 健康檢查 POST /admin/database/health */
  HEALTH: '/admin/database/health',
  /** 完整性檢查 POST /admin/database/integrity */
  INTEGRITY: '/admin/database/integrity',
} as const;

/** 資料庫備份 API 端點 */
export const BACKUP_ENDPOINTS = {
  /** 建立備份 POST /backup/create */
  CREATE: '/backup/create',
  /** 備份列表 POST /backup/list */
  LIST: '/backup/list',
  /** 刪除備份 POST /backup/delete */
  DELETE: '/backup/delete',
  /** 還原備份 POST /backup/restore */
  RESTORE: '/backup/restore',
  /** 備份設定 POST /backup/config */
  CONFIG: '/backup/config',
  /** 備份狀態 POST /backup/status */
  STATUS: '/backup/status',
} as const;

// ============================================================================
// 桃園查估派工管理系統端點
// ============================================================================

/** 桃園派工管理 API 端點 */
export const TAOYUAN_DISPATCH_ENDPOINTS = {
  // 轄管工程清單
  /** 工程列表 POST /taoyuan-dispatch/projects/list */
  PROJECTS_LIST: '/taoyuan-dispatch/projects/list',
  /** 建立工程 POST /taoyuan-dispatch/projects/create */
  PROJECTS_CREATE: '/taoyuan-dispatch/projects/create',
  /** 工程詳情 POST /taoyuan-dispatch/projects/:id/detail */
  PROJECTS_DETAIL: (id: number) => `/taoyuan-dispatch/projects/${id}/detail`,
  /** 更新工程 POST /taoyuan-dispatch/projects/:id/update */
  PROJECTS_UPDATE: (id: number) => `/taoyuan-dispatch/projects/${id}/update`,
  /** 刪除工程 POST /taoyuan-dispatch/projects/:id/delete */
  PROJECTS_DELETE: (id: number) => `/taoyuan-dispatch/projects/${id}/delete`,
  /** Excel 匯入工程 POST /taoyuan-dispatch/projects/import */
  PROJECTS_IMPORT: '/taoyuan-dispatch/projects/import',
  /** 下載匯入範本 GET /taoyuan-dispatch/projects/import-template */
  PROJECTS_IMPORT_TEMPLATE: '/taoyuan-dispatch/projects/import-template',

  // 派工紀錄
  /** 派工單列表 POST /taoyuan-dispatch/dispatch/list */
  DISPATCH_ORDERS_LIST: '/taoyuan-dispatch/dispatch/list',
  /** 建立派工單 POST /taoyuan-dispatch/dispatch/create */
  DISPATCH_ORDERS_CREATE: '/taoyuan-dispatch/dispatch/create',
  /** 派工單詳情 POST /taoyuan-dispatch/dispatch/:id/detail */
  DISPATCH_ORDERS_DETAIL: (id: number) => `/taoyuan-dispatch/dispatch/${id}/detail`,
  /** 更新派工單 POST /taoyuan-dispatch/dispatch/:id/update */
  DISPATCH_ORDERS_UPDATE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/update`,
  /** 刪除派工單 POST /taoyuan-dispatch/dispatch/:id/delete */
  DISPATCH_ORDERS_DELETE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/delete`,

  // 派工單公文關聯
  /** 新增公文關聯 POST /taoyuan-dispatch/dispatch/:id/link-document */
  DISPATCH_LINK_DOCUMENT: (id: number) => `/taoyuan-dispatch/dispatch/${id}/link-document`,
  /** 移除派工單公文關聯 POST /taoyuan-dispatch/dispatch/:id/unlink-document/:linkId */
  DISPATCH_UNLINK_DOCUMENT: (id: number, linkId: number) => `/taoyuan-dispatch/dispatch/${id}/unlink-document/${linkId}`,
  /** 取得派工單公文 POST /taoyuan-dispatch/dispatch/:id/documents */
  DISPATCH_DOCUMENTS: (id: number) => `/taoyuan-dispatch/dispatch/${id}/documents`,

  // 契金管控
  /** 契金列表 POST /taoyuan-dispatch/payments/list */
  PAYMENTS_LIST: '/taoyuan-dispatch/payments/list',
  /** 建立契金 POST /taoyuan-dispatch/payments/create */
  PAYMENTS_CREATE: '/taoyuan-dispatch/payments/create',
  /** 更新契金 POST /taoyuan-dispatch/payments/:id/update */
  PAYMENTS_UPDATE: (id: number) => `/taoyuan-dispatch/payments/${id}/update`,
  /** 刪除契金 POST /taoyuan-dispatch/payments/:id/delete */
  PAYMENTS_DELETE: (id: number) => `/taoyuan-dispatch/payments/${id}/delete`,

  // 總控表
  /** 總控表查詢 POST /taoyuan-dispatch/master-control */
  MASTER_CONTROL: '/taoyuan-dispatch/master-control',
} as const;

// ============================================================================
// 統一匯出
// ============================================================================

/**
 * API 端點集合
 *
 * 使用方式:
 * ```typescript
 * import { API_ENDPOINTS } from './endpoints';
 *
 * // 靜態端點
 * apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);
 *
 * // 動態端點
 * apiClient.post(API_ENDPOINTS.DOCUMENTS.DETAIL(123));
 * ```
 */
export const API_ENDPOINTS = {
  // 核心功能
  DASHBOARD: DASHBOARD_ENDPOINTS,
  DOCUMENTS: DOCUMENTS_ENDPOINTS,
  PROJECTS: PROJECTS_ENDPOINTS,
  AGENCIES: AGENCIES_ENDPOINTS,
  VENDORS: VENDORS_ENDPOINTS,

  // 行事曆
  CALENDAR: CALENDAR_ENDPOINTS,

  // 通知
  SYSTEM_NOTIFICATIONS: SYSTEM_NOTIFICATIONS_ENDPOINTS,
  PROJECT_NOTIFICATIONS: PROJECT_NOTIFICATIONS_ENDPOINTS,

  // 檔案
  FILES: FILES_ENDPOINTS,

  // 使用者與權限
  USERS: USERS_ENDPOINTS,
  AUTH: AUTH_ENDPOINTS,
  ADMIN_USER_MANAGEMENT: ADMIN_USER_MANAGEMENT_ENDPOINTS,
  CERTIFICATIONS: CERTIFICATIONS_ENDPOINTS,

  // 關聯模組
  PROJECT_VENDORS: PROJECT_VENDORS_ENDPOINTS,
  PROJECT_STAFF: PROJECT_STAFF_ENDPOINTS,
  PROJECT_AGENCY_CONTACTS: PROJECT_AGENCY_CONTACTS_ENDPOINTS,

  // 系統管理
  // DOCUMENT_NUMBERS 已移除，請使用 DOCUMENTS.NEXT_SEND_NUMBER
  REMINDER_MANAGEMENT: REMINDER_MANAGEMENT_ENDPOINTS,
  CSV_IMPORT: CSV_IMPORT_ENDPOINTS,
  PUBLIC: PUBLIC_ENDPOINTS,
  SYSTEM: SYSTEM_ENDPOINTS,
  ADMIN_DATABASE: ADMIN_DATABASE_ENDPOINTS,
  BACKUP: BACKUP_ENDPOINTS,

  // 桃園派工管理
  TAOYUAN_DISPATCH: TAOYUAN_DISPATCH_ENDPOINTS,
} as const;

// 預設匯出
export default API_ENDPOINTS;
