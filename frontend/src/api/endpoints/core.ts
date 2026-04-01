/**
 * 核心功能模組端點
 * 包含: 儀表板、公文、行事曆、通知、檔案、提醒、CSV匯入、公開、系統
 */

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
  /** 批次更新狀態 POST /calendar/events/batch-update-status */
  EVENTS_BATCH_UPDATE_STATUS: '/calendar/events/batch-update-status',
  /** 批次刪除 POST /calendar/events/batch-delete */
  EVENTS_BATCH_DELETE: '/calendar/events/batch-delete',
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
  /** 系統覆盤儀表板 POST /system/review-dashboard */
  REVIEW_DASHBOARD: '/system/review-dashboard',
} as const;
