/**
 * 使用者與權限管理端點
 * 包含: 使用者、認證、管理員、證照、專案人員/廠商/機關承辦
 */

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
  /** 管理員登入紀錄 POST /auth/login-history/admin */
  LOGIN_HISTORY_ADMIN: '/auth/login-history/admin',
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
  /** LINE Login OAuth Callback POST /auth/line/callback */
  LINE_CALLBACK: '/auth/line/callback',
  /** 綁定 LINE 帳號 POST /auth/line/bind */
  LINE_BIND: '/auth/line/bind',
  /** 解除 LINE 綁定 POST /auth/line/unbind */
  LINE_UNBIND: '/auth/line/unbind',
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
  /** 角色權限詳情 POST /admin/user-management/roles/:role/permissions/detail */
  ROLE_PERMISSIONS_DETAIL: (role: string) => `/admin/user-management/roles/${role}/permissions/detail`,
  /** 更新角色權限 POST /admin/user-management/roles/:role/permissions/update */
  ROLE_PERMISSIONS_UPDATE: (role: string) => `/admin/user-management/roles/${role}/permissions/update`,
  /** 列出所有角色 POST /admin/user-management/roles/list */
  ROLES_LIST: '/admin/user-management/roles/list',
  /** 管理員解鎖帳號 POST /admin/user-management/users/:id/unlock */
  USERS_UNLOCK: (id: number) => `/admin/user-management/users/${id}/unlock`,
  /** 管理員綁定 LINE POST /admin/user-management/users/:id/line-bind */
  LINE_BIND: (id: number) => `/admin/user-management/users/${id}/line-bind`,
  /** 管理員解除 LINE POST /admin/user-management/users/:id/line-unbind */
  LINE_UNBIND: (id: number) => `/admin/user-management/users/${id}/line-unbind`,
} as const;

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
  /** 依建案案號取得承辦同仁 POST /project-staff/case/:caseCode/list */
  CASE_LIST: (caseCode: string) => `/project-staff/case/${caseCode}/list` as const,
  /** 更新關聯 POST /project-staff/project/:projectId/user/:userId/update */
  UPDATE: (projectId: number, userId: number) => `/project-staff/project/${projectId}/user/${userId}/update` as const,
  /** 刪除關聯 POST /project-staff/project/:projectId/user/:userId/delete */
  DELETE: (projectId: number, userId: number) => `/project-staff/project/${projectId}/user/${userId}/delete` as const,
  /** 依 ID 刪除關聯 POST /project-staff/assignment/:assignmentId/delete */
  ASSIGNMENT_DELETE: (assignmentId: number) => `/project-staff/assignment/${assignmentId}/delete` as const,
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
