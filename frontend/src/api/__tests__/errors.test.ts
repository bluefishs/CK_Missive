/**
 * API 錯誤處理模組測試
 * API Errors Module Tests
 *
 * 驗證 ApiException 類別與 ApiErrorBus 事件匯流排
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/errors.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiException, apiErrorBus } from '../errors';
import { ErrorCode } from '../types';

// ============================================================================
// ApiException 基本建構
// ============================================================================

describe('ApiException 基本建構', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該是 Error 的實例', () => {
    const error = new ApiException('ERR_TEST', '測試錯誤');
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiException);
  });

  it('應該正確設定 name 為 ApiException', () => {
    const error = new ApiException('ERR_TEST', '測試錯誤');
    expect(error.name).toBe('ApiException');
  });

  it('應該正確設定 message', () => {
    const error = new ApiException('ERR_TEST', '測試錯誤訊息');
    expect(error.message).toBe('測試錯誤訊息');
  });

  it('應該正確設定 code', () => {
    const error = new ApiException(ErrorCode.NOT_FOUND, '找不到');
    expect(error.code).toBe(ErrorCode.NOT_FOUND);
  });

  it('應該正確設定自訂字串 code', () => {
    const error = new ApiException('CUSTOM_CODE', '自訂錯誤');
    expect(error.code).toBe('CUSTOM_CODE');
  });

  it('statusCode 預設為 500', () => {
    const error = new ApiException('ERR_TEST', '測試');
    expect(error.statusCode).toBe(500);
  });

  it('應該正確設定自訂 statusCode', () => {
    const error = new ApiException('ERR_TEST', '測試', 404);
    expect(error.statusCode).toBe(404);
  });

  it('details 預設為空陣列', () => {
    const error = new ApiException('ERR_TEST', '測試');
    expect(error.details).toEqual([]);
  });

  it('應該正確設定 details', () => {
    const details = [
      { field: 'email', message: 'Email 格式不正確' },
      { field: 'phone', message: '電話號碼不正確', value: '12345' },
    ];
    const error = new ApiException('ERR_VALIDATION', '驗證失敗', 422, details);
    expect(error.details).toEqual(details);
    expect(error.details).toHaveLength(2);
  });

  it('應該自動設定 timestamp', () => {
    const before = new Date();
    const error = new ApiException('ERR_TEST', '測試');
    const after = new Date();

    expect(error.timestamp).toBeInstanceOf(Date);
    expect(error.timestamp.getTime()).toBeGreaterThanOrEqual(before.getTime());
    expect(error.timestamp.getTime()).toBeLessThanOrEqual(after.getTime());
  });
});

// ============================================================================
// ApiException.fromResponse 靜態方法
// ============================================================================

describe('ApiException.fromResponse', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該從 ErrorResponse 建立 ApiException', () => {
    const response = {
      success: false as const,
      error: {
        code: ErrorCode.NOT_FOUND,
        message: '公文不存在',
      },
      timestamp: new Date().toISOString(),
    };

    const error = ApiException.fromResponse(response, 404);

    expect(error).toBeInstanceOf(ApiException);
    expect(error.code).toBe(ErrorCode.NOT_FOUND);
    expect(error.message).toBe('公文不存在');
    expect(error.statusCode).toBe(404);
  });

  it('statusCode 預設為 500', () => {
    const response = {
      success: false as const,
      error: {
        code: ErrorCode.INTERNAL_ERROR,
        message: '伺服器錯誤',
      },
      timestamp: new Date().toISOString(),
    };

    const error = ApiException.fromResponse(response);
    expect(error.statusCode).toBe(500);
  });

  it('應該正確傳遞 details', () => {
    const details = [{ field: 'name', message: '名稱不可為空' }];
    const response = {
      success: false as const,
      error: {
        code: ErrorCode.VALIDATION_ERROR,
        message: '驗證失敗',
        details,
      },
      timestamp: new Date().toISOString(),
    };

    const error = ApiException.fromResponse(response, 422);
    expect(error.details).toEqual(details);
  });
});

// ============================================================================
// ApiException.fromAxiosError 靜態方法
// ============================================================================

describe('ApiException.fromAxiosError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('網路錯誤（無 response）應回傳 NETWORK_ERROR', () => {
    const axiosError = {
      response: undefined,
      code: 'ERR_NETWORK',
      message: 'Network Error',
      isAxiosError: true,
      toJSON: () => ({}),
      name: 'AxiosError',
      config: {} as never,
    };

    const error = ApiException.fromAxiosError(axiosError as never);
    expect(error.code).toBe(ErrorCode.NETWORK_ERROR);
    expect(error.statusCode).toBe(0);
    expect(error.message).toBe('網路連線失敗，請檢查網路狀態');
  });

  it('請求超時應回傳 TIMEOUT', () => {
    const axiosError = {
      response: undefined,
      code: 'ECONNABORTED',
      message: 'timeout of 30000ms exceeded',
      isAxiosError: true,
      toJSON: () => ({}),
      name: 'AxiosError',
      config: {} as never,
    };

    const error = ApiException.fromAxiosError(axiosError as never);
    expect(error.code).toBe(ErrorCode.TIMEOUT);
    expect(error.statusCode).toBe(0);
  });

  it('後端統一格式錯誤應正確解析', () => {
    const axiosError = {
      response: {
        status: 422,
        data: {
          success: false,
          error: {
            code: ErrorCode.VALIDATION_ERROR,
            message: '驗證失敗',
            details: [{ field: 'email', message: 'Email 已存在' }],
          },
        },
      },
      isAxiosError: true,
      toJSON: () => ({}),
      name: 'AxiosError',
      config: {} as never,
    };

    const error = ApiException.fromAxiosError(axiosError as never);
    expect(error.code).toBe(ErrorCode.VALIDATION_ERROR);
    expect(error.statusCode).toBe(422);
    expect(error.details).toHaveLength(1);
  });

  it('FastAPI HTTPException 格式應正確解析', () => {
    const axiosError = {
      response: {
        status: 400,
        data: { detail: '請求參數缺少必要欄位' },
      },
      isAxiosError: true,
      toJSON: () => ({}),
      name: 'AxiosError',
      config: {} as never,
    };

    const error = ApiException.fromAxiosError(axiosError as never);
    expect(error.code).toBe(ErrorCode.BAD_REQUEST);
    expect(error.message).toBe('請求參數缺少必要欄位');
    expect(error.statusCode).toBe(400);
  });

  it('FastAPI HTTPException 非 400 狀態碼應使用 INTERNAL_ERROR', () => {
    const axiosError = {
      response: {
        status: 500,
        data: { detail: '內部伺服器錯誤' },
      },
      isAxiosError: true,
      toJSON: () => ({}),
      name: 'AxiosError',
      config: {} as never,
    };

    const error = ApiException.fromAxiosError(axiosError as never);
    expect(error.code).toBe(ErrorCode.INTERNAL_ERROR);
    expect(error.message).toBe('內部伺服器錯誤');
  });

  it('應根據 HTTP 狀態碼產生對應的錯誤碼', () => {
    const statusMap: Array<[number, ErrorCode, string]> = [
      [400, ErrorCode.BAD_REQUEST, '請求參數錯誤'],
      [401, ErrorCode.UNAUTHORIZED, '請先登入'],
      [403, ErrorCode.FORBIDDEN, '您沒有權限執行此操作'],
      [404, ErrorCode.NOT_FOUND, '找不到請求的資源'],
      [409, ErrorCode.CONFLICT, '資源衝突'],
      [422, ErrorCode.VALIDATION_ERROR, '輸入資料驗證失敗'],
      [429, ErrorCode.TOO_MANY_REQUESTS, '請求過於頻繁，請稍後再試'],
      [500, ErrorCode.INTERNAL_ERROR, '伺服器內部錯誤'],
      [502, ErrorCode.SERVICE_UNAVAILABLE, '服務暫時無法使用'],
      [503, ErrorCode.SERVICE_UNAVAILABLE, '服務暫時無法使用'],
    ];

    for (const [status, expectedCode, expectedMessage] of statusMap) {
      const axiosError = {
        response: {
          status,
          data: {},  // 非統一格式，無 error 或 detail 欄位
        },
        isAxiosError: true,
        toJSON: () => ({}),
        name: 'AxiosError',
        config: {} as never,
      };

      const error = ApiException.fromAxiosError(axiosError as never);
      expect(error.code, `HTTP ${status} 應對應 ${expectedCode}`).toBe(expectedCode);
      expect(error.message, `HTTP ${status} 應對應訊息 "${expectedMessage}"`).toBe(expectedMessage);
      expect(error.statusCode).toBe(status);
    }
  });

  it('未知狀態碼應回傳 INTERNAL_ERROR', () => {
    const axiosError = {
      response: {
        status: 418,  // I'm a teapot
        data: {},
      },
      isAxiosError: true,
      toJSON: () => ({}),
      name: 'AxiosError',
      config: {} as never,
    };

    const error = ApiException.fromAxiosError(axiosError as never);
    expect(error.code).toBe(ErrorCode.INTERNAL_ERROR);
    expect(error.message).toBe('發生未知錯誤');
  });
});

// ============================================================================
// ApiException 實例方法
// ============================================================================

describe('ApiException.getUserMessage', () => {
  it('應該回傳 message 字串', () => {
    const error = new ApiException('ERR_TEST', '使用者友善訊息');
    expect(error.getUserMessage()).toBe('使用者友善訊息');
  });
});

describe('ApiException.getFieldErrors', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('無 details 時應回傳空物件', () => {
    const error = new ApiException('ERR_TEST', '測試');
    expect(error.getFieldErrors()).toEqual({});
  });

  it('應該將 details 轉換為 field:message 格式', () => {
    const details = [
      { field: 'email', message: 'Email 格式不正確' },
      { field: 'phone', message: '電話號碼不正確' },
    ];
    const error = new ApiException('ERR_VALIDATION', '驗證失敗', 422, details);

    const fieldErrors = error.getFieldErrors();
    expect(fieldErrors).toEqual({
      email: 'Email 格式不正確',
      phone: '電話號碼不正確',
    });
  });

  it('無 field 的 detail 應被忽略', () => {
    const details = [
      { field: 'name', message: '名稱不可為空' },
      { message: '通用錯誤' },  // 無 field
    ];
    const error = new ApiException('ERR_VALIDATION', '驗證失敗', 422, details);

    const fieldErrors = error.getFieldErrors();
    expect(fieldErrors).toEqual({ name: '名稱不可為空' });
    expect(Object.keys(fieldErrors)).toHaveLength(1);
  });
});

describe('ApiException.isBusinessError', () => {
  it('400 應為業務錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 400);
    expect(error.isBusinessError()).toBe(true);
  });

  it('409 應為業務錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 409);
    expect(error.isBusinessError()).toBe(true);
  });

  it('422 應為業務錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 422);
    expect(error.isBusinessError()).toBe(true);
  });

  it('403 不應為業務錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 403);
    expect(error.isBusinessError()).toBe(false);
  });

  it('500 不應為業務錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 500);
    expect(error.isBusinessError()).toBe(false);
  });

  it('0（網路錯誤）不應為業務錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 0);
    expect(error.isBusinessError()).toBe(false);
  });
});

describe('ApiException.isGlobalError', () => {
  it('403 應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 403);
    expect(error.isGlobalError()).toBe(true);
  });

  it('500 應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 500);
    expect(error.isGlobalError()).toBe(true);
  });

  it('502 應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 502);
    expect(error.isGlobalError()).toBe(true);
  });

  it('503 應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 503);
    expect(error.isGlobalError()).toBe(true);
  });

  it('0（網路錯誤）應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 0);
    expect(error.isGlobalError()).toBe(true);
  });

  it('400 不應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 400);
    expect(error.isGlobalError()).toBe(false);
  });

  it('422 不應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 422);
    expect(error.isGlobalError()).toBe(false);
  });

  it('200 不應為全域錯誤', () => {
    const error = new ApiException('ERR_TEST', '測試', 200);
    expect(error.isGlobalError()).toBe(false);
  });
});

// ============================================================================
// ApiErrorBus 事件匯流排
// ============================================================================

describe('ApiErrorBus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('apiErrorBus 應該被正確匯出', () => {
    expect(apiErrorBus).toBeDefined();
    expect(typeof apiErrorBus.subscribe).toBe('function');
    expect(typeof apiErrorBus.emit).toBe('function');
  });

  it('subscribe 應該回傳 unsubscribe 函數', () => {
    const listener = vi.fn();
    const unsubscribe = apiErrorBus.subscribe(listener);

    expect(typeof unsubscribe).toBe('function');
    unsubscribe();
  });

  it('emit 應該觸發已訂閱的 listener', () => {
    const listener = vi.fn();
    const unsubscribe = apiErrorBus.subscribe(listener);

    const error = new ApiException('ERR_TEST', '測試錯誤', 500);
    apiErrorBus.emit(error);

    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith(error);

    unsubscribe();
  });

  it('emit 應該觸發所有已訂閱的 listeners', () => {
    const listener1 = vi.fn();
    const listener2 = vi.fn();
    const listener3 = vi.fn();

    const unsub1 = apiErrorBus.subscribe(listener1);
    const unsub2 = apiErrorBus.subscribe(listener2);
    const unsub3 = apiErrorBus.subscribe(listener3);

    const error = new ApiException('ERR_TEST', '測試', 500);
    apiErrorBus.emit(error);

    expect(listener1).toHaveBeenCalledTimes(1);
    expect(listener2).toHaveBeenCalledTimes(1);
    expect(listener3).toHaveBeenCalledTimes(1);

    unsub1();
    unsub2();
    unsub3();
  });

  it('unsubscribe 後不應再接收事件', () => {
    const listener = vi.fn();
    const unsubscribe = apiErrorBus.subscribe(listener);

    // 發出第一個事件
    apiErrorBus.emit(new ApiException('ERR_1', '錯誤 1', 500));
    expect(listener).toHaveBeenCalledTimes(1);

    // 取消訂閱
    unsubscribe();

    // 發出第二個事件
    apiErrorBus.emit(new ApiException('ERR_2', '錯誤 2', 500));
    expect(listener).toHaveBeenCalledTimes(1); // 仍然只有 1 次
  });

  it('多次 emit 應多次觸發 listener', () => {
    const listener = vi.fn();
    const unsubscribe = apiErrorBus.subscribe(listener);

    apiErrorBus.emit(new ApiException('ERR_1', '錯誤 1', 500));
    apiErrorBus.emit(new ApiException('ERR_2', '錯誤 2', 403));
    apiErrorBus.emit(new ApiException('ERR_3', '錯誤 3', 0));

    expect(listener).toHaveBeenCalledTimes(3);

    unsubscribe();
  });

  it('unsubscribe 僅移除特定 listener，不影響其他', () => {
    const listener1 = vi.fn();
    const listener2 = vi.fn();

    const unsub1 = apiErrorBus.subscribe(listener1);
    const unsub2 = apiErrorBus.subscribe(listener2);

    // 移除 listener1
    unsub1();

    apiErrorBus.emit(new ApiException('ERR_TEST', '測試', 500));

    expect(listener1).not.toHaveBeenCalled();
    expect(listener2).toHaveBeenCalledTimes(1);

    unsub2();
  });

  it('沒有訂閱者時 emit 不應拋出錯誤', () => {
    expect(() => {
      apiErrorBus.emit(new ApiException('ERR_TEST', '測試', 500));
    }).not.toThrow();
  });

  it('重複 unsubscribe 不應拋出錯誤', () => {
    const listener = vi.fn();
    const unsubscribe = apiErrorBus.subscribe(listener);

    unsubscribe();
    expect(() => unsubscribe()).not.toThrow();
  });

  it('listener 接收到的 error 應為 ApiException 實例', () => {
    const listener = vi.fn();
    const unsubscribe = apiErrorBus.subscribe(listener);

    const error = new ApiException(ErrorCode.FORBIDDEN, '沒有權限', 403);
    apiErrorBus.emit(error);

    const receivedError = listener.mock.calls[0][0];
    expect(receivedError).toBeInstanceOf(ApiException);
    expect(receivedError.code).toBe(ErrorCode.FORBIDDEN);
    expect(receivedError.statusCode).toBe(403);
    expect(receivedError.message).toBe('沒有權限');

    unsubscribe();
  });
});
