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
  /** 匯出公文 Excel POST /documents-enhanced/export/excel */
  EXPORT_EXCEL: '/documents-enhanced/export/excel',
  /** 匯入 Excel 預覽 POST /documents-enhanced/import/excel/preview */
  IMPORT_EXCEL_PREVIEW: '/documents-enhanced/import/excel/preview',
  /** 匯入 Excel POST /documents-enhanced/import/excel */
  IMPORT_EXCEL: '/documents-enhanced/import/excel',
  /** 匯入 Excel 範本 POST /documents-enhanced/import/excel/template */
  IMPORT_EXCEL_TEMPLATE: '/documents-enhanced/import/excel/template',
  /** 審計日誌列表 POST /documents-enhanced/audit-logs */
  AUDIT_LOGS: '/documents-enhanced/audit-logs',
  /** 公文審計歷史 POST /documents-enhanced/:id/audit-history */
  AUDIT_HISTORY: (id: number) => `/documents-enhanced/${id}/audit-history`,
  /** 整合搜尋 POST /documents-enhanced/integrated-search */
  INTEGRATED_SEARCH: '/documents-enhanced/integrated-search',
  /** 取得下一個發文字號 POST /documents-enhanced/next-send-number */
  NEXT_SEND_NUMBER: '/documents-enhanced/next-send-number',
  /** 公文趨勢統計 POST /documents-enhanced/trends */
  TRENDS: '/documents-enhanced/trends',
  /** 公文處理效率 POST /documents-enhanced/efficiency */
  EFFICIENCY: '/documents-enhanced/efficiency',
} as const;

/** 承攬案件 API 端點 */
export const PROJECTS_ENDPOINTS = {
  /** 專案列表 POST /projects/list */
  LIST: '/projects/list',
  /** 建立專案 POST /projects/create */
  CREATE: '/projects/create',
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
  /** 事件詳情 POST /calendar/events/detail */
  EVENTS_DETAIL: '/calendar/events/detail',
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
  /** 檢查公文是否已有事件 POST /calendar/events/check-document */
  EVENTS_CHECK_DOCUMENT: '/calendar/events/check-document',
  /** 建立事件含提醒 POST /calendar/events/create-with-reminders */
  EVENTS_CREATE_WITH_REMINDERS: '/calendar/events/create-with-reminders',
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
  /** 部門選項 POST /users/departments */
  DEPARTMENTS: '/users/departments',
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
  /** 上傳證照附件 POST /certifications/:id/upload-attachment */
  UPLOAD_ATTACHMENT: (id: number) => `/certifications/${id}/upload-attachment`,
  /** 下載證照附件 POST /certifications/:id/download-attachment */
  DOWNLOAD_ATTACHMENT: (id: number) => `/certifications/${id}/download-attachment`,
  /** 刪除證照附件 POST /certifications/:id/delete-attachment */
  DELETE_ATTACHMENT: (id: number) => `/certifications/${id}/delete-attachment`,
} as const;

/** 認證 API 端點 */
export const AUTH_ENDPOINTS = {
  /** 登入 POST /auth/login */
  LOGIN: '/auth/login',
  /** Google OAuth 登入 POST /auth/google */
  GOOGLE: '/auth/google',
  /** 使用者註冊 POST /auth/register */
  REGISTER: '/auth/register',
  /** 登出 POST /auth/logout */
  LOGOUT: '/auth/logout',
  /** 刷新 Token POST /auth/refresh */
  REFRESH: '/auth/refresh',
  /** 當前使用者 POST /auth/me */
  ME: '/auth/me',
  /** 認證狀態檢查 POST /auth/check */
  CHECK: '/auth/check',
  /** 更新個人資料 POST /auth/profile/update */
  PROFILE_UPDATE: '/auth/profile/update',
  /** 修改密碼 POST /auth/password/change */
  PASSWORD_CHANGE: '/auth/password/change',
  /** 請求密碼重設 POST /auth/password-reset */
  PASSWORD_RESET: '/auth/password-reset',
  /** 確認密碼重設 POST /auth/password-reset-confirm */
  PASSWORD_RESET_CONFIRM: '/auth/password-reset-confirm',
  /** 發送 Email 驗證信 POST /auth/send-verification */
  SEND_VERIFICATION: '/auth/send-verification',
  /** 驗證 Email POST /auth/verify-email */
  VERIFY_EMAIL: '/auth/verify-email',
  /** 登入歷史 POST /auth/login-history */
  LOGIN_HISTORY: '/auth/login-history',
  /** 活躍 Session 列表 POST /auth/sessions */
  SESSIONS: '/auth/sessions',
  /** 撤銷指定 Session POST /auth/sessions/revoke */
  SESSION_REVOKE: '/auth/sessions/revoke',
  /** 撤銷所有其他 Session POST /auth/sessions/revoke-all */
  SESSION_REVOKE_ALL: '/auth/sessions/revoke-all',
  /** MFA 設定 POST /auth/mfa/setup */
  MFA_SETUP: '/auth/mfa/setup',
  /** MFA 驗證並啟用 POST /auth/mfa/verify */
  MFA_VERIFY: '/auth/mfa/verify',
  /** MFA 停用 POST /auth/mfa/disable */
  MFA_DISABLE: '/auth/mfa/disable',
  /** MFA 登入驗證 POST /auth/mfa/validate */
  MFA_VALIDATE: '/auth/mfa/validate',
  /** MFA 狀態查詢 POST /auth/mfa/status */
  MFA_STATUS: '/auth/mfa/status',
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
  /** 檢查權限 POST /admin/user-management/permissions/check */
  PERMISSIONS_CHECK: '/admin/user-management/permissions/check',
} as const;

// ============================================================================
// 關聯模組端點
// ============================================================================

/** 案件廠商關聯 API 端點 */
export const PROJECT_VENDORS_ENDPOINTS = {
  /** 案件廠商列表 POST /project-vendors/project/:projectId/list */
  PROJECT_LIST: (projectId: number) => `/project-vendors/project/${projectId}/list`,
  /** 全部關聯列表 POST /project-vendors/list */
  LIST: '/project-vendors/list',
  /** 建立關聯 POST /project-vendors */
  CREATE: '/project-vendors',
  /** 更新關聯 POST /project-vendors/project/:projectId/vendor/:vendorId/update */
  UPDATE: (projectId: number, vendorId: number) =>
    `/project-vendors/project/${projectId}/vendor/${vendorId}/update`,
  /** 刪除關聯 POST /project-vendors/project/:projectId/vendor/:vendorId/delete */
  DELETE: (projectId: number, vendorId: number) =>
    `/project-vendors/project/${projectId}/vendor/${vendorId}/delete`,
} as const;

/** 案件承辦同仁 API 端點 */
export const PROJECT_STAFF_ENDPOINTS = {
  /** 全部關聯列表 POST /project-staff/list */
  LIST: '/project-staff/list',
  /** 建立關聯 POST /project-staff */
  CREATE: '/project-staff',
  /** 案件承辦同仁列表 POST /project-staff/project/:projectId/list */
  PROJECT_LIST: (projectId: number) => `/project-staff/project/${projectId}/list` as const,
  /** 更新關聯 POST /project-staff/project/:projectId/user/:userId/update */
  UPDATE: (projectId: number, userId: number) => `/project-staff/project/${projectId}/user/${userId}/update` as const,
  /** 刪除關聯 POST /project-staff/project/:projectId/user/:userId/delete */
  DELETE: (projectId: number, userId: number) => `/project-staff/project/${projectId}/user/${userId}/delete` as const,
} as const;

/** 專案機關承辦 API 端點 */
export const PROJECT_AGENCY_CONTACTS_ENDPOINTS = {
  /** 承辦列表 POST /project-agency-contacts/list */
  LIST: '/project-agency-contacts/list',
  /** 承辦詳情 POST /project-agency-contacts/detail */
  DETAIL: '/project-agency-contacts/detail',
  /** 建立承辦 POST /project-agency-contacts/create */
  CREATE: '/project-agency-contacts/create',
  /** 更新承辦 POST /project-agency-contacts/update */
  UPDATE: '/project-agency-contacts/update',
  /** 刪除承辦 POST /project-agency-contacts/delete */
  DELETE: '/project-agency-contacts/delete',
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
  /** 系統健康摘要 GET /health/summary */
  HEALTH_SUMMARY: '/health/summary',
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
  // === 異地備份設定 ===
  /** 異地備份設定 POST /backup/remote-config */
  REMOTE_CONFIG: '/backup/remote-config',
  /** 更新異地備份設定 POST /backup/remote-config/update */
  REMOTE_CONFIG_UPDATE: '/backup/remote-config/update',
  /** 手動異地同步 POST /backup/remote-sync */
  REMOTE_SYNC: '/backup/remote-sync',
  // === 備份日誌 ===
  /** 備份日誌 POST /backup/logs */
  LOGS: '/backup/logs',
  // === 排程器控制 ===
  /** 排程器狀態 POST /backup/scheduler/status */
  SCHEDULER_STATUS: '/backup/scheduler/status',
  /** 啟動排程器 POST /backup/scheduler/start */
  SCHEDULER_START: '/backup/scheduler/start',
  /** 停止排程器 POST /backup/scheduler/stop */
  SCHEDULER_STOP: '/backup/scheduler/stop',
  // === 環境狀態與清理 ===
  /** 環境狀態 POST /backup/environment-status */
  ENVIRONMENT_STATUS: '/backup/environment-status',
  /** 清理孤立檔案 POST /backup/cleanup */
  CLEANUP: '/backup/cleanup',
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
  /** 下載匯入範本 POST /taoyuan-dispatch/projects/import-template */
  PROJECTS_IMPORT_TEMPLATE: '/taoyuan-dispatch/projects/import-template',

  // 承攬案件切換
  /** 桃園派工承攬案件列表 POST /taoyuan-dispatch/dispatch/contract-projects */
  DISPATCH_CONTRACT_PROJECTS: '/taoyuan-dispatch/dispatch/contract-projects',

  // 派工紀錄
  /** 派工單列表 POST /taoyuan-dispatch/dispatch/list */
  DISPATCH_ORDERS_LIST: '/taoyuan-dispatch/dispatch/list',
  /** 取得下一個派工單號 POST /taoyuan-dispatch/dispatch/next-dispatch-no */
  DISPATCH_NEXT_NO: '/taoyuan-dispatch/dispatch/next-dispatch-no',
  /** 建立派工單 POST /taoyuan-dispatch/dispatch/create */
  DISPATCH_ORDERS_CREATE: '/taoyuan-dispatch/dispatch/create',
  /** Excel 匯入派工紀錄 POST /taoyuan-dispatch/dispatch/import */
  DISPATCH_IMPORT: '/taoyuan-dispatch/dispatch/import',
  /** 下載派工紀錄匯入範本 POST /taoyuan-dispatch/dispatch/import-template */
  DISPATCH_IMPORT_TEMPLATE: '/taoyuan-dispatch/dispatch/import-template',
  /** 派工單詳情 POST /taoyuan-dispatch/dispatch/:id/detail */
  DISPATCH_ORDERS_DETAIL: (id: number) => `/taoyuan-dispatch/dispatch/${id}/detail`,
  /** 更新派工單 POST /taoyuan-dispatch/dispatch/:id/update */
  DISPATCH_ORDERS_UPDATE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/update`,
  /** 刪除派工單 POST /taoyuan-dispatch/dispatch/:id/delete */
  DISPATCH_ORDERS_DELETE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/delete`,
  /** 批量設定結案批次 POST /taoyuan-dispatch/dispatch/batch-set-batch */
  DISPATCH_BATCH_SET_BATCH: '/taoyuan-dispatch/dispatch/batch-set-batch',

  // 派工單公文關聯
  /** 新增公文關聯 POST /taoyuan-dispatch/dispatch/:id/link-document */
  DISPATCH_LINK_DOCUMENT: (id: number) => `/taoyuan-dispatch/dispatch/${id}/link-document`,
  /** 移除派工單公文關聯 POST /taoyuan-dispatch/dispatch/:id/unlink-document/:linkId */
  DISPATCH_UNLINK_DOCUMENT: (id: number, linkId: number) => `/taoyuan-dispatch/dispatch/${id}/unlink-document/${linkId}`,
  /** 取得派工單公文 POST /taoyuan-dispatch/dispatch/:id/documents */
  DISPATCH_DOCUMENTS: (id: number) => `/taoyuan-dispatch/dispatch/${id}/documents`,
  /** 搜尋可關聯的桃園派工公文 POST /taoyuan-dispatch/dispatch/search-linkable-documents */
  DISPATCH_SEARCH_LINKABLE_DOCUMENTS: '/taoyuan-dispatch/dispatch/search-linkable-documents',
  /** 知識圖譜實體配對建議 POST /taoyuan-dispatch/dispatch/:id/entity-similarity */
  DISPATCH_ENTITY_SIMILARITY: (id: number) => `/taoyuan-dispatch/dispatch/${id}/entity-similarity`,
  /** NER 驅動公文對照建議 POST /taoyuan-dispatch/dispatch/:id/correspondence-suggestions */
  DISPATCH_CORRESPONDENCE_SUGGESTIONS: (id: number) => `/taoyuan-dispatch/dispatch/${id}/correspondence-suggestions`,
  /** 確認公文對照配對（回饋圖譜） POST /taoyuan-dispatch/dispatch/:id/confirm-correspondence */
  DISPATCH_CONFIRM_CORRESPONDENCE: (id: number) => `/taoyuan-dispatch/dispatch/${id}/confirm-correspondence`,

  // 匯出
  /** 派工總表 Excel 匯出 POST /taoyuan-dispatch/dispatch/export/excel */
  DISPATCH_EXPORT_EXCEL: '/taoyuan-dispatch/dispatch/export/excel',
  /** 非同步匯出 POST /taoyuan-dispatch/dispatch/export/excel/async */
  DISPATCH_EXPORT_ASYNC: '/taoyuan-dispatch/dispatch/export/excel/async',
  /** 匯出進度 POST /taoyuan-dispatch/dispatch/export/excel/progress */
  DISPATCH_EXPORT_PROGRESS: '/taoyuan-dispatch/dispatch/export/excel/progress',
  /** 下載匯出結果 POST /taoyuan-dispatch/dispatch/export/excel/download */
  DISPATCH_EXPORT_DOWNLOAD: '/taoyuan-dispatch/dispatch/export/excel/download',

  // 公文歷程匹配 (對應原始需求欄位 14-17)
  /** 匹配公文歷程 POST /taoyuan-dispatch/dispatch/match-documents */
  MATCH_DOCUMENTS: '/taoyuan-dispatch/dispatch/match-documents',
  /** 派工單詳情含公文歷程 POST /taoyuan-dispatch/dispatch/:id/detail-with-history */
  DISPATCH_DETAIL_WITH_HISTORY: (id: number) => `/taoyuan-dispatch/dispatch/${id}/detail-with-history`,

  // 以公文為主體的關聯 API
  /** 查詢公文關聯的派工單 POST /taoyuan-dispatch/document/:id/dispatch-links */
  DOCUMENT_DISPATCH_LINKS: (id: number) => `/taoyuan-dispatch/document/${id}/dispatch-links`,
  /** 將公文關聯到派工單 POST /taoyuan-dispatch/document/:id/link-dispatch */
  DOCUMENT_LINK_DISPATCH: (id: number) => `/taoyuan-dispatch/document/${id}/link-dispatch`,
  /** 移除公文與派工的關聯 POST /taoyuan-dispatch/document/:docId/unlink-dispatch/:linkId */
  DOCUMENT_UNLINK_DISPATCH: (docId: number, linkId: number) => `/taoyuan-dispatch/document/${docId}/unlink-dispatch/${linkId}`,
  /** 批次查詢多筆公文的派工關聯 POST /taoyuan-dispatch/documents/batch-dispatch-links */
  DOCUMENTS_BATCH_DISPATCH_LINKS: '/taoyuan-dispatch/documents/batch-dispatch-links',

  // 以工程為主體的關聯 API
  /** 查詢工程關聯的派工單 POST /taoyuan-dispatch/project/:id/dispatch-links */
  PROJECT_DISPATCH_LINKS: (id: number) => `/taoyuan-dispatch/project/${id}/dispatch-links`,
  /** 將工程關聯到派工單 POST /taoyuan-dispatch/project/:id/link-dispatch */
  PROJECT_LINK_DISPATCH: (id: number) => `/taoyuan-dispatch/project/${id}/link-dispatch`,
  /** 移除工程與派工的關聯 POST /taoyuan-dispatch/project/:projId/unlink-dispatch/:linkId */
  PROJECT_UNLINK_DISPATCH: (projId: number, linkId: number) => `/taoyuan-dispatch/project/${projId}/unlink-dispatch/${linkId}`,
  /** 批次查詢多筆工程的派工關聯 POST /taoyuan-dispatch/projects/batch-dispatch-links */
  PROJECTS_BATCH_DISPATCH_LINKS: '/taoyuan-dispatch/projects/batch-dispatch-links',

  // 公文-工程直接關聯 API (不經過派工單)
  /** 查詢公文關聯的工程 POST /taoyuan-dispatch/document/:id/project-links */
  DOCUMENT_PROJECT_LINKS: (id: number) => `/taoyuan-dispatch/document/${id}/project-links`,
  /** 將公文關聯到工程 POST /taoyuan-dispatch/document/:id/link-project */
  DOCUMENT_LINK_PROJECT: (id: number) => `/taoyuan-dispatch/document/${id}/link-project`,
  /** 移除公文與工程的關聯 POST /taoyuan-dispatch/document/:docId/unlink-project/:linkId */
  DOCUMENT_UNLINK_PROJECT: (docId: number, linkId: number) => `/taoyuan-dispatch/document/${docId}/unlink-project/${linkId}`,
  /** 批次查詢多筆公文的工程關聯 POST /taoyuan-dispatch/documents/batch-project-links */
  DOCUMENTS_BATCH_PROJECT_LINKS: '/taoyuan-dispatch/documents/batch-project-links',

  // 契金管控
  /** 契金列表 POST /taoyuan-dispatch/payments/list */
  PAYMENTS_LIST: '/taoyuan-dispatch/payments/list',
  /** 建立契金 POST /taoyuan-dispatch/payments/create */
  PAYMENTS_CREATE: '/taoyuan-dispatch/payments/create',
  /** 更新契金 POST /taoyuan-dispatch/payments/:id/update */
  PAYMENTS_UPDATE: (id: number) => `/taoyuan-dispatch/payments/${id}/update`,
  /** 刪除契金 POST /taoyuan-dispatch/payments/:id/delete */
  PAYMENTS_DELETE: (id: number) => `/taoyuan-dispatch/payments/${id}/delete`,
  /** 契金管控展示 POST /taoyuan-dispatch/payments/control */
  PAYMENTS_CONTROL: '/taoyuan-dispatch/payments/control',

  // 總控表
  /** 總控表查詢 POST /taoyuan-dispatch/master-control */
  MASTER_CONTROL: '/taoyuan-dispatch/master-control',

  // 統計資料
  /** 桃園查估派工統計 POST /taoyuan-dispatch/statistics */
  STATISTICS: '/taoyuan-dispatch/statistics',

  // 派工單附件
  /** 上傳派工單附件 POST /taoyuan-dispatch/dispatch/:id/attachments/upload */
  DISPATCH_ATTACHMENTS_UPLOAD: (id: number) => `/taoyuan-dispatch/dispatch/${id}/attachments/upload`,
  /** 取得派工單附件列表 POST /taoyuan-dispatch/dispatch/:id/attachments/list */
  DISPATCH_ATTACHMENTS_LIST: (id: number) => `/taoyuan-dispatch/dispatch/${id}/attachments/list`,
  /** 下載附件 POST /taoyuan-dispatch/dispatch/attachments/:id/download */
  DISPATCH_ATTACHMENT_DOWNLOAD: (id: number) => `/taoyuan-dispatch/dispatch/attachments/${id}/download`,
  /** 刪除附件 POST /taoyuan-dispatch/dispatch/attachments/:id/delete */
  DISPATCH_ATTACHMENT_DELETE: (id: number) => `/taoyuan-dispatch/dispatch/attachments/${id}/delete`,
  /** 驗證附件完整性 POST /taoyuan-dispatch/dispatch/attachments/:id/verify */
  DISPATCH_ATTACHMENT_VERIFY: (id: number) => `/taoyuan-dispatch/dispatch/attachments/${id}/verify`,

  // 作業歷程
  /** 作業歷程列表（依派工單）POST /taoyuan-dispatch/workflow/list */
  WORKFLOW_LIST: '/taoyuan-dispatch/workflow/list',
  /** 作業歷程列表（依工程）POST /taoyuan-dispatch/workflow/by-project */
  WORKFLOW_BY_PROJECT: '/taoyuan-dispatch/workflow/by-project',
  /** 建立作業紀錄 POST /taoyuan-dispatch/workflow/create */
  WORKFLOW_CREATE: '/taoyuan-dispatch/workflow/create',
  /** 取得作業紀錄 POST /taoyuan-dispatch/workflow/:id */
  WORKFLOW_DETAIL: (id: number) => `/taoyuan-dispatch/workflow/${id}`,
  /** 更新作業紀錄 POST /taoyuan-dispatch/workflow/:id/update */
  WORKFLOW_UPDATE: (id: number) => `/taoyuan-dispatch/workflow/${id}/update`,
  /** 刪除作業紀錄 POST /taoyuan-dispatch/workflow/:id/delete */
  WORKFLOW_DELETE: (id: number) => `/taoyuan-dispatch/workflow/${id}/delete`,
  /** 批量更新批次歸屬 POST /taoyuan-dispatch/workflow/batch-update */
  WORKFLOW_BATCH_UPDATE: '/taoyuan-dispatch/workflow/batch-update',
  /** 工程歷程總覽 POST /taoyuan-dispatch/workflow/summary/:projectId */
  WORKFLOW_SUMMARY: (projectId: number) => `/taoyuan-dispatch/workflow/summary/${projectId}`,
} as const;

// ============================================================================
// AI 服務端點
// ============================================================================

/** AI 服務 API 端點 */
export const AI_ENDPOINTS = {
  /** 公文摘要 POST /ai/document/summary */
  SUMMARY: '/ai/document/summary',
  /** 串流摘要 POST /ai/document/summary/stream */
  SUMMARY_STREAM: '/ai/document/summary/stream',
  /** 分類建議 POST /ai/document/classify */
  CLASSIFY: '/ai/document/classify',
  /** 關鍵字提取 POST /ai/document/keywords */
  KEYWORDS: '/ai/document/keywords',
  /** 自然語言搜尋 POST /ai/document/natural-search */
  NATURAL_SEARCH: '/ai/document/natural-search',
  /** 意圖解析 POST /ai/document/parse-intent */
  PARSE_INTENT: '/ai/document/parse-intent',
  /** 機關匹配 POST /ai/agency/match */
  AGENCY_MATCH: '/ai/agency/match',
  /** 健康檢查 POST /ai/health */
  HEALTH: '/ai/health',
  /** AI 配置 POST /ai/config */
  CONFIG: '/ai/config',
  /** AI 統計 POST /ai/stats */
  STATS: '/ai/stats',
  /** 重設統計 POST /ai/stats/reset */
  STATS_RESET: '/ai/stats/reset',
  /** 同義詞列表 POST /ai/synonyms/list */
  SYNONYMS_LIST: '/ai/synonyms/list',
  /** 新增同義詞 POST /ai/synonyms/create */
  SYNONYMS_CREATE: '/ai/synonyms/create',
  /** 更新同義詞 POST /ai/synonyms/update */
  SYNONYMS_UPDATE: '/ai/synonyms/update',
  /** 刪除同義詞 POST /ai/synonyms/delete */
  SYNONYMS_DELETE: '/ai/synonyms/delete',
  /** 重新載入同義詞 POST /ai/synonyms/reload */
  SYNONYMS_RELOAD: '/ai/synonyms/reload',
  /** Prompt 版本列表 POST /ai/prompts/list */
  PROMPTS_LIST: '/ai/prompts/list',
  /** 新增 Prompt 版本 POST /ai/prompts/create */
  PROMPTS_CREATE: '/ai/prompts/create',
  /** 啟用 Prompt 版本 POST /ai/prompts/activate */
  PROMPTS_ACTIVATE: '/ai/prompts/activate',
  /** Prompt 版本比較 POST /ai/prompts/compare */
  PROMPTS_COMPARE: '/ai/prompts/compare',
  /** 搜尋歷史列表 POST /ai/search-history/list */
  SEARCH_HISTORY_LIST: '/ai/search-history/list',
  /** 搜尋統計 POST /ai/search-history/stats */
  SEARCH_HISTORY_STATS: '/ai/search-history/stats',
  /** 清除搜尋歷史 POST /ai/search-history/clear */
  SEARCH_HISTORY_CLEAR: '/ai/search-history/clear',
  /** 搜尋回饋 POST /ai/search-history/feedback */
  SEARCH_HISTORY_FEEDBACK: '/ai/search-history/feedback',
  /** 搜尋建議 POST /ai/search-history/suggestions */
  SEARCH_HISTORY_SUGGESTIONS: '/ai/search-history/suggestions',
  /** 關聯圖譜 POST /ai/document/relation-graph */
  RELATION_GRAPH: '/ai/document/relation-graph',
  /** Embedding 統計 POST /ai/embedding/stats */
  EMBEDDING_STATS: '/ai/embedding/stats',
  /** Embedding 批次 POST /ai/embedding/batch */
  EMBEDDING_BATCH: '/ai/embedding/batch',
  /** 語意相似推薦 POST /ai/document/semantic-similar */
  SEMANTIC_SIMILAR: '/ai/document/semantic-similar',
  /** 實體提取 POST /ai/entity/extract */
  ENTITY_EXTRACT: '/ai/entity/extract',
  /** 實體批次提取 POST /ai/entity/batch */
  ENTITY_BATCH: '/ai/entity/batch',
  /** 實體提取統計 POST /ai/entity/stats */
  ENTITY_STATS: '/ai/entity/stats',
  // --- 知識圖譜 Phase 2: 正規化實體查詢 ---
  /** 正規化實體搜尋 POST /ai/graph/entity/search */
  GRAPH_ENTITY_SEARCH: '/ai/graph/entity/search',
  /** 實體鄰居查詢 POST /ai/graph/entity/neighbors */
  GRAPH_ENTITY_NEIGHBORS: '/ai/graph/entity/neighbors',
  /** 實體詳情 POST /ai/graph/entity/detail */
  GRAPH_ENTITY_DETAIL: '/ai/graph/entity/detail',
  /** 最短路徑 POST /ai/graph/entity/shortest-path */
  GRAPH_SHORTEST_PATH: '/ai/graph/entity/shortest-path',
  /** 實體時間軸 POST /ai/graph/entity/timeline */
  GRAPH_ENTITY_TIMELINE: '/ai/graph/entity/timeline',
  /** 高頻實體排名 POST /ai/graph/entity/top */
  GRAPH_ENTITY_TOP: '/ai/graph/entity/top',
  /** 實體中心圖譜 POST /ai/graph/entity/graph */
  GRAPH_ENTITY_GRAPH: '/ai/graph/entity/graph',
  /** 圖譜統計 POST /ai/graph/stats */
  GRAPH_STATS: '/ai/graph/stats',
  /** 時序聚合 POST /ai/graph/timeline/aggregate */
  GRAPH_TIMELINE_AGGREGATE: '/ai/graph/timeline/aggregate',
  /** 圖譜入圖管線 POST /ai/graph/ingest */
  GRAPH_INGEST: '/ai/graph/ingest',
  /** Code Wiki 代碼圖譜 POST /ai/graph/code-wiki */
  GRAPH_CODE_WIKI: '/ai/graph/code-wiki',
  /** Code Graph 入圖觸發 POST /ai/graph/admin/code-ingest */
  GRAPH_CODE_INGEST: '/ai/graph/admin/code-ingest',
  /** 循環依賴偵測 POST /ai/graph/admin/cycle-detection */
  GRAPH_CYCLE_DETECTION: '/ai/graph/admin/cycle-detection',
  /** 架構分析 POST /ai/graph/admin/architecture-analysis */
  GRAPH_ARCHITECTURE_ANALYSIS: '/ai/graph/admin/architecture-analysis',
  /** JSON 圖譜匯入 POST /ai/graph/admin/json-import */
  GRAPH_JSON_IMPORT: '/ai/graph/admin/json-import',
  /** 實體合併 POST /ai/graph/admin/merge-entities */
  GRAPH_MERGE_ENTITIES: '/ai/graph/admin/merge-entities',
  /** 模組架構概覽 POST /ai/graph/module-overview */
  GRAPH_MODULE_OVERVIEW: '/ai/graph/module-overview',
  /** 動態模組映射 GET /ai/graph/module-mappings */
  GRAPH_MODULE_MAPPINGS: '/ai/graph/module-mappings',
  /** 資料庫 Schema 反射 POST /ai/graph/db-schema */
  GRAPH_DB_SCHEMA: '/ai/graph/db-schema',
  /** 資料庫 ER 圖譜 POST /ai/graph/db-graph */
  GRAPH_DB_GRAPH: '/ai/graph/db-graph',
  /** 跨圖譜統一搜尋 POST /ai/graph/unified-search */
  GRAPH_UNIFIED_SEARCH: '/ai/graph/unified-search',
  // --- RAG 問答 ---
  /** RAG 問答 POST /ai/rag/query */
  RAG_QUERY: '/ai/rag/query',
  /** RAG 串流問答 POST /ai/rag/query/stream */
  RAG_QUERY_STREAM: '/ai/rag/query/stream',
  // --- Agentic 問答 ---
  /** Agentic 串流問答 POST /ai/agent/query/stream */
  AGENT_QUERY_STREAM: '/ai/agent/query/stream',
  /** 清除 Agent 對話記憶 POST /ai/agent/conversation/{session_id}/delete */
  AGENT_CONVERSATION_CLEAR: (sessionId: string) => `/ai/agent/conversation/${sessionId}/delete` as const,
  // --- 語音轉文字 ---
  /** 語音轉文字 POST /ai/voice/transcribe (multipart/form-data) */
  VOICE_TRANSCRIBE: '/ai/voice/transcribe',
  // --- Ollama 管理 ---
  /** Ollama 詳細狀態 POST /ai/ollama/status */
  OLLAMA_STATUS: '/ai/ollama/status',
  /** Ollama 模型檢查與拉取 POST /ai/ollama/ensure-models */
  OLLAMA_ENSURE_MODELS: '/ai/ollama/ensure-models',
  /** Ollama 模型預熱 POST /ai/ollama/warmup */
  OLLAMA_WARMUP: '/ai/ollama/warmup',
  // --- AI 回饋 + 分析 ---
  /** 提交 AI 回答回饋 POST /ai/feedback */
  FEEDBACK: '/ai/feedback',
  /** AI 回饋統計 POST /ai/feedback/stats */
  FEEDBACK_STATS: '/ai/feedback/stats',
  /** 系統使用分析總覽 POST /ai/analytics/overview */
  ANALYTICS_OVERVIEW: '/ai/analytics/overview',
  // --- AI 分析持久化 ---
  /** 取得公文 AI 分析結果 POST /ai/analysis/{document_id} */
  ANALYSIS_GET: (documentId: number) => `/ai/analysis/${documentId}` as const,
  /** 觸發公文 AI 分析 POST /ai/analysis/{document_id}/analyze */
  ANALYSIS_TRIGGER: (documentId: number) => `/ai/analysis/${documentId}/analyze` as const,
  /** 批次 AI 分析 POST /ai/analysis/batch */
  ANALYSIS_BATCH: '/ai/analysis/batch',
  /** AI 分析覆蓋率統計 POST /ai/analysis/stats */
  ANALYSIS_STATS: '/ai/analysis/stats',
  // --- Phase 3A 統計端點 ---
  /** 工具成功率統計 POST /ai/stats/tool-success-rates */
  STATS_TOOL_SUCCESS_RATES: '/ai/stats/tool-success-rates',
  /** Agent 追蹤記錄 POST /ai/stats/agent-traces */
  STATS_AGENT_TRACES: '/ai/stats/agent-traces',
  /** 學習模式統計 POST /ai/stats/patterns */
  STATS_PATTERNS: '/ai/stats/patterns',
  /** 持久化學習統計 POST /ai/stats/learnings */
  STATS_LEARNINGS: '/ai/stats/learnings',
  /** 每日趨勢統計 POST /ai/stats/daily-trend */
  STATS_DAILY_TREND: '/ai/stats/daily-trend',
  /** 主動觸發警報 POST /ai/proactive/alerts */
  PROACTIVE_ALERTS: '/ai/proactive/alerts',
  /** 工具註冊清單 POST /ai/stats/tool-registry */
  STATS_TOOL_REGISTRY: '/ai/stats/tool-registry',
  /** Skills 能力圖譜 POST /ai/graph/skills-map */
  GRAPH_SKILLS_MAP: '/ai/graph/skills-map',
  /** 技能演化樹 POST /ai/graph/skill-evolution */
  GRAPH_SKILL_EVOLUTION: '/ai/graph/skill-evolution',
} as const;

// ============================================================================
// 部署管理端點
// ============================================================================

/** 部署管理 API 端點 (POST-only 安全模式) */
export const DEPLOYMENT_ENDPOINTS = {
  /** 系統狀態 POST /deploy/status */
  STATUS: '/deploy/status',
  /** 部署歷史 POST /deploy/history */
  HISTORY: '/deploy/history',
  /** 觸發部署 POST /deploy/trigger */
  TRIGGER: '/deploy/trigger',
  /** 回滾部署 POST /deploy/rollback */
  ROLLBACK: '/deploy/rollback',
  /** 部署日誌 POST /deploy/logs/:runId */
  LOGS: (runId: number) => `/deploy/logs/${runId}`,
  /** 部署配置 POST /deploy/config */
  CONFIG: '/deploy/config',
} as const;

// ============================================================================
// LINE Bot 端點
// ============================================================================

/** LINE Bot API 端點 */
export const LINE_ENDPOINTS = {
  /** LINE Push 通知 POST /line/push */
  PUSH: '/line/push',
} as const;

// ============================================================================
// 知識庫瀏覽器端點
// ============================================================================

/** 知識庫瀏覽器 API 端點 */
export const KNOWLEDGE_BASE_ENDPOINTS = {
  TREE: '/knowledge-base/tree',
  FILE: '/knowledge-base/file',
  ADR_LIST: '/knowledge-base/adr/list',
  DIAGRAMS_LIST: '/knowledge-base/diagrams/list',
  SEARCH: '/knowledge-base/search',
} as const;

// ============================================================================
// 專案管理 (PM) 端點
// ============================================================================

/** PM 專案管理 API 端點 */
export const PM_ENDPOINTS = {
  /** 案件列表 POST /pm/cases/list */
  CASES_LIST: '/pm/cases/list',
  /** 建立案件 POST /pm/cases/create */
  CASES_CREATE: '/pm/cases/create',
  /** 案件詳情 POST /pm/cases/detail */
  CASES_DETAIL: '/pm/cases/detail',
  /** 更新案件 POST /pm/cases/update-by-id */
  CASES_UPDATE: '/pm/cases/update-by-id',
  /** 刪除案件 POST /pm/cases/delete */
  CASES_DELETE: '/pm/cases/delete',
  /** 案件統計摘要 POST /pm/cases/summary */
  CASES_SUMMARY: '/pm/cases/summary',
  /** 里程碑列表 POST /pm/milestones/list */
  MILESTONES_LIST: '/pm/milestones/list',
  /** 建立里程碑 POST /pm/milestones/create */
  MILESTONES_CREATE: '/pm/milestones/create',
  /** 更新里程碑 POST /pm/milestones/update */
  MILESTONES_UPDATE: '/pm/milestones/update',
  /** 刪除里程碑 POST /pm/milestones/delete */
  MILESTONES_DELETE: '/pm/milestones/delete',
  /** 人員列表 POST /pm/staff/list */
  STAFF_LIST: '/pm/staff/list',
  /** 建立人員 POST /pm/staff/create */
  STAFF_CREATE: '/pm/staff/create',
  /** 更新人員 POST /pm/staff/update */
  STAFF_UPDATE: '/pm/staff/update',
  /** 刪除人員 POST /pm/staff/delete */
  STAFF_DELETE: '/pm/staff/delete',
  /** 產生案號 POST /pm/cases/generate-code */
  GENERATE_CODE: '/pm/cases/generate-code',
  /** 重新計算進度 POST /pm/cases/recalculate-progress */
  RECALCULATE_PROGRESS: '/pm/cases/recalculate-progress',
  /** 跨模組案號查詢 POST /pm/cases/cross-lookup */
  CROSS_LOOKUP: '/pm/cases/cross-lookup',
  /** 甘特圖 POST /pm/cases/gantt */
  GANTT: '/pm/cases/gantt',
  /** 案號關聯公文 POST /pm/cases/linked-documents */
  LINKED_DOCUMENTS: '/pm/cases/linked-documents',
  /** 匯出 CSV POST /pm/cases/export */
  EXPORT: '/pm/cases/export',
  /** 多年度趨勢 POST /pm/cases/yearly-trend */
  YEARLY_TREND: '/pm/cases/yearly-trend',
} as const;

// ============================================================================
// 財務管理 (ERP) 端點
// ============================================================================

/** ERP 財務管理 API 端點 */
export const ERP_ENDPOINTS = {
  /** 報價列表 POST /erp/quotations/list */
  QUOTATIONS_LIST: '/erp/quotations/list',
  /** 建立報價 POST /erp/quotations/create */
  QUOTATIONS_CREATE: '/erp/quotations/create',
  /** 報價詳情 POST /erp/quotations/detail */
  QUOTATIONS_DETAIL: '/erp/quotations/detail',
  /** 更新報價 POST /erp/quotations/update */
  QUOTATIONS_UPDATE: '/erp/quotations/update',
  /** 刪除報價 POST /erp/quotations/delete */
  QUOTATIONS_DELETE: '/erp/quotations/delete',
  /** 損益摘要 POST /erp/quotations/profit-summary */
  PROFIT_SUMMARY: '/erp/quotations/profit-summary',
  /** 發票列表 POST /erp/invoices/list */
  INVOICES_LIST: '/erp/invoices/list',
  /** 建立發票 POST /erp/invoices/create */
  INVOICES_CREATE: '/erp/invoices/create',
  /** 更新發票 POST /erp/invoices/update */
  INVOICES_UPDATE: '/erp/invoices/update',
  /** 刪除發票 POST /erp/invoices/delete */
  INVOICES_DELETE: '/erp/invoices/delete',
  /** 請款列表 POST /erp/billings/list */
  BILLINGS_LIST: '/erp/billings/list',
  /** 建立請款 POST /erp/billings/create */
  BILLINGS_CREATE: '/erp/billings/create',
  /** 更新請款 POST /erp/billings/update */
  BILLINGS_UPDATE: '/erp/billings/update',
  /** 刪除請款 POST /erp/billings/delete */
  BILLINGS_DELETE: '/erp/billings/delete',
  /** 廠商應付列表 POST /erp/vendor-payables/list */
  VENDOR_PAYABLES_LIST: '/erp/vendor-payables/list',
  /** 建立廠商應付 POST /erp/vendor-payables/create */
  VENDOR_PAYABLES_CREATE: '/erp/vendor-payables/create',
  /** 更新廠商應付 POST /erp/vendor-payables/update */
  VENDOR_PAYABLES_UPDATE: '/erp/vendor-payables/update',
  /** 刪除廠商應付 POST /erp/vendor-payables/delete */
  VENDOR_PAYABLES_DELETE: '/erp/vendor-payables/delete',
  /** 產生案號 POST /erp/quotations/generate-code */
  GENERATE_CODE: '/erp/quotations/generate-code',
  /** 損益趨勢 POST /erp/quotations/profit-trend */
  PROFIT_TREND: '/erp/quotations/profit-trend',
  /** 匯出 CSV POST /erp/quotations/export */
  EXPORT: '/erp/quotations/export',

  // --- 費用報銷 (expenses) ---
  /** 費用發票列表 POST /erp/expenses/list */
  EXPENSES_LIST: '/erp/expenses/list',
  /** 建立報銷發票 POST /erp/expenses/create */
  EXPENSES_CREATE: '/erp/expenses/create',
  /** 發票詳情 POST /erp/expenses/detail */
  EXPENSES_DETAIL: '/erp/expenses/detail',
  /** 更新報銷發票 POST /erp/expenses/update */
  EXPENSES_UPDATE: '/erp/expenses/update',
  /** 審核通過 POST /erp/expenses/approve */
  EXPENSES_APPROVE: '/erp/expenses/approve',
  /** 駁回報銷 POST /erp/expenses/reject */
  EXPENSES_REJECT: '/erp/expenses/reject',
  /** QR Code 掃描建立 POST /erp/expenses/qr-scan */
  EXPENSES_QR_SCAN: '/erp/expenses/qr-scan',
  /** 上傳收據影像 POST /erp/expenses/upload-receipt */
  EXPENSES_UPLOAD_RECEIPT: '/erp/expenses/upload-receipt',
  /** 取得收據影像 POST /erp/expenses/receipt-image */
  EXPENSES_RECEIPT_IMAGE: '/erp/expenses/receipt-image',
  /** OCR 辨識發票影像 POST /erp/expenses/ocr-parse */
  EXPENSES_OCR_PARSE: '/erp/expenses/ocr-parse',

  // --- 統一帳本 (ledger) ---
  /** 帳本列表 POST /erp/ledger/list */
  LEDGER_LIST: '/erp/ledger/list',
  /** 手動記帳 POST /erp/ledger/create */
  LEDGER_CREATE: '/erp/ledger/create',
  /** 帳本詳情 POST /erp/ledger/detail */
  LEDGER_DETAIL: '/erp/ledger/detail',
  /** 專案收支餘額 POST /erp/ledger/balance */
  LEDGER_BALANCE: '/erp/ledger/balance',
  /** 分類拆解 POST /erp/ledger/category-breakdown */
  LEDGER_CATEGORY_BREAKDOWN: '/erp/ledger/category-breakdown',
  /** 刪除帳本 POST /erp/ledger/delete */
  LEDGER_DELETE: '/erp/ledger/delete',

  // --- 財務彙總 (financial-summary) ---
  /** 單一專案財務彙總 POST /erp/financial-summary/project */
  FINANCIAL_SUMMARY_PROJECT: '/erp/financial-summary/project',
  /** 所有專案一覽 POST /erp/financial-summary/projects */
  FINANCIAL_SUMMARY_PROJECTS: '/erp/financial-summary/projects',
  /** 全公司財務總覽 POST /erp/financial-summary/company */
  FINANCIAL_SUMMARY_COMPANY: '/erp/financial-summary/company',
  /** 月度收支趨勢 POST /erp/financial-summary/monthly-trend */
  FINANCIAL_SUMMARY_MONTHLY_TREND: '/erp/financial-summary/monthly-trend',
  /** 預算使用率排行 POST /erp/financial-summary/budget-ranking */
  FINANCIAL_SUMMARY_BUDGET_RANKING: '/erp/financial-summary/budget-ranking',
  /** 匯出費用報銷 Excel POST /erp/financial-summary/export-expenses */
  EXPORT_EXPENSES: '/erp/financial-summary/export-expenses',
  /** 匯出帳本 Excel POST /erp/financial-summary/export-ledger */
  EXPORT_LEDGER: '/erp/financial-summary/export-ledger',

  // --- 電子發票同步 (einvoice-sync) ---
  /** 手動觸發同步 POST /erp/einvoice-sync/sync */
  EINVOICE_SYNC: '/erp/einvoice-sync/sync',
  /** 待核銷清單 POST /erp/einvoice-sync/pending-list */
  EINVOICE_PENDING_LIST: '/erp/einvoice-sync/pending-list',
  /** 上傳收據照片 POST /erp/einvoice-sync/upload-receipt */
  EINVOICE_UPLOAD_RECEIPT: '/erp/einvoice-sync/upload-receipt',
  /** 同步歷史記錄 POST /erp/einvoice-sync/sync-logs */
  EINVOICE_SYNC_LOGS: '/erp/einvoice-sync/sync-logs',
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

  // AI 服務
  AI: AI_ENDPOINTS,

  // 部署管理
  DEPLOYMENT: DEPLOYMENT_ENDPOINTS,

  // 桃園派工管理
  TAOYUAN_DISPATCH: TAOYUAN_DISPATCH_ENDPOINTS,

  // 知識庫瀏覽器
  KNOWLEDGE_BASE: KNOWLEDGE_BASE_ENDPOINTS,

  // LINE Bot
  LINE: LINE_ENDPOINTS,

  // 專案管理 (PM)
  PM: PM_ENDPOINTS,

  // 財務管理 (ERP)
  ERP: ERP_ENDPOINTS,
} as const;

// 預設匯出
export default API_ENDPOINTS;
