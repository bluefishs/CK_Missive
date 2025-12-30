import React from 'react';
// @ts-ignore
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// @ts-ignore
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// 建立 QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 5分鐘快取時間
      staleTime: 5 * 60 * 1000,
      // 10分鐘垃圾回收時間
      gcTime: 10 * 60 * 1000,
      // 失敗時重試 3 次
      retry: 3,
      // 重試延遲
      retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // 聚焦視窗時重新獲取
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