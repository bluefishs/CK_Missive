/**
 * useCalendarViewModel - 行事曆視圖的篩選、統計、批次操作邏輯
 *
 * 從 EnhancedCalendarView.tsx 提取，負責：
 * - 事件篩選（快速篩選 + 標準篩選）
 * - 統計數據計算
 * - 逾期事件列表
 * - 批次標記完成/取消操作
 * - 快速篩選狀態管理
 *
 * @version 1.0.0
 */

import { useState, useMemo, useCallback } from 'react';
import { App, Tag } from 'antd';
import dayjs from 'dayjs';
import { logger } from '../../services/logger';

import type {
  CalendarEvent,
  FilterState,
  QuickFilterType,
  CalendarStatisticsType,
} from './views';
import { EVENT_TYPE_CONFIG, QUICK_FILTER_LABELS } from './views';

import type { ViewMode } from './views';

interface UseCalendarViewModelOptions {
  events: CalendarEvent[];
  onEventUpdate?: (eventId: number, updates: Partial<CalendarEvent>) => Promise<void>;
  onEventDelete?: (eventId: number) => Promise<void>;
  onRefresh?: () => void;
}

export function useCalendarViewModel({
  events,
  onEventUpdate,
  onEventDelete,
  onRefresh,
}: UseCalendarViewModelOptions) {
  const { modal, notification } = App.useApp();

  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [filters, setFilters] = useState<FilterState>({
    eventTypes: [],
    priorities: [],
    statuses: [],
    dateRange: null,
    searchText: '',
  });
  const [quickFilter, setQuickFilter] = useState<QuickFilterType>(null);
  const [batchProcessing, setBatchProcessing] = useState(false);
  const [selectedEventIds, setSelectedEventIds] = useState<number[]>([]);

  // 篩選後的事件
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      // 快速篩選
      if (quickFilter) {
        const eventDate = dayjs(event.start_date);
        const today = dayjs();
        const weekStart = today.startOf('isoWeek');
        const weekEnd = today.endOf('isoWeek');
        const nextWeekStart = weekEnd.add(1, 'day').startOf('day');
        const nextWeekEnd = nextWeekStart.add(6, 'day').endOf('day');

        switch (quickFilter) {
          case 'today':
            if (!eventDate.isSame(today, 'day')) return false;
            break;
          case 'thisWeek':
            if (!(eventDate.isSameOrAfter(weekStart, 'day') && eventDate.isSameOrBefore(weekEnd, 'day'))) return false;
            break;
          case 'upcoming':
            if (!(eventDate.isSameOrAfter(nextWeekStart, 'day') && eventDate.isSameOrBefore(nextWeekEnd, 'day'))) return false;
            break;
          case 'overdue':
            if (!(event.status === 'pending' && eventDate.isBefore(today, 'day'))) return false;
            break;
        }
      }

      // 標準篩選
      if (filters.eventTypes.length > 0 && !filters.eventTypes.includes(event.event_type)) return false;
      if (filters.priorities.length > 0 && !filters.priorities.includes(event.priority)) return false;
      if (filters.statuses.length > 0 && !filters.statuses.includes(event.status)) return false;
      if (filters.dateRange) {
        const eventDate = dayjs(event.start_date);
        const [start, end] = filters.dateRange;
        if (!eventDate.isBetween(start, end, 'day', '[]')) return false;
      }
      if (filters.searchText) {
        const searchLower = filters.searchText.toLowerCase();
        if (
          !event.title.toLowerCase().includes(searchLower) &&
          !event.description?.toLowerCase().includes(searchLower)
        )
          return false;
      }
      if (filters.hasReminders !== undefined) {
        const hasReminders = event.reminder_enabled && event.reminders && event.reminders.length > 0;
        if (hasReminders !== filters.hasReminders) return false;
      }

      return true;
    });
  }, [events, filters, quickFilter]);

  // 統計數據
  const statistics = useMemo<CalendarStatisticsType>(() => {
    const now = dayjs();
    const weekStart = now.startOf('isoWeek');
    const weekEnd = now.endOf('isoWeek');
    const nextWeekStart = weekEnd.add(1, 'day').startOf('day');
    const nextWeekEnd = nextWeekStart.add(6, 'day').endOf('day');

    const total = events.length;
    const today = events.filter((e) => dayjs(e.start_date).isSame(now, 'day')).length;
    const thisWeek = events.filter((e) => {
      const eventDate = dayjs(e.start_date);
      return eventDate.isSameOrAfter(weekStart, 'day') && eventDate.isSameOrBefore(weekEnd, 'day');
    }).length;
    const upcoming = events.filter((e) => {
      const eventDate = dayjs(e.start_date);
      return eventDate.isSameOrAfter(nextWeekStart, 'day') && eventDate.isSameOrBefore(nextWeekEnd, 'day');
    }).length;
    const overdue = events.filter(
      (e) => e.status === 'pending' && dayjs(e.start_date).isBefore(now, 'day')
    ).length;

    return { total, today, thisWeek, upcoming, overdue };
  }, [events]);

  // 逾期事件列表
  const overdueEvents = useMemo(() => {
    return events.filter((e) => e.status === 'pending' && dayjs(e.start_date).isBefore(dayjs(), 'day'));
  }, [events]);

  // 快速篩選處理
  const handleQuickFilter = useCallback(
    (filterType: QuickFilterType) => {
      if (quickFilter === filterType) {
        setQuickFilter(null);
        notification.info({ title: '已清除快速篩選', duration: 1.5 });
      } else {
        setQuickFilter(filterType);
        if (filterType && filterType !== 'all') {
          setViewMode('list');
        }
        notification.success({
          title: `篩選：${QUICK_FILTER_LABELS[filterType || 'all']}`,
          duration: 1.5,
        });
      }
    },
    [quickFilter, notification]
  );

  const getQuickFilterLabel = (): string | null => {
    if (!quickFilter || quickFilter === 'all') return null;
    return QUICK_FILTER_LABELS[quickFilter] || null;
  };

  // 批次標記完成
  const handleBatchMarkComplete = useCallback(async () => {
    if (!onEventUpdate) {
      notification.warning({ title: '此功能暫不可用' });
      return;
    }

    const eventsToUpdate = quickFilter === 'overdue' ? filteredEvents : overdueEvents;
    if (eventsToUpdate.length === 0) {
      notification.info({ title: '沒有需要處理的事件' });
      return;
    }

    modal.confirm({
      title: '批次標記完成',
      content: (
        <div>
          <p>
            確定要將以下 <strong>{eventsToUpdate.length}</strong> 個逾期事件標記為「已完成」嗎？
          </p>
          <div style={{ maxHeight: 200, overflow: 'auto', marginTop: 12 }}>
            {eventsToUpdate.slice(0, 10).map((event) => (
              <div key={event.id} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Tag
                  color={EVENT_TYPE_CONFIG[event.event_type]?.color || 'default'}
                  style={{ marginRight: 8 }}
                >
                  {EVENT_TYPE_CONFIG[event.event_type]?.name || event.event_type}
                </Tag>
                <span>{event.title}</span>
                <span style={{ color: '#999', marginLeft: 8 }}>
                  ({dayjs(event.start_date).format('MM/DD')})
                </span>
              </div>
            ))}
            {eventsToUpdate.length > 10 && (
              <div style={{ padding: '8px 0', color: '#999', textAlign: 'center' }}>
                ...還有 {eventsToUpdate.length - 10} 個事件
              </div>
            )}
          </div>
        </div>
      ),
      okText: '確定標記完成',
      okType: 'primary',
      cancelText: '取消',
      onOk: async () => {
        setBatchProcessing(true);
        let successCount = 0;
        let failCount = 0;

        try {
          for (const event of eventsToUpdate) {
            try {
              await onEventUpdate(event.id, { status: 'completed' });
              successCount++;
            } catch (error) {
              failCount++;
              logger.error(`標記事件 ${event.id} 失敗:`, error);
            }
          }

          if (successCount > 0) {
            notification.success({
              title: '批次處理完成',
              description: `成功標記 ${successCount} 個事件為已完成${failCount > 0 ? `，${failCount} 個失敗` : ''}`,
            });
            setQuickFilter(null);
            onRefresh?.();
          } else {
            notification.error({
              title: '批次處理失敗',
              description: '所有事件標記失敗，請稍後再試',
            });
          }
        } finally {
          setBatchProcessing(false);
        }
      },
    });
  }, [onEventUpdate, quickFilter, filteredEvents, overdueEvents, modal, notification, onRefresh]);

  // 批次標記取消
  const handleBatchMarkCancelled = useCallback(async () => {
    if (!onEventUpdate) {
      notification.warning({ title: '此功能暫不可用' });
      return;
    }

    const eventsToUpdate = quickFilter === 'overdue' ? filteredEvents : overdueEvents;
    if (eventsToUpdate.length === 0) {
      notification.info({ title: '沒有需要處理的事件' });
      return;
    }

    modal.confirm({
      title: '批次標記取消',
      content: `確定要將 ${eventsToUpdate.length} 個逾期事件標記為「已取消」嗎？`,
      okText: '確定取消事件',
      okType: 'danger',
      cancelText: '返回',
      onOk: async () => {
        setBatchProcessing(true);
        let successCount = 0;

        try {
          for (const event of eventsToUpdate) {
            try {
              await onEventUpdate(event.id, { status: 'cancelled' });
              successCount++;
            } catch (error) {
              logger.error(`標記事件 ${event.id} 失敗:`, error);
            }
          }

          if (successCount > 0) {
            notification.success({
              title: '批次處理完成',
              description: `成功標記 ${successCount} 個事件為已取消`,
            });
            setQuickFilter(null);
            onRefresh?.();
          }
        } finally {
          setBatchProcessing(false);
        }
      },
    });
  }, [onEventUpdate, quickFilter, filteredEvents, overdueEvents, modal, notification, onRefresh]);

  // 批次選取處理
  const handleSelectEvent = useCallback((eventId: number, checked: boolean) => {
    if (checked) {
      setSelectedEventIds((prev) => [...prev, eventId]);
    } else {
      setSelectedEventIds((prev) => prev.filter((id) => id !== eventId));
    }
  }, []);

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (checked) {
        setSelectedEventIds(filteredEvents.map((e) => e.id));
      } else {
        setSelectedEventIds([]);
      }
    },
    [filteredEvents]
  );

  const handleBatchDelete = useCallback(async () => {
    if (selectedEventIds.length === 0) return;

    let successCount = 0;
    let failCount = 0;

    for (const eventId of selectedEventIds) {
      try {
        await onEventDelete?.(eventId);
        successCount++;
      } catch {
        failCount++;
      }
    }

    setSelectedEventIds([]);
    notification.success({
      title: '批次刪除完成',
      description: `成功 ${successCount} 個${failCount > 0 ? `，失敗 ${failCount} 個` : ''}`,
    });
    onRefresh?.();
  }, [selectedEventIds, onEventDelete, notification, onRefresh]);

  return {
    // State
    viewMode,
    setViewMode,
    filters,
    setFilters,
    quickFilter,
    batchProcessing,
    selectedEventIds,
    // Derived
    filteredEvents,
    statistics,
    quickFilterLabel: getQuickFilterLabel(),
    // Handlers
    handleQuickFilter,
    handleBatchMarkComplete,
    handleBatchMarkCancelled,
    handleSelectEvent,
    handleSelectAll,
    handleBatchDelete,
  };
}
