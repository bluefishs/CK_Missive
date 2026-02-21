/**
 * API 錯誤處理 Hook
 *
 * 錯誤解析邏輯已提取至 utils/apiErrorParser.ts 共用。
 */
import { useCallback, useState } from 'react';
import { message, notification } from 'antd';
import { logger } from '../../utils/logger';
import { parseApiError, type ParsedApiError } from '../../utils/apiErrorParser';

type ApiError = ParsedApiError;

interface UseApiErrorHandlerOptions {
  showNotification?: boolean;
  showMessage?: boolean;
  retryable?: boolean;
  onError?: (error: ApiError) => void;
}

interface UseApiErrorHandlerReturn {
  error: ApiError | null;
  isRetrying: boolean;
  retryCount: number;
  handleError: (error: unknown) => void;
  clearError: () => void;
  retry: () => Promise<void>;
  setRetryFunction: (fn: () => Promise<void>) => void;
}

export const useApiErrorHandler = (
  options: UseApiErrorHandlerOptions = {}
): UseApiErrorHandlerReturn => {
  const {
    showNotification = true,
    showMessage = false,
    retryable = false,
    onError
  } = options;

  const [error, setError] = useState<ApiError | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [retryFunction, setRetryFunction] = useState<(() => Promise<void>) | null>(null);

  const showErrorFeedback = useCallback((error: ApiError) => {
    const { status, message: errorMessage, detail } = error;

    if (showMessage) {
      if (status && status >= 500) {
        message.error(errorMessage);
      } else {
        message.warning(errorMessage);
      }
    }

    if (showNotification) {
      const notificationType = status && status >= 500 ? 'error' : 'warning';
      let description = errorMessage;

      if (detail && process.env.NODE_ENV === 'development') {
        description = `${errorMessage}\n\n技術詳情：\n${detail}`;
      }

      notification[notificationType]({
        message: '操作失敗',
        description,
        duration: 5,
        placement: 'topRight'
      });
    }
  }, [showMessage, showNotification]);

  const handleError = useCallback((error: unknown) => {
    const parsedError = parseApiError(error);
    setError(parsedError);

    showErrorFeedback(parsedError);

    if (onError) {
      onError(parsedError);
    }

    logger.error('API Error:', {
      originalError: error,
      parsedError,
      timestamp: new Date().toISOString()
    });
  }, [onError, showErrorFeedback]);

  const clearError = useCallback(() => {
    setError(null);
    setRetryCount(0);
  }, []);

  const retry = useCallback(async () => {
    if (!retryFunction || !retryable) {
      return;
    }

    setIsRetrying(true);
    setRetryCount(prev => prev + 1);

    try {
      await retryFunction();
      clearError();
    } catch (error) {
      handleError(error);
    } finally {
      setIsRetrying(false);
    }
  }, [retryFunction, retryable, clearError, handleError]);

  const setRetryFunctionWrapper = useCallback((fn: () => Promise<void>) => {
    setRetryFunction(() => fn);
  }, []);

  return {
    error,
    isRetrying,
    retryCount,
    handleError,
    clearError,
    retry,
    setRetryFunction: setRetryFunctionWrapper
  };
};

export const setupGlobalErrorHandler = () => {
  window.addEventListener('unhandledrejection', (event) => {
    logger.error('Unhandled promise rejection:', event.reason);
    event.preventDefault();

    notification.error({
      message: '系統錯誤',
      description: '發生未處理的錯誤，請重新整理頁面或聯繫技術支援',
      duration: 0,
      placement: 'topRight'
    });
  });

  window.addEventListener('error', (event) => {
    logger.error('Global error:', event.error);

    notification.error({
      message: '頁面錯誤',
      description: '頁面執行時發生錯誤，建議重新整理頁面',
      duration: 5,
      placement: 'topRight'
    });
  });
};

export default useApiErrorHandler;