/**
 * API 錯誤解析工具
 *
 * 從 useApiErrorHandler 提取的純函數，
 * 可供 React Query 全域 onError、Hook、元件共用。
 *
 * @version 1.0.0
 * @date 2026-01-28
 */

export interface ParsedApiError {
  status?: number;
  message: string;
  detail?: string;
  timestamp: string;
  path?: string;
}

/** HTTP 狀態碼對應的使用者友善訊息 */
const STATUS_MESSAGES: Record<number, string> = {
  400: '請求參數錯誤',
  401: '未授權，請重新登入',
  403: '權限不足，無法執行此操作',
  404: '請求的資源不存在',
  408: '請求逾時，請重試',
  409: '資料衝突，請檢查後重試',
  422: '資料驗證失敗',
  429: '請求過於頻繁，請稍後再試',
  500: '伺服器內部錯誤',
  502: '服務暫時不可用',
  503: '服務維護中',
  504: '伺服器回應逾時',
};

/**
 * 根據 HTTP 狀態碼取得使用者友善訊息
 */
export function getStatusMessage(status: number, fallback: string): string {
  return STATUS_MESSAGES[status] || fallback;
}

/**
 * 將任意錯誤物件解析為結構化的 ParsedApiError
 *
 * 支援：
 * - 字串錯誤
 * - Axios 回應錯誤 (error.response)
 * - 網路錯誤 (error.request)
 * - Error 物件
 * - ApiException (client.ts)
 */
/** Type guard: check if error has an Axios-like response property */
function isAxiosLikeError(error: unknown): error is {
  response: { status: number; data: unknown; config?: { url?: string } };
  message?: string;
} {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as Record<string, unknown>).response === 'object' &&
    (error as Record<string, unknown>).response !== null
  );
}

/** Type guard: check if error has a request property (network error) */
function isNetworkError(error: unknown): error is { request: unknown } {
  return (
    typeof error === 'object' &&
    error !== null &&
    'request' in error &&
    !('response' in error)
  );
}

export function parseApiError(error: unknown): ParsedApiError {
  const timestamp = new Date().toISOString();

  if (typeof error === 'string') {
    return { message: error, timestamp };
  }

  if (error == null) {
    return { message: '發生未知錯誤', timestamp };
  }

  // Axios response error
  if (isAxiosLikeError(error)) {
    const status: number = error.response.status;
    const data = error.response.data;

    let messageText = '發生未知錯誤';
    let detail = '';

    if (typeof data === 'string') {
      messageText = data;
    } else if (data && typeof data === 'object') {
      const d = data as Record<string, string>;
      messageText = d.message || d.detail || d.error || messageText;
      detail = d.detail || '';
    }

    return {
      status,
      message: getStatusMessage(status, messageText),
      detail,
      timestamp,
      path: error.response.config?.url || '',
    };
  }

  // Network error (request sent but no response)
  if (isNetworkError(error)) {
    return {
      message: '網路連線失敗，請檢查網路狀態',
      detail: 'Network Error',
      timestamp,
    };
  }

  // Error instance or plain object
  if (error instanceof Error) {
    return {
      message: error.message || '發生未預期的錯誤',
      detail: error.stack || '',
      timestamp,
    };
  }

  return {
    message: '發生未預期的錯誤',
    timestamp,
  };
}

/**
 * 從錯誤物件快速取得使用者友善的錯誤訊息字串
 *
 * 用於取代散落各處的 `error?.response?.data?.detail || error?.message || '操作失敗'` 模式
 */
export function getErrorMessage(error: unknown, fallback = '操作失敗'): string {
  const parsed = parseApiError(error);
  return parsed.message || fallback;
}
