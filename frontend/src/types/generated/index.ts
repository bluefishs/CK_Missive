/**
 * OpenAPI 自動生成型別包裝層
 *
 * 此檔案提供從 OpenAPI 規範自動生成的型別的便捷存取。
 * 當後端 Schema 變更時，執行 `npm run api:generate` 重新生成。
 *
 * @example
 * import { ApiDocumentResponse, ApiUserResponse } from '../types/generated';
 *
 * @version 1.0.0
 * @date 2026-01-18
 */

import type { components } from './api';

// =============================================================================
// 從 OpenAPI 自動生成的型別（帶 Api 前綴避免命名衝突）
// =============================================================================

// 公文相關
export type ApiDocumentResponse = components['schemas']['DocumentResponse'];
export type ApiDocumentCreateRequest = components['schemas']['DocumentCreateRequest'];
export type ApiDocumentUpdateRequest = components['schemas']['DocumentUpdateRequest'];
export type ApiDocumentListResponse = components['schemas']['DocumentListResponse'];

// 使用者相關
export type ApiUserResponse = components['schemas']['UserResponse'];

// 機關相關
export type ApiAgency = components['schemas']['Agency'];
export type ApiAgencyWithStats = components['schemas']['AgencyWithStats'];
export type ApiAgenciesResponse = components['schemas']['AgenciesResponse'];

// 通知相關
export type ApiNotificationItem = components['schemas']['NotificationItem'];
export type ApiNotificationQuery = components['schemas']['NotificationQuery'];
export type ApiNotificationListResponse = components['schemas']['NotificationListResponse'];
export type ApiMarkReadRequest = components['schemas']['MarkReadRequest'];
export type ApiMarkReadResponse = components['schemas']['MarkReadResponse'];
export type ApiUnreadCountResponse = components['schemas']['UnreadCountResponse'];

// 廠商相關
export type ApiVendor = components['schemas']['Vendor'];
export type ApiVendorCreate = components['schemas']['VendorCreate'];
export type ApiVendorUpdate = components['schemas']['VendorUpdate'];
export type ApiVendorListResponse = components['schemas']['VendorListResponse'];

// =============================================================================
// 型別驗證輔助函數（可選，用於執行時驗證）
// =============================================================================

/**
 * 驗證物件是否符合 ApiDocumentResponse 結構
 * 用於 API 回應的執行時檢查
 */
export function isApiDocumentResponse(obj: unknown): obj is ApiDocumentResponse {
  if (!obj || typeof obj !== 'object') return false;
  const doc = obj as Record<string, unknown>;
  return (
    typeof doc.id === 'number' &&
    typeof doc.doc_number === 'string' &&
    typeof doc.subject === 'string'
  );
}

/**
 * 驗證物件是否符合 ApiUserResponse 結構
 */
export function isApiUserResponse(obj: unknown): obj is ApiUserResponse {
  if (!obj || typeof obj !== 'object') return false;
  const user = obj as Record<string, unknown>;
  return (
    typeof user.id === 'number' &&
    typeof user.email === 'string'
  );
}

// =============================================================================
// 完整 components 型別匯出（進階使用）
// =============================================================================

export type { components };
