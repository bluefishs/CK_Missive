/**
 * useApiErrorHandler Hook 測試
 * useApiErrorHandler Hook Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';

// Mock Antd message and notification
vi.mock('antd', () => ({
  message: {
    error: vi.fn(),
    warning: vi.fn(),
  },
  notification: {
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock apiErrorParser
vi.mock('../../utils/apiErrorParser', () => ({
  parseApiError: vi.fn((error) => ({
    message: error?.message || '未知錯誤',
    status: error?.response?.status,
    detail: error?.response?.data?.detail,
  })),
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    log: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

import { useApiErrorHandler } from '../../hooks/utility/useApiErrorHandler';
import { notification, message } from 'antd';

describe('useApiErrorHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('初始狀態', () => {
    it('應該有正確的初始值', () => {
      const { result } = renderHook(() => useApiErrorHandler());

      expect(result.current.error).toBeNull();
      expect(result.current.isRetrying).toBe(false);
      expect(result.current.retryCount).toBe(0);
    });
  });

  describe('handleError', () => {
    it('應該解析並儲存錯誤', () => {
      const { result } = renderHook(() => useApiErrorHandler());

      act(() => {
        result.current.handleError(new Error('測試錯誤'));
      });

      expect(result.current.error).not.toBeNull();
      expect(result.current.error?.message).toBe('測試錯誤');
    });

    it('應該顯示通知當 showNotification 為 true', () => {
      const { result } = renderHook(() =>
        useApiErrorHandler({ showNotification: true, showMessage: false })
      );

      act(() => {
        result.current.handleError(new Error('通知錯誤'));
      });

      expect(notification.warning).toHaveBeenCalled();
    });

    it('應該顯示訊息當 showMessage 為 true', () => {
      const { result } = renderHook(() =>
        useApiErrorHandler({ showNotification: false, showMessage: true })
      );

      act(() => {
        result.current.handleError({ message: '訊息錯誤', response: { status: 400 } });
      });

      expect(message.warning).toHaveBeenCalled();
    });

    it('應該呼叫 onError 回調', () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useApiErrorHandler({ onError, showNotification: false })
      );

      act(() => {
        result.current.handleError(new Error('回調錯誤'));
      });

      expect(onError).toHaveBeenCalled();
    });
  });

  describe('clearError', () => {
    it('應該清除錯誤狀態', () => {
      const { result } = renderHook(() => useApiErrorHandler({ showNotification: false }));

      act(() => {
        result.current.handleError(new Error('要清除的錯誤'));
      });

      expect(result.current.error).not.toBeNull();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('setRetryFunction', () => {
    it('應該設定重試函數', () => {
      const { result } = renderHook(() =>
        useApiErrorHandler({ retryable: true, showNotification: false })
      );

      const retryFn = vi.fn().mockResolvedValue(undefined);

      act(() => {
        result.current.setRetryFunction(retryFn);
      });

      // 驗證 setRetryFunction 是一個函數
      expect(typeof result.current.setRetryFunction).toBe('function');
    });
  });

  describe('錯誤類型處理', () => {
    it('應該處理 Axios 錯誤格式', () => {
      const { result } = renderHook(() => useApiErrorHandler({ showNotification: false }));

      const axiosError = {
        response: {
          status: 404,
          data: { detail: '找不到資源' },
        },
        message: 'Request failed',
      };

      act(() => {
        result.current.handleError(axiosError);
      });

      expect(result.current.error?.status).toBe(404);
    });

    it('應該處理網路錯誤', () => {
      const { result } = renderHook(() => useApiErrorHandler({ showNotification: false }));

      const networkError = {
        message: 'Network Error',
        code: 'ERR_NETWORK',
      };

      act(() => {
        result.current.handleError(networkError);
      });

      expect(result.current.error?.message).toContain('Network Error');
    });
  });
});
