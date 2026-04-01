/**
 * 專案、機關、廠商端點
 */

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
  /** 廠商財務彙總 POST /vendors/:id/financial-summary */
  FINANCIAL_SUMMARY: (id: number) => `/vendors/${id}/financial-summary`,
} as const;
