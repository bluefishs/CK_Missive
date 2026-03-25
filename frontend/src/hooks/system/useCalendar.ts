/**
 * 行事曆 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useCallback } from 'react';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import {
  calendarApi,
  CalendarEvent,
  CalendarStats,
  DEFAULT_CATEGORIES,
} from '../../api/calendarApi';
import { queryKeys, defaultQueryOptions } from '../../config/queryConfig';

// 啟用 dayjs 週計算插件
dayjs.extend(isoWeek);

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得行事曆事件
 */
export const useCalendarEvents = () => {
  return useQuery({
    queryKey: queryKeys.calendar.events(),
    queryFn: () => calendarApi.getEvents(),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得 Google Calendar 狀態
 */
export const useGoogleCalendarStatus = () => {
  return useQuery({
    queryKey: queryKeys.calendar.googleStatus(),
    queryFn: () => calendarApi.getGoogleStatus(),
    ...defaultQueryOptions.dropdown,
  });
};

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * 更新事件
 */
export const useUpdateCalendarEvent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ eventId, updates }: { eventId: number; updates: Partial<CalendarEvent> }) =>
      calendarApi.updateEvent(eventId, updates),
    onSuccess: () => {
      // 同時 invalidate Calendar 和 Dashboard 的 queryKey
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.events() });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
    },
  });
};

/**
 * 刪除事件
 */
export const useDeleteCalendarEvent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (eventId: number) => calendarApi.deleteEvent(eventId),
    onSuccess: () => {
      // 同時 invalidate Calendar 和 Dashboard 的 queryKey
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.events() });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
    },
  });
};

/**
 * 批量同步到 Google Calendar
 */
export const useBulkSync = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => calendarApi.bulkSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.all });
    },
  });
};

// ============================================================================
// 組合 Hook
// ============================================================================

/**
 * 行事曆頁面 Hook
 *
 * 整合事件列表、Google 狀態與操作方法
 */
export const useCalendarPage = () => {
  const eventsQuery = useCalendarEvents();
  const googleStatusQuery = useGoogleCalendarStatus();
  const updateMutation = useUpdateCalendarEvent();
  const deleteMutation = useDeleteCalendarEvent();
  const syncMutation = useBulkSync();

  const queryClient = useQueryClient();
  const events = useMemo(() => eventsQuery.data ?? [], [eventsQuery.data]);

  // 計算統計資料
  const stats: CalendarStats = useMemo(() => {
    const now = dayjs();
    const todayStr = now.format('YYYY-MM-DD');
    const weekStart = now.startOf('isoWeek');
    const weekEnd = now.endOf('isoWeek');
    const monthStart = now.startOf('month');
    const monthEnd = now.endOf('month');

    const safeEvents = Array.isArray(events) ? events : [];

    const todayEvents = safeEvents.filter(
      (e) => dayjs(e.start_datetime).format('YYYY-MM-DD') === todayStr
    ).length;

    const weekEvents = safeEvents.filter((e) => {
      const eventDate = dayjs(e.start_datetime);
      // 使用 isSameOrAfter/isSameOrBefore 確保包含邊界（週一和週日）
      return eventDate.isSameOrAfter(weekStart, 'day') && eventDate.isSameOrBefore(weekEnd, 'day');
    }).length;

    const monthEvents = safeEvents.filter((e) => {
      const eventDate = dayjs(e.start_datetime);
      // 使用 isSameOrAfter/isSameOrBefore 確保包含邊界
      return eventDate.isSameOrAfter(monthStart, 'day') && eventDate.isSameOrBefore(monthEnd, 'day');
    }).length;

    // 下週事件：下週一起算 7 天（下週一 ~ 下週日），與本週不重疊
    const nextWeekStart = weekEnd.add(1, 'day').startOf('day');  // 下週一
    const nextWeekEnd = nextWeekStart.add(6, 'day').endOf('day'); // 下週日
    const upcomingEvents = safeEvents.filter((e) => {
      const eventDate = dayjs(e.start_datetime);
      return eventDate.isSameOrAfter(nextWeekStart, 'day') && eventDate.isSameOrBefore(nextWeekEnd, 'day');
    }).length;

    return {
      total_events: safeEvents.length,
      today_events: todayEvents,
      this_week_events: weekEvents,
      this_month_events: monthEvents,
      upcoming_events: upcomingEvents,
    };
  }, [events]);

  // 批次更新事件狀態（單次 API 呼叫，避免 rate limit + N 次 invalidate）
  const batchUpdateEventStatus = useCallback(async (
    eventUpdates: Array<{ eventId: number; status: 'pending' | 'completed' | 'cancelled' }>
  ): Promise<{ successCount: number; failCount: number }> => {
    // 按 status 分組（通常只有一種）
    const statusGroups = new Map<string, number[]>();
    for (const { eventId, status } of eventUpdates) {
      const ids = statusGroups.get(status) ?? [];
      ids.push(eventId);
      statusGroups.set(status, ids);
    }

    let successCount = 0;
    let failCount = 0;

    for (const [status, ids] of statusGroups) {
      try {
        const result = await calendarApi.batchUpdateStatus(
          ids,
          status as 'pending' | 'completed' | 'cancelled'
        );
        successCount += result.updated;
        failCount += result.total - result.updated;
      } catch {
        failCount += ids.length;
      }
    }

    queryClient.invalidateQueries({ queryKey: queryKeys.calendar.events() });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });

    return { successCount, failCount };
  }, [queryClient]);

  // 批次刪除事件（單次 API 呼叫）
  const batchDeleteEvents = useCallback(async (
    eventIds: number[]
  ): Promise<{ successCount: number; failCount: number }> => {
    try {
      const result = await calendarApi.batchDelete(eventIds);
      queryClient.invalidateQueries({ queryKey: queryKeys.calendar.events() });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardCalendar.all });
      return { successCount: result.deleted, failCount: result.total - result.deleted };
    } catch {
      return { successCount: 0, failCount: eventIds.length };
    }
  }, [queryClient]);

  return {
    // 事件資料
    events,
    stats,
    categories: DEFAULT_CATEGORIES,

    // Google 狀態
    googleStatus: googleStatusQuery.data ?? null,

    // 狀態
    isLoading: eventsQuery.isLoading,
    isError: eventsQuery.isError,
    error: eventsQuery.error,

    // 操作
    refetch: eventsQuery.refetch,
    updateEvent: updateMutation.mutateAsync,
    deleteEvent: deleteMutation.mutateAsync,
    bulkSync: syncMutation.mutateAsync,
    batchUpdateEventStatus,
    batchDeleteEvents,

    // 操作狀態
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isSyncing: syncMutation.isPending,
  };
};

export default useCalendarPage;
