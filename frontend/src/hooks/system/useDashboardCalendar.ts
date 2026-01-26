/**
 * 儀表板行事曆 Hook
 *
 * 提供儀表板頁面使用的行事曆事件資料，
 * 包含統計計算、快速篩選和時間軸展示邏輯。
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import { useMemo, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import { calendarApi, CalendarEvent } from '../../api/calendarApi';
import { defaultQueryOptions } from '../../config/queryConfig';

// 擴展 dayjs
dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);

// ============================================================================
// 型別定義
// ============================================================================

/** 快速篩選類型 */
export type DashboardQuickFilter = 'all' | 'today' | 'thisWeek' | 'upcoming' | 'overdue' | null;

/** 儀表板行事曆統計 */
export interface DashboardCalendarStats {
  total: number;
  today: number;
  thisWeek: number;
  upcoming: number;
  overdue: number;
}

/** 事件類型配置 */
export const EVENT_TYPE_CONFIG = {
  deadline: { name: '截止提醒', color: 'red', priority: 1 },
  meeting: { name: '會議安排', color: 'purple', priority: 2 },
  review: { name: '審核提醒', color: 'blue', priority: 3 },
  reminder: { name: '一般提醒', color: 'orange', priority: 4 },
  reference: { name: '參考事件', color: 'default', priority: 5 },
} as const;

/** 優先級配置 */
export const PRIORITY_CONFIG: Record<number, { name: string; color: string }> = {
  1: { name: '緊急', color: 'red' },
  2: { name: '重要', color: 'orange' },
  3: { name: '普通', color: 'blue' },
  4: { name: '低', color: 'green' },
  5: { name: '最低', color: 'default' },
};

// ============================================================================
// Query Keys
// ============================================================================

const dashboardCalendarKeys = {
  all: ['dashboardCalendar'] as const,
  events: () => [...dashboardCalendarKeys.all, 'events'] as const,
};

// ============================================================================
// Hook 實作
// ============================================================================

/**
 * 儀表板行事曆 Hook
 *
 * 整合行事曆事件資料，提供：
 * - 事件列表（可篩選）
 * - 統計數據
 * - 快速篩選機制
 */
export const useDashboardCalendar = () => {
  // 查詢行事曆事件
  const eventsQuery = useQuery({
    queryKey: dashboardCalendarKeys.events(),
    queryFn: () => calendarApi.getEvents(),
    ...defaultQueryOptions.list,
  });

  const events = eventsQuery.data ?? [];

  // 快速篩選狀態
  const [quickFilter, setQuickFilter] = useState<DashboardQuickFilter>(null);

  // 統計數據計算
  const statistics = useMemo<DashboardCalendarStats>(() => {
    const now = dayjs();
    const weekStart = now.startOf('week');
    const weekEnd = now.endOf('week');

    return {
      total: events.length,
      today: events.filter((e) =>
        dayjs(e.start_datetime).isSame(now, 'day')
      ).length,
      thisWeek: events.filter((e) => {
        const eventDate = dayjs(e.start_datetime);
        return eventDate.isSameOrAfter(weekStart, 'day') &&
               eventDate.isSameOrBefore(weekEnd, 'day');
      }).length,
      upcoming: events.filter((e) => {
        const eventDate = dayjs(e.start_datetime);
        return eventDate.isAfter(now, 'day') &&
               eventDate.isBefore(now.add(7, 'day'), 'day');
      }).length,
      overdue: events.filter((e) =>
        e.status === 'pending' && dayjs(e.start_datetime).isBefore(now, 'day')
      ).length,
    };
  }, [events]);

  // 篩選後的事件
  const filteredEvents = useMemo(() => {
    if (!quickFilter || quickFilter === 'all') {
      // 預設只顯示未來 14 天內的事件（含今天）
      const now = dayjs();
      const cutoff = now.add(14, 'day');
      return events
        .filter((e) => {
          const eventDate = dayjs(e.start_datetime);
          // 包含逾期事件 + 未來 14 天
          return e.status === 'pending' || eventDate.isSameOrAfter(now.subtract(30, 'day'), 'day');
        })
        .filter((e) => {
          const eventDate = dayjs(e.start_datetime);
          return eventDate.isSameOrBefore(cutoff, 'day') || e.status === 'pending';
        });
    }

    const now = dayjs();

    return events.filter((event) => {
      const eventDate = dayjs(event.start_datetime);

      switch (quickFilter) {
        case 'today':
          return eventDate.isSame(now, 'day');
        case 'thisWeek':
          return eventDate.isSame(now, 'week');
        case 'upcoming':
          return eventDate.isAfter(now, 'day') &&
                 eventDate.isBefore(now.add(7, 'day'), 'day');
        case 'overdue':
          return event.status === 'pending' && eventDate.isBefore(now, 'day');
        default:
          return true;
      }
    });
  }, [events, quickFilter]);

  // 排序後的事件（按時間降冪，最新在前）
  const sortedEvents = useMemo(() => {
    return [...filteredEvents].sort((a, b) => {
      // 逾期事件優先
      const aOverdue = a.status === 'pending' && dayjs(a.start_datetime).isBefore(dayjs(), 'day');
      const bOverdue = b.status === 'pending' && dayjs(b.start_datetime).isBefore(dayjs(), 'day');
      if (aOverdue && !bOverdue) return -1;
      if (!aOverdue && bOverdue) return 1;

      // 按日期排序
      return dayjs(a.start_datetime).valueOf() - dayjs(b.start_datetime).valueOf();
    });
  }, [filteredEvents]);

  // 快速篩選處理
  const handleQuickFilter = useCallback((filter: DashboardQuickFilter) => {
    setQuickFilter((prev) => (prev === filter ? null : filter));
  }, []);

  // 取得篩選標籤文字
  const getFilterLabel = useCallback((filter: DashboardQuickFilter): string => {
    const labels: Record<DashboardQuickFilter & string, string> = {
      all: '全部',
      today: '今日',
      thisWeek: '本週',
      upcoming: '即將到來',
      overdue: '已逾期',
    };
    return filter ? labels[filter] : '';
  }, []);

  return {
    // 事件資料
    events: sortedEvents,
    allEvents: events,

    // 統計
    statistics,

    // 篩選
    quickFilter,
    setQuickFilter: handleQuickFilter,
    getFilterLabel,

    // 狀態
    isLoading: eventsQuery.isLoading,
    isError: eventsQuery.isError,
    error: eventsQuery.error,

    // 操作
    refetch: eventsQuery.refetch,
  };
};

export default useDashboardCalendar;
