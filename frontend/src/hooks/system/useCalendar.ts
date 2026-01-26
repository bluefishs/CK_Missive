/**
 * 行事曆 React Query Hooks
 *
 * 整合 queryConfig 統一快取策略
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import {
  calendarApi,
  CalendarEvent,
  CalendarStats,
  GoogleCalendarStatus,
  DEFAULT_CATEGORIES,
  EventCategory,
} from '../../api/calendarApi';
import { defaultQueryOptions } from '../../config/queryConfig';

// 啟用 dayjs 週計算插件
dayjs.extend(isoWeek);

// ============================================================================
// 查詢鍵
// ============================================================================

const calendarKeys = {
  all: ['calendar'] as const,
  events: () => [...calendarKeys.all, 'events'] as const,
  googleStatus: () => [...calendarKeys.all, 'googleStatus'] as const,
};

// ============================================================================
// 查詢 Hooks
// ============================================================================

/**
 * 取得行事曆事件
 */
export const useCalendarEvents = () => {
  return useQuery({
    queryKey: calendarKeys.events(),
    queryFn: () => calendarApi.getEvents(),
    ...defaultQueryOptions.list,
  });
};

/**
 * 取得 Google Calendar 狀態
 */
export const useGoogleCalendarStatus = () => {
  return useQuery({
    queryKey: calendarKeys.googleStatus(),
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
      queryClient.invalidateQueries({ queryKey: calendarKeys.events() });
      queryClient.invalidateQueries({ queryKey: ['dashboardCalendar'] });
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
      queryClient.invalidateQueries({ queryKey: calendarKeys.events() });
      queryClient.invalidateQueries({ queryKey: ['dashboardCalendar'] });
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
      queryClient.invalidateQueries({ queryKey: calendarKeys.all });
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

  const events = eventsQuery.data ?? [];

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
      return eventDate.isAfter(weekStart) && eventDate.isBefore(weekEnd);
    }).length;

    const monthEvents = safeEvents.filter((e) => {
      const eventDate = dayjs(e.start_datetime);
      return eventDate.isAfter(monthStart) && eventDate.isBefore(monthEnd);
    }).length;

    const upcomingEvents = safeEvents.filter((e) =>
      dayjs(e.start_datetime).isAfter(now)
    ).length;

    return {
      total_events: safeEvents.length,
      today_events: todayEvents,
      this_week_events: weekEvents,
      this_month_events: monthEvents,
      upcoming_events: upcomingEvents,
    };
  }, [events]);

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

    // 操作狀態
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isSyncing: syncMutation.isPending,
  };
};

export default useCalendarPage;
