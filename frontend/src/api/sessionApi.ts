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

/** Session 資訊 */
export interface SessionInfo {
  id: number;
  ip_address: string | null;
  user_agent: string | null;
  device_info: string | null;
  created_at: string;
  last_activity: string | null;
  is_active: boolean;
  is_current: boolean;
}

/** Session 列表回應 */
export interface SessionListResponse {
  sessions: SessionInfo[];
  total: number;
}

/** 撤銷 Session 回應 */
export interface RevokeSessionResponse {
  message: string;
  session_id?: number;
  revoked_count?: number;
}

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
