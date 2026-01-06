import React from 'react';
// @ts-ignore
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// @ts-ignore
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { staleTimeConfig } from '../config/queryConfig';

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
      // 失敗時重試 3 次
      retry: 3,
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