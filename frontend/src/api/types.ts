/**
 * API 統一型別定義
 *
 * 與後端 common.py Schema 對應，確保前後端型別一致
 */

// ============================================================================
// 錯誤碼定義（與後端 ErrorCode 對應）
// ============================================================================

export enum ErrorCode {
  // 驗證錯誤 (4xx)
  VALIDATION_ERROR = 'ERR_VALIDATION',
  NOT_FOUND = 'ERR_NOT_FOUND',
  UNAUTHORIZED = 'ERR_UNAUTHORIZED',
  FORBIDDEN = 'ERR_FORBIDDEN',
  CONFLICT = 'ERR_CONFLICT',
  BAD_REQUEST = 'ERR_BAD_REQUEST',
  TOO_MANY_REQUESTS = 'ERR_TOO_MANY_REQUESTS',

  // 伺服器錯誤 (5xx)
  INTERNAL_ERROR = 'ERR_INTERNAL',
  DATABASE_ERROR = 'ERR_DATABASE',
  SERVICE_UNAVAILABLE = 'ERR_SERVICE_UNAVAILABLE',

  // 業務邏輯錯誤
  DUPLICATE_ENTRY = 'ERR_DUPLICATE',
  INVALID_OPERATION = 'ERR_INVALID_OPERATION',
  RESOURCE_IN_USE = 'ERR_RESOURCE_IN_USE',

  // 前端特有錯誤
  NETWORK_ERROR = 'ERR_NETWORK',
  TIMEOUT = 'ERR_TIMEOUT',
}

// ============================================================================
// 錯誤回應格式
// ============================================================================

/** 錯誤詳細資訊 */
export interface ErrorDetail {
  field?: string;
  message: string;
  value?: unknown;
}

/** 錯誤物件 */
export interface ApiError {
  code: ErrorCode | string;
  message: string;
  details?: ErrorDetail[];
}

/** 統一錯誤回應格式 */
export interface ErrorResponse {
  success: false;
  error: ApiError;
  timestamp: string;
}

// ============================================================================
// 成功回應格式
// ============================================================================

/** 統一成功回應格式（單一資料） */
export interface SuccessResponse<T = unknown> {
  success: true;
  data?: T;
  message?: string;
}

// ============================================================================
// 分頁相關
// ============================================================================

/** 分頁參數（請求用） */
export interface PaginationParams {
  page?: number;
  limit?: number;
}

/** 分頁元資料（回應用） */
export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

/** 統一分頁回應格式 */
export interface PaginatedResponse<T = unknown> {
  success: true;
  items: T[];
  pagination: PaginationMeta;
}

// ============================================================================
// 排序相關
// ============================================================================

export type SortOrder = 'asc' | 'desc';

export interface SortParams {
  sort_by?: string;
  sort_order?: SortOrder;
}

// ============================================================================
// 查詢參數基類
// ============================================================================

export interface BaseQueryParams extends PaginationParams, SortParams {
  search?: string;
}

// ============================================================================
// 通用回應
// ============================================================================

/** 刪除操作回應 */
export interface DeleteResponse {
  success: boolean;
  message: string;
  deleted_id: number;
}

/** 批次操作回應 */
export interface BatchOperationResponse {
  success: boolean;
  message: string;
  success_count: number;
  failed_count: number;
  failed_ids: number[];
  errors: string[];
}

// ============================================================================
// 下拉選項格式
// ============================================================================

export interface SelectOption<T = string | number> {
  value: T;
  label: string;
  disabled?: boolean;
}

// ============================================================================
// 統一 API 回應類型（支援舊格式相容）
// ============================================================================

/**
 * API 回應聯合型別
 *
 * 支援新舊格式，用於漸進式遷移
 */
export type ApiResponse<T> =
  | SuccessResponse<T>
  | ErrorResponse
  | PaginatedResponse<T>
  // 舊格式相容（逐步淘汰）
  | LegacyListResponse<T>;

/** 舊版列表回應格式（相容用） */
export interface LegacyListResponse<T> {
  items?: T[];
  documents?: T[];
  projects?: T[];
  vendors?: T[];
  users?: T[];
  total: number;
  page?: number;
  limit?: number;
  per_page?: number;
  pages?: number;
  total_pages?: number;
  skip?: number;
}

// ============================================================================
// 型別守衛函數
// ============================================================================

/** 判斷是否為錯誤回應 */
export function isErrorResponse(response: unknown): response is ErrorResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    (response as ErrorResponse).success === false &&
    'error' in response
  );
}

/** 判斷是否為成功回應 */
export function isSuccessResponse<T>(
  response: unknown
): response is SuccessResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    (response as SuccessResponse<T>).success === true &&
    'data' in response
  );
}

/** 判斷是否為分頁回應 */
export function isPaginatedResponse<T>(
  response: unknown
): response is PaginatedResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    (response as PaginatedResponse<T>).success === true &&
    'items' in response &&
    'pagination' in response
  );
}

/** 判斷是否為舊版列表回應 */
export function isLegacyListResponse<T>(
  response: unknown
): response is LegacyListResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'total' in response &&
    !('pagination' in response) &&
    !('success' in response)
  );
}

// ============================================================================
// 回應轉換工具
// ============================================================================

/**
 * 將舊格式轉換為新的分頁回應格式
 */
export function normalizePaginatedResponse<T>(
  response: LegacyListResponse<T> | PaginatedResponse<T>,
  defaultPage = 1,
  defaultLimit = 20
): PaginatedResponse<T> {
  // 已經是新格式
  if (isPaginatedResponse(response)) {
    return response;
  }

  // 舊格式轉換
  const items =
    response.items ||
    response.documents ||
    response.projects ||
    response.vendors ||
    response.users ||
    [];

  const total = response.total || 0;
  const page = response.page || defaultPage;
  const limit = response.limit || response.per_page || defaultLimit;
  const totalPages =
    response.total_pages || response.pages || Math.ceil(total / limit) || 0;

  return {
    success: true,
    items: items as T[],
    pagination: {
      total,
      page,
      limit,
      total_pages: totalPages,
      has_next: page < totalPages,
      has_prev: page > 1,
    },
  };
}
