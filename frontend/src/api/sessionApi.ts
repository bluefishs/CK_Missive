/**
 * Session 管理 API 服務
 *
 * 提供使用者 Session 查詢與撤銷功能。
 * 型別從 types/api.ts 匯入 (SSOT)。
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';

// 型別從 types/admin-system.ts 匯入 (SSOT)
import type { SessionInfo, SessionListResponse, RevokeSessionResponse } from '../types/api';

// 向後相容 re-export
export type { SessionInfo, SessionListResponse, RevokeSessionResponse };

/**
 * 列出使用者所有活躍 Session
 */
export const listSessions = (): Promise<SessionListResponse> =>
  apiClient.post<SessionListResponse>(API_ENDPOINTS.AUTH.SESSIONS);

/**
 * 撤銷指定 Session
 */
export const revokeSession = (sessionId: number): Promise<RevokeSessionResponse> =>
  apiClient.post<RevokeSessionResponse>(API_ENDPOINTS.AUTH.SESSION_REVOKE, {
    session_id: sessionId,
  });

/**
 * 撤銷所有其他 Session
 */
export const revokeAllSessions = (): Promise<RevokeSessionResponse> =>
  apiClient.post<RevokeSessionResponse>(API_ENDPOINTS.AUTH.SESSION_REVOKE_ALL);
