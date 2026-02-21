/**
 * 儀表板 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */

import { useQuery } from '@tanstack/react-query';
import { dashboardApi, FormattedDocument } from '../../api/dashboardApi';
import { defaultQueryOptions } from '../../config/queryConfig';

// ============================================================================
// 查詢鍵
// ============================================================================

const dashboardKeys = {
  all: ['dashboard'] as const,
  data: () => [...dashboardKeys.all, 'data'] as const,
};

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得儀表板資料
 */
export const useDashboardData = () => {
  return useQuery({
    queryKey: dashboardKeys.data(),
    queryFn: () => dashboardApi.getDashboardData(),
    ...defaultQueryOptions.detail,
  });
};

// ============================================================================
// 組合 Hook
// ============================================================================

/**
 * 儀表板頁面 Hook
 *
 * 整合統計資料與近期公文
 */
export const useDashboardPage = () => {
  const dashboardQuery = useDashboardData();

  // 格式化近期公文
  const recentDocuments: FormattedDocument[] = dashboardQuery.data?.recent_documents
    ? dashboardApi.formatRecentDocuments(dashboardQuery.data.recent_documents)
    : [];

  return {
    // 統計資料
    stats: dashboardQuery.data?.stats ?? {
      total: 0,
      approved: 0,
      pending: 0,
      rejected: 0,
    },

    // 近期公文 (已格式化)
    recentDocuments,

    // 狀態
    isLoading: dashboardQuery.isLoading,
    isError: dashboardQuery.isError,
    error: dashboardQuery.error,

    // 操作
    refetch: dashboardQuery.refetch,
  };
};

export default useDashboardPage;
