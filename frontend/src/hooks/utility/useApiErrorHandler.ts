/**
 * API 錯誤處理 Hook
 */
import { useCallback, useState } from 'react';
import { message, notification } from 'antd';

interface ApiError {
  status?: number;
  message: string;
  detail?: string;
  timestamp?: string;
  path?: string;
}

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
  handleError: (error: any) => void;
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

  const parseError = (error: any): ApiError => {
    if (typeof error === 'string') {
      return { message: error };
    }

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      let messageText = '發生未知錯誤';
      let detail = '';

      if (typeof data === 'string') {
        messageText = data;
      } else if (data && typeof data === 'object') {
        messageText = data.message || data.detail || data.error || messageText;
        detail = data.detail || '';
      }

      return {
        status,
        message: getStatusMessage(status, messageText),
        detail,
        timestamp: new Date().toISOString(),
        path: error.response.config?.url || ''
      };
    }

    if (error.request) {
      return {
        message: '網路連線失敗，請檢查網路狀態',
        detail: 'Network Error',
        timestamp: new Date().toISOString()
      };
    }

    return {
      message: error.message || '發生未預期的錯誤',
      detail: error.stack || '',
      timestamp: new Date().toISOString()
    };
  };

  const getStatusMessage = (status: number, originalMessage: string): string => {
    const statusMessages: Record<number, string> = {
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
      504: '伺服器回應逾時'
    };

    return statusMessages[status] || originalMessage;
  };

  const showErrorFeedback = (error: ApiError) => {
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
  };

  const handleError = useCallback((error: any) => {
    const parsedError = parseError(error);
    setError(parsedError);

    showErrorFeedback(parsedError);

    if (onError) {
      onError(parsedError);
    }

    console.error('API Error:', {
      originalError: error,
      parsedError,
      timestamp: new Date().toISOString()
    });
  }, [onError, showMessage, showNotification]);

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
    console.error('Unhandled promise rejection:', event.reason);
    event.preventDefault();

    notification.error({
      message: '系統錯誤',
      description: '發生未處理的錯誤，請重新整理頁面或聯繫技術支援',
      duration: 0,
      placement: 'topRight'
    });
  });

  window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);

    notification.error({
      message: '頁面錯誤',
      description: '頁面執行時發生錯誤，建議重新整理頁面',
      duration: 5,
      placement: 'topRight'
    });
  });
};

export default useApiErrorHandler;