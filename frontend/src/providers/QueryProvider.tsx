import React from 'react';
// @ts-ignore
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// @ts-ignore
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { message } from 'antd';
import { staleTimeConfig } from '../config/queryConfig';
import { parseApiError } from '../utils/apiErrorParser';

/**
 * 建立 QueryClient
 *
 * 快取策略說明：
 * - 下拉選單：10 分鐘（staleTimeConfig.dropdown）
 * - 列表資料：30 秒（staleTimeConfig.list）
 * - 詳情資料：1 分鐘（staleTimeConfig.detail）
 * - 統計資料：5 分鐘（staleTimeConfig.statistics）
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 預設使用列表資料快取時間
      staleTime: staleTimeConfig.list,
      // 5分鐘垃圾回收時間
      gcTime: 5 * 60 * 1000,
      // 失敗時重試 3 次，但排除 429 (Too Many Requests) 和 401/403 錯誤
      retry: (failureCount, error) => {
        // 不重試的錯誤碼：401 (未授權)、403 (禁止)、429 (請求過多)
        const err = error as { statusCode?: number; response?: { status?: number } };
        const status = err.statusCode || err.response?.status;
        if (status === 401 || status === 403 || status === 429) {
          return false;
        }
        return failureCount < 3;
      },
      // 重試延遲
      retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // 聚焦視窗時不重新獲取（避免頻繁請求）
      refetchOnWindowFocus: false,
      // 重新連接時重新獲取
      refetchOnReconnect: 'always' as const,
    },
    mutations: {
      retry: 1,
      retryDelay: 1000,
      onError: (error: Error) => {
        const parsed = parseApiError(error);
        // 401 由 API client 的 token refresh 機制處理，不重複顯示
        if (parsed.status === 401) return;
        const level = parsed.status && parsed.status >= 500 ? 'error' : 'warning';
        message[level](parsed.message);
        if (import.meta.env.DEV) {
          console.error('[Mutation Error]', parsed);
        }
      },
    },
  },
});

interface QueryProviderProps {
  children: React.ReactNode;
}

export const QueryProvider: React.FC<QueryProviderProps> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
};

export { queryClient };