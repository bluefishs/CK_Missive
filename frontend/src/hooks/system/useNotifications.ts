/**
 * 通知中心 Hook
 *
 * 集中管理通知相關的 useQuery 邏輯
 *
 * @version 1.1.0
 * @date 2026-01-23
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';

// ============================================================================
// 型別定義
// ============================================================================

export interface SystemNotification {
  id: number;
  type: string;
  severity: string;
  title: string;
  message: string;
  source_table?: string;
  source_id?: number;
  changes?: Record<string, unknown>;
  user_name?: string;
  is_read: boolean;
  created_at?: string;
}

interface NotificationListResponse {
  success: boolean;
  items: SystemNotification[];
  total: number;
  unread_count: number;
}

interface UnreadCountResponse {
  success: boolean;
  unread_count: number;
}

interface MarkReadResponse {
  success: boolean;
  updated_count: number;
  message: string;
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * 未讀通知數量 Hook
 */
export const useUnreadNotificationCount = (enabled: boolean = true) => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery<UnreadCountResponse>({
    queryKey: ['notifications-unread-count'],
    queryFn: async () => {
      return await apiClient.post<UnreadCountResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.UNREAD_COUNT, {});
    },
    refetchInterval: 30000, // 每 30 秒自動刷新
    enabled,
  });

  return {
    unreadCount: data?.unread_count || 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};

/**
 * 通知列表 Hook
 */
export const useNotificationList = (enabled: boolean = true) => {
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery<NotificationListResponse>({
    queryKey: ['notifications-list'],
    queryFn: async () => {
      return await apiClient.post<NotificationListResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.LIST, {
        limit: 20,
        is_read: null,
      });
    },
    enabled,
  });

  return {
    notifications: data?.items || [],
    total: data?.total || 0,
    unreadCount: data?.unread_count || 0,
    isLoading,
    error: error as Error | null,
    refetch,
  };
};

/**
 * 通知操作 Hook (標記已讀等)
 */
export const useNotificationMutations = () => {
  const queryClient = useQueryClient();

  // 標記已讀
  const markReadMutation = useMutation<MarkReadResponse, Error, number[]>({
    mutationFn: async (ids: number[]) => {
      return await apiClient.post<MarkReadResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.MARK_READ, {
        notification_ids: ids,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] });
    },
  });

  // 全部標記已讀
  const markAllReadMutation = useMutation<MarkReadResponse, Error, void>({
    mutationFn: async () => {
      return await apiClient.post<MarkReadResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.MARK_ALL_READ, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] });
    },
  });

  return {
    markRead: markReadMutation.mutate,
    markReadAsync: markReadMutation.mutateAsync,
    markAllRead: markAllReadMutation.mutate,
    markAllReadAsync: markAllReadMutation.mutateAsync,
    isMarkingRead: markReadMutation.isPending,
    isMarkingAllRead: markAllReadMutation.isPending,
  };
};

/**
 * 通知中心整合 Hook
 * 結合未讀數量、列表和操作功能
 */
export const useNotificationCenter = (listEnabled: boolean = false) => {
  const { unreadCount, refetch: refetchUnread } = useUnreadNotificationCount(true);
  const { notifications, total, isLoading, refetch: refetchList } = useNotificationList(listEnabled);
  const mutations = useNotificationMutations();

  return {
    // 資料
    unreadCount,
    notifications,
    total,
    isLoading,
    // 操作
    markRead: mutations.markRead,
    markAllRead: mutations.markAllRead,
    isMarkingRead: mutations.isMarkingRead,
    isMarkingAllRead: mutations.isMarkingAllRead,
    // 刷新
    refetch: () => {
      refetchUnread();
      refetchList();
    },
  };
};
