/**
 * 系統管理端點 + 標案檢索
 */

/** 標案檢索 API 端點 */
export const TENDER_ENDPOINTS = {
  /** 搜尋標案 POST /tender/search */
  SEARCH: '/tender/search',
  /** 標案詳情 POST /tender/detail */
  DETAIL: '/tender/detail',
  /** 廠商搜尋 POST /tender/search-company */
  SEARCH_COMPANY: '/tender/search-company',
  /** 智能推薦 POST /tender/recommend */
  RECOMMEND: '/tender/recommend',
  /** 標案知識圖譜 POST /tender/graph */
  GRAPH: '/tender/graph',
  /** 從標案建案 POST /tender/create-case */
  CREATE_CASE: '/tender/create-case',
  /** 訂閱列表 POST /tender/subscriptions/list */
  SUBSCRIPTIONS_LIST: '/tender/subscriptions/list',
  /** 建立訂閱 POST /tender/subscriptions/create */
  SUBSCRIPTIONS_CREATE: '/tender/subscriptions/create',
  /** 刪除訂閱 POST /tender/subscriptions/delete */
  SUBSCRIPTIONS_DELETE: '/tender/subscriptions/delete',
  /** 書籤列表 POST /tender/bookmarks/list */
  BOOKMARKS_LIST: '/tender/bookmarks/list',
  /** 收藏標案 POST /tender/bookmarks/create */
  BOOKMARKS_CREATE: '/tender/bookmarks/create',
  /** 更新書籤 POST /tender/bookmarks/update */
  BOOKMARKS_UPDATE: '/tender/bookmarks/update',
  /** 刪除書籤 POST /tender/bookmarks/delete */
  BOOKMARKS_DELETE: '/tender/bookmarks/delete',
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

/** LINE Bot API 端點 */
export const LINE_ENDPOINTS = {
  /** LINE Push 通知 POST /line/push */
  PUSH: '/line/push',
} as const;

/** Discord Bot API 端點 */
export const DISCORD_ENDPOINTS = {
  /** Discord Push 通知 POST /discord/push */
  PUSH: '/discord/push',
} as const;

/** 安全網站管理 API 端點 */
export const SECURE_SITE_MANAGEMENT_ENDPOINTS = {
  /** CSRF 令牌 POST /secure-site-management/csrf-token */
  CSRF_TOKEN: '/secure-site-management/csrf-token',
  /** 導覽項目操作 POST /secure-site-management/navigation/action */
  NAVIGATION_ACTION: '/secure-site-management/navigation/action',
  /** 有效路徑 POST /secure-site-management/navigation/valid-paths */
  NAVIGATION_VALID_PATHS: '/secure-site-management/navigation/valid-paths',
  /** 配置操作 POST /secure-site-management/config/action */
  CONFIG_ACTION: '/secure-site-management/config/action',
} as const;
