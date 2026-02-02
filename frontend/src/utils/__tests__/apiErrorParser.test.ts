/**
 * API 錯誤解析工具測試
 * API Error Parser Utility Tests
 */
import { describe, it, expect } from 'vitest';
import { parseApiError } from '../apiErrorParser';

describe('parseApiError', () => {
  describe('標準 Error 物件', () => {
    it('應該解析標準 Error 物件', () => {
      const error = new Error('測試錯誤');
      const result = parseApiError(error);

      expect(result.message).toBe('測試錯誤');
      expect(result.status).toBeUndefined();
    });
  });

  describe('Axios 錯誤格式', () => {
    it('應該解析帶有 response 的 Axios 錯誤', () => {
      const axiosError = {
        response: {
          status: 404,
          data: {
            detail: '資源不存在',
          },
        },
        message: 'Request failed with status code 404',
      };

      const result = parseApiError(axiosError);

      expect(result.status).toBe(404);
      expect(result.message).toContain('資源不存在');
    });

    it('應該處理 500 伺服器錯誤', () => {
      const serverError = {
        response: {
          status: 500,
          data: {
            detail: '內部伺服器錯誤',
          },
        },
      };

      const result = parseApiError(serverError);

      expect(result.status).toBe(500);
    });

    it('應該處理 401 未授權錯誤', () => {
      const authError = {
        response: {
          status: 401,
          data: {
            detail: '認證失敗',
          },
        },
      };

      const result = parseApiError(authError);

      expect(result.status).toBe(401);
    });

    it('應該處理 403 禁止訪問錯誤', () => {
      const forbiddenError = {
        response: {
          status: 403,
          data: {
            detail: '權限不足',
          },
        },
      };

      const result = parseApiError(forbiddenError);

      expect(result.status).toBe(403);
    });
  });

  describe('FastAPI 錯誤格式', () => {
    it('應該解析 FastAPI HTTPException detail 格式', () => {
      const fastApiError = {
        response: {
          status: 400,
          data: {
            detail: '請求格式錯誤',
          },
        },
      };

      const result = parseApiError(fastApiError);

      // parseApiError 會返回適當的錯誤訊息
      expect(result.status).toBe(400);
      expect(result.message).toBeTruthy();
    });

    it('應該解析 FastAPI 驗證錯誤格式', () => {
      const validationError = {
        response: {
          status: 422,
          data: {
            detail: [
              { loc: ['body', 'email'], msg: '無效的電子郵件格式', type: 'value_error' },
            ],
          },
        },
      };

      const result = parseApiError(validationError);

      expect(result.status).toBe(422);
    });
  });

  describe('網路錯誤', () => {
    it('應該處理無 response 的網路錯誤', () => {
      const networkError = {
        message: 'Network Error',
        code: 'ERR_NETWORK',
      };

      const result = parseApiError(networkError);

      expect(result.message).toContain('Network Error');
      expect(result.status).toBeUndefined();
    });
  });

  describe('特殊情況', () => {
    it('應該處理 null 值', () => {
      const result = parseApiError(null);
      expect(result.message).toBeTruthy();
    });

    it('應該處理 undefined 值', () => {
      const result = parseApiError(undefined);
      expect(result.message).toBeTruthy();
    });

    it('應該處理字串錯誤', () => {
      const result = parseApiError('字串錯誤訊息');
      expect(result.message).toContain('字串錯誤訊息');
    });

    it('應該處理數字', () => {
      const result = parseApiError(500);
      expect(result.message).toBeTruthy();
    });
  });
});
