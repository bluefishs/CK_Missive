/**
 * API 錯誤處理模組
 *
 * 統一封裝 API 錯誤，提供一致的錯誤處理介面。
 * 從 client.ts 拆分以提升可維護性。
 *
 * @version 1.0.0
 * @date 2026-02-11
 */

import { AxiosError } from 'axios';
import { ErrorCode, ErrorResponse } from './types';

/**
 * API 錯誤類
 *
 * 統一封裝 API 錯誤，提供一致的錯誤處理介面
 */
export class ApiException extends Error {
  public readonly code: ErrorCode | string;
  public readonly statusCode: number;
  public readonly details: { field?: string; message: string; value?: unknown }[];
  public readonly timestamp: Date;

  constructor(
    code: ErrorCode | string,
    message: string,
    statusCode = 500,
    details?: { field?: string; message: string; value?: unknown }[]
  ) {
    super(message);
    this.name = 'ApiException';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details || [];
    this.timestamp = new Date();
  }

  /** 從錯誤回應建立 ApiException */
  static fromResponse(response: ErrorResponse, statusCode = 500): ApiException {
    return new ApiException(
      response.error.code,
      response.error.message,
      statusCode,
      response.error.details
    );
  }

  /** 從 Axios 錯誤建立 ApiException */
  static fromAxiosError(error: AxiosError<ErrorResponse>): ApiException {
    // 網路錯誤
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        return new ApiException(
          ErrorCode.TIMEOUT,
          '請求超時，請檢查網路連線後重試',
          0
        );
      }
      return new ApiException(
        ErrorCode.NETWORK_ERROR,
        '網路連線失敗，請檢查網路狀態',
        0
      );
    }

    const { status, data } = error.response;

    // 後端回傳統一格式的錯誤
    if (data && typeof data === 'object' && 'error' in data) {
      return ApiException.fromResponse(data as ErrorResponse, status);
    }

    // FastAPI HTTPException 格式 ({"detail": "..."})
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: string }).detail;
      return new ApiException(
        status === 400 ? ErrorCode.BAD_REQUEST : ErrorCode.INTERNAL_ERROR,
        detail,
        status
      );
    }

    // 根據 HTTP 狀態碼建立錯誤
    const statusMessages: Record<number, [ErrorCode, string]> = {
      400: [ErrorCode.BAD_REQUEST, '請求參數錯誤'],
      401: [ErrorCode.UNAUTHORIZED, '請先登入'],
      403: [ErrorCode.FORBIDDEN, '您沒有權限執行此操作'],
      404: [ErrorCode.NOT_FOUND, '找不到請求的資源'],
      409: [ErrorCode.CONFLICT, '資源衝突'],
      422: [ErrorCode.VALIDATION_ERROR, '輸入資料驗證失敗'],
      429: [ErrorCode.TOO_MANY_REQUESTS, '請求過於頻繁，請稍後再試'],
      500: [ErrorCode.INTERNAL_ERROR, '伺服器內部錯誤'],
      502: [ErrorCode.SERVICE_UNAVAILABLE, '服務暫時無法使用'],
      503: [ErrorCode.SERVICE_UNAVAILABLE, '服務暫時無法使用'],
    };

    const [code, message] = statusMessages[status] || [
      ErrorCode.INTERNAL_ERROR,
      '發生未知錯誤',
    ];

    return new ApiException(code, message, status);
  }

  /** 取得使用者友善的錯誤訊息 */
  getUserMessage(): string {
    return this.message;
  }

  /** 取得欄位錯誤（用於表單驗證） */
  getFieldErrors(): Record<string, string> {
    if (!this.details) return {};

    return this.details.reduce((acc, detail) => {
      if (detail.field) {
        acc[detail.field] = detail.message;
      }
      return acc;
    }, {} as Record<string, string>);
  }

  /** 是否為業務邏輯錯誤（元件應自行處理） */
  isBusinessError(): boolean {
    return [400, 409, 422].includes(this.statusCode);
  }

  /** 是否為全域錯誤（由 GlobalApiErrorNotifier 自動處理） */
  isGlobalError(): boolean {
    return [403, 500, 502, 503].includes(this.statusCode)
      || this.statusCode === 0;  // 網路錯誤
  }
}

// ============================================================================
// 全域 API 錯誤事件
// ============================================================================

type ApiErrorListener = (error: ApiException) => void;

/**
 * 全域 API 錯誤事件匯流排
 *
 * 攔截器發出 → GlobalApiErrorNotifier 接收並顯示。
 * 業務錯誤 (400/409/422) 不會被發出，由元件自行處理。
 */
class ApiErrorBus {
  private listeners: ApiErrorListener[] = [];

  /** 訂閱全域 API 錯誤（在 GlobalApiErrorNotifier 中呼叫） */
  subscribe(listener: ApiErrorListener): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  /** 發出全域 API 錯誤（在攔截器中呼叫） */
  emit(error: ApiException): void {
    this.listeners.forEach(l => l(error));
  }
}

export const apiErrorBus = new ApiErrorBus();
