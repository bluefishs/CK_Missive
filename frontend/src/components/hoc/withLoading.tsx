/**
 * 載入狀態高階元件 (HOC)
 *
 * 提供統一的載入狀態處理封裝
 *
 * @version 1.0.0
 * @date 2026-01-06
 */

import React, { ComponentType, useState, useCallback } from 'react';
import { Alert } from 'antd';
import { PageLoading } from '../common';

/** 載入狀態 */
export interface LoadingState {
  isLoading: boolean;
  error: Error | null;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
  clearError: () => void;
  withLoading: <T>(promise: Promise<T>) => Promise<T>;
}

/** HOC 選項 */
export interface WithLoadingOptions {
  /** 是否全頁載入 */
  fullPage?: boolean;
  /** 載入訊息 */
  loadingMessage?: string;
  /** 是否顯示錯誤 */
  showError?: boolean;
  /** 錯誤標題 */
  errorTitle?: string;
}

/**
 * 載入狀態 HOC
 *
 * 為元件注入載入狀態管理功能
 *
 * @example
 * ```tsx
 * interface MyPageProps extends WithLoadingInjectedProps {
 *   title: string;
 * }
 *
 * const MyPage: React.FC<MyPageProps> = ({ title, loadingState }) => {
 *   const handleFetch = async () => {
 *     await loadingState.withLoading(fetchData());
 *   };
 *
 *   if (loadingState.isLoading) {
 *     return <Spin />;
 *   }
 *
 *   return <div>{title}</div>;
 * };
 *
 * export default withLoading(MyPage);
 * ```
 */
export interface WithLoadingInjectedProps {
  loadingState: LoadingState;
}

export function withLoading<P extends WithLoadingInjectedProps>(
  WrappedComponent: ComponentType<P>,
  options: WithLoadingOptions = {}
): ComponentType<Omit<P, keyof WithLoadingInjectedProps>> {
  const {
    fullPage = false,
    loadingMessage = '載入中...',
    showError = true,
    errorTitle = '發生錯誤',
  } = options;

  const WithLoadingComponent: React.FC<Omit<P, keyof WithLoadingInjectedProps>> = (props) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const clearError = useCallback(() => setError(null), []);

    const withLoadingWrapper = useCallback(async <T,>(promise: Promise<T>): Promise<T> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await promise;
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    }, []);

    const loadingState: LoadingState = {
      isLoading,
      error,
      setLoading: setIsLoading,
      setError,
      clearError,
      withLoading: withLoadingWrapper,
    };

    // 全頁載入
    if (fullPage && isLoading) {
      return <PageLoading message={loadingMessage} />;
    }

    // 顯示錯誤
    if (showError && error) {
      return (
        <div style={{ padding: 24 }}>
          <Alert
            type="error"
            message={errorTitle}
            description={error.message}
            showIcon
            closable
            onClose={clearError}
          />
          <WrappedComponent {...(props as P)} loadingState={loadingState} />
        </div>
      );
    }

    return <WrappedComponent {...(props as P)} loadingState={loadingState} />;
  };

  WithLoadingComponent.displayName = `withLoading(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return WithLoadingComponent;
}

/**
 * 使用載入狀態的 Hook
 *
 * @example
 * ```tsx
 * const MyComponent = () => {
 *   const { isLoading, withLoading, error } = useLoadingState();
 *
 *   const handleFetch = async () => {
 *     await withLoading(fetchData());
 *   };
 *
 *   return isLoading ? <Spin /> : <div>Content</div>;
 * };
 * ```
 */
export function useLoadingState(): LoadingState {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const withLoadingWrapper = useCallback(async <T,>(promise: Promise<T>): Promise<T> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await promise;
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoading,
    error,
    setLoading: setIsLoading,
    setError,
    clearError,
    withLoading: withLoadingWrapper,
  };
}

export default withLoading;
