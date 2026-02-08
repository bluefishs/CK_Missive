/**
 * 認證相關 API 服務
 *
 * 提供 Email 驗證等認證輔助功能的 API 呼叫
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import { apiClient } from './client';
import { AUTH_ENDPOINTS } from './endpoints';

/**
 * 發送 Email 驗證信
 *
 * 需要已登入狀態。如果使用者 email 已驗證，後端會回傳提示訊息。
 *
 * @returns { message: string }
 */
export const sendVerificationEmail = (): Promise<{ message: string }> =>
  apiClient.post(AUTH_ENDPOINTS.SEND_VERIFICATION);

/**
 * 驗證 Email
 *
 * 使用從驗證信中取得的 token 驗證 email。
 * 不需要 CSRF token（透過 email link 存取）。
 *
 * @param token - 驗證 token
 * @returns { message: string; verified?: boolean; already_verified?: boolean }
 */
export const verifyEmail = (
  token: string
): Promise<{ message: string; verified?: boolean; already_verified?: boolean }> =>
  apiClient.post(AUTH_ENDPOINTS.VERIFY_EMAIL, { token });
