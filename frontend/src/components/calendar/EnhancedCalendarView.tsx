/**
 * 增強型行事曆視圖組件
 * 提供多種視圖模式、事件篩選、提醒管理等功能
 *
 * 重構版本：拆分為多個子元件
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Card, Space, Empty, App, Grid, Tag } from 'antd';
import type { MenuProps } from 'antd';
import {
  CheckCircleOutlined, EyeOutlined, EditOutlined, DeleteOutlined, BellOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { logger } from '../../services/logger';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
import { EventFormModal } from './EventFormModal';
import { ReminderSettingsModal } from './ReminderSettingsModal';

// 子元件匯入
import {
  CalendarHeader,
  CalendarStatistics,
  CalendarFilters,
  MonthView,
  EventListView,
  TimelineView,
  EventDetailModal,
  EVENT_TYPE_CONFIG,
  QUICK_FILTER_LABELS
} from './views';

import type {
  CalendarEvent,
  FilterState,
  QuickFilterType,
  ViewMode,
  CalendarStatisticsType,
  EventReminder
} from './views';

// 擴展 dayjs 以支援 isBetween
dayjs.extend(isBetween);

const { useBreakpoint } = Grid;

interface EnhancedCalendarViewProps {
  events?: CalendarEvent[];
  loading?: boolean;
  onEventUpdate?: (eventId: number, updates: Partial<CalendarEvent>) => Promise<void>;
  onEventDelete?: (eventId: number) => Promise<void>;
  onReminderUpdate?: (eventId: number, reminders: EventReminder[]) => Promise<void>;
  onDateSelect?: (date: Dayjs) => void;
  onRefresh?: () => void;
}

export const EnhancedCalendarView: React.FC<EnhancedCalendarViewProps> = ({
  events = [],
  loading = false,
  onEventUpdate,
  onEventDelete,
  onReminderUpdate: _onReminderUpdate,
  onDateSelect,
  onRefresh
}) => {
  const navigate = useNavigate();
  const { modal, notification } = App.useApp();

  // 響應式斷點
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  // 狀態管理
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [, setSelectedDate] = useState<Dayjs>(dayjs());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [selectedEventIds, setSelectedEventIds] = useState<number[]>([]);
  const [showEventModal, setShowEventModal] = useState(false);
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [showEventFormModal, setShowEventFormModal] = useState(false);
  const [eventFormMode, setEventFormMode] = useState<'create' | 'edit'>('create');

  const [filters, setFilters] = useState<FilterState>({
    eventTypes: [],
    priorities: [],
    statuses: [],
    dateRange: null,
    searchText: ''
  });

  const [quickFilter, setQuickFilter] = useState<QuickFilterType>(null);
  const [batchProcessing, setBatchProcessing] = useState(false);

  // 篩選後的事件
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      // 快速篩選
      if (quickFilter) {
        const eventDate = dayjs(event.start_date);
        const today = dayjs();

        // 使用 ISO Week（週一開始）確保一致性
        const weekStart = today.startOf('isoWeek');
        const weekEnd = today.endOf('isoWeek');
        // 下週事件：下週一起算 7 天（下週一 ~ 下週日），與本週不重疊
        const nextWeekStart = weekEnd.add(1, 'day').startOf('day');  // 下週一
        const nextWeekEnd = nextWeekStart.add(6, 'day').endOf('day'); // 下週日

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
      if (filters.eventTypes.length > 0 && !filters.eventTypes.includes(event.event_type)) {
        return false;
      }
      if (filters.priorities.length > 0 && !filters.priorities.includes(event.priority)) {
        return false;
      }
      if (filters.statuses.length > 0 && !filters.statuses.includes(event.status)) {
        return false;
      }
      if (filters.dateRange) {
        const eventDate = dayjs(event.start_date);
        const [start, end] = filters.dateRange;
        if (!eventDate.isBetween(start, end, 'day', '[]')) {
          return false;
        }
      }
      if (filters.searchText) {
        const searchLower = filters.searchText.toLowerCase();
        if (!event.title.toLowerCase().includes(searchLower) &&
            !event.description?.toLowerCase().includes(searchLower)) {
          return false;
        }
      }
      if (filters.hasReminders !== undefined) {
        const hasReminders = event.reminder_enabled && event.reminders && event.reminders.length > 0;
        if (hasReminders !== filters.hasReminders) {
          return false;
        }
      }

      return true;
    });
  }, [events, filters, quickFilter]);

  // 統計數據
  const statistics = useMemo<CalendarStatisticsType>(() => {
    const now = dayjs();
    // 使用 ISO Week（週一開始）確保一致性
    const weekStart = now.startOf('isoWeek');
    const weekEnd = now.endOf('isoWeek');
    // 下週事件：下週一起算 7 天（下週一 ~ 下週日），與本週不重疊
    const nextWeekStart = weekEnd.add(1, 'day').startOf('day');  // 下週一
    const nextWeekEnd = nextWeekStart.add(6, 'day').endOf('day'); // 下週日

    const total = events.length;
    const today = events.filter(e => dayjs(e.start_date).isSame(now, 'day')).length;
    const thisWeek = events.filter(e => {
      const eventDate = dayjs(e.start_date);
      return eventDate.isSameOrAfter(weekStart, 'day') && eventDate.isSameOrBefore(weekEnd, 'day');
    }).length;
    const upcoming = events.filter(e => {
      const eventDate = dayjs(e.start_date);
      return eventDate.isSameOrAfter(nextWeekStart, 'day') && eventDate.isSameOrBefore(nextWeekEnd, 'day');
    }).length;
    const overdue = events.filter(e =>
      e.status === 'pending' && dayjs(e.start_date).isBefore(now, 'day')
    ).length;

    return { total, today, thisWeek, upcoming, overdue };
  }, [events]);

  // 逾期事件列表
  const overdueEvents = useMemo(() => {
    return events.filter(e =>
      e.status === 'pending' && dayjs(e.start_date).isBefore(dayjs(), 'day')
    );
  }, [events]);

  // 快速篩選處理
  const handleQuickFilter = (filterType: QuickFilterType) => {
    if (quickFilter === filterType) {
      setQuickFilter(null);
      notification.info({ message: '已清除快速篩選', duration: 1.5 });
    } else {
      setQuickFilter(filterType);
      if (filterType && filterType !== 'all') {
        setViewMode('list');
      }
      notification.success({
        message: `篩選：${QUICK_FILTER_LABELS[filterType || 'all']}`,
        duration: 1.5
      });
    }
  };

  const getQuickFilterLabel = (): string | null => {
    if (!quickFilter || quickFilter === 'all') return null;
    return QUICK_FILTER_LABELS[quickFilter] || null;
  };

  // 批次標記完成
  const handleBatchMarkComplete = async () => {
    if (!onEventUpdate) {
      notification.warning({ message: '此功能暫不可用' });
      return;
    }

    const eventsToUpdate = quickFilter === 'overdue' ? filteredEvents : overdueEvents;
    if (eventsToUpdate.length === 0) {
      notification.info({ message: '沒有需要處理的事件' });
      return;
    }

    modal.confirm({
      title: '批次標記完成',
      content: (
        <div>
          <p>確定要將以下 <strong>{eventsToUpdate.length}</strong> 個逾期事件標記為「已完成」嗎？</p>
          <div style={{ maxHeight: 200, overflow: 'auto', marginTop: 12 }}>
            {eventsToUpdate.slice(0, 10).map(event => (
              <div key={event.id} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Tag color={EVENT_TYPE_CONFIG[event.event_type]?.color || 'default'} style={{ marginRight: 8 }}>
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
              message: '批次處理完成',
              description: `成功標記 ${successCount} 個事件為已完成${failCount > 0 ? `，${failCount} 個失敗` : ''}`
            });
            setQuickFilter(null);
            onRefresh?.();
          } else {
            notification.error({
              message: '批次處理失敗',
              description: '所有事件標記失敗，請稍後再試'
            });
          }
        } finally {
          setBatchProcessing(false);
        }
      }
    });
  };

  // 批次標記取消
  const handleBatchMarkCancelled = async () => {
    if (!onEventUpdate) {
      notification.warning({ message: '此功能暫不可用' });
      return;
    }

    const eventsToUpdate = quickFilter === 'overdue' ? filteredEvents : overdueEvents;
    if (eventsToUpdate.length === 0) {
      notification.info({ message: '沒有需要處理的事件' });
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
              message: '批次處理完成',
              description: `成功標記 ${successCount} 個事件為已取消`
            });
            setQuickFilter(null);
            onRefresh?.();
          }
        } finally {
          setBatchProcessing(false);
        }
      }
    });
  };

  // 事件拖曳處理（變更日期）
  const handleEventDrop = useCallback(async (eventId: number, newDate: Dayjs, originalDate: string) => {
    if (!onEventUpdate) {
      notification.warning({ message: '更新功能暫不可用' });
      return;
    }

    // 計算日期差異，保持時間部分不變
    const originalDayjs = dayjs(originalDate);
    const daysDiff = newDate.diff(originalDayjs, 'day');

    // 找到原事件以獲取完整資料
    const event = events.find(e => e.id === eventId);
    if (!event) {
      notification.error({ message: '找不到事件' });
      return;
    }

    // 計算新的開始和結束日期（保持原時間）
    const newStartDate = dayjs(event.start_date).add(daysDiff, 'day');
    const newEndDate = event.end_date
      ? dayjs(event.end_date).add(daysDiff, 'day')
      : newStartDate;

    try {
      await onEventUpdate(eventId, {
        start_date: newStartDate.toISOString(),
        end_date: newEndDate.toISOString()
      });
      onRefresh?.();
    } catch (error) {
      logger.error('拖曳更新失敗:', error);
      throw error;
    }
  }, [events, onEventUpdate, onRefresh, notification]);

  // 事件操作選單
  const getEventActionMenu = (event: CalendarEvent): MenuProps['items'] => [
    {
      key: 'view',
      label: '檢視詳情',
      icon: <EyeOutlined />,
      onClick: () => {
        setSelectedEvent(event);
        setShowEventModal(true);
      }
    },
    {
      key: 'edit',
      label: '編輯事件',
      icon: <EditOutlined />,
      onClick: () => {
        setSelectedEvent(event);
        setEventFormMode('edit');
        setShowEventFormModal(true);
      }
    },
    {
      key: 'reminders',
      label: '提醒設定',
      icon: <BellOutlined />,
      onClick: () => {
        setSelectedEvent(event);
        setShowReminderModal(true);
      }
    },
    { type: 'divider' },
    {
      key: 'complete',
      label: event.status === 'completed' ? '標記為待處理' : '標記為完成',
      icon: <CheckCircleOutlined />,
      onClick: async () => {
        const newStatus = event.status === 'completed' ? 'pending' : 'completed';
        await onEventUpdate?.(event.id, { status: newStatus });
        notification.success({
          message: `事件已標記為${newStatus === 'completed' ? '完成' : '待處理'}`
        });
      }
    },
    {
      key: 'delete',
      label: '刪除事件',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {
        modal.confirm({
          title: '確認刪除',
          content: `確定要刪除事件「${event.title}」嗎？`,
          onOk: async () => {
            await onEventDelete?.(event.id);
            notification.success({ message: '事件已刪除' });
          }
        });
      }
    }
  ];

  // 導航到公文詳情
  const handleNavigateToDocument = (documentId: number) => {
    navigate(`/documents/${documentId}`);
  };

  // 批次選取處理
  const handleSelectEvent = (eventId: number, checked: boolean) => {
    if (checked) {
      setSelectedEventIds(prev => [...prev, eventId]);
    } else {
      setSelectedEventIds(prev => prev.filter(id => id !== eventId));
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedEventIds(filteredEvents.map(e => e.id));
    } else {
      setSelectedEventIds([]);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedEventIds.length === 0) return;

    let successCount = 0;
    let failCount = 0;

    for (const eventId of selectedEventIds) {
      try {
        await onEventDelete?.(eventId);
        successCount++;
      } catch (error) {
        failCount++;
      }
    }

    setSelectedEventIds([]);
    notification.success({
      message: '批次刪除完成',
      description: `成功 ${successCount} 個${failCount > 0 ? `，失敗 ${failCount} 個` : ''}`
    });
    onRefresh?.();
  };

  return (
    <div>
      <Space direction="vertical" size={isMobile ? 'middle' : 'large'} style={{ width: '100%' }}>
        {/* 工具列 */}
        <CalendarHeader
          viewMode={viewMode}
          isMobile={isMobile}
          onViewModeChange={setViewMode}
          onAddEvent={() => {
            setSelectedEvent(null);
            setEventFormMode('create');
            setShowEventFormModal(true);
          }}
          onOpenFilter={() => setShowFilterModal(true)}
        />

        {/* 統計數據 */}
        <CalendarStatistics
          statistics={statistics}
          filteredCount={filteredEvents.length}
          quickFilter={quickFilter}
          quickFilterLabel={getQuickFilterLabel()}
          isMobile={isMobile}
          batchProcessing={batchProcessing}
          onQuickFilter={handleQuickFilter}
          onBatchMarkComplete={handleBatchMarkComplete}
          onBatchMarkCancelled={handleBatchMarkCancelled}
        />

        {/* 主要內容區域 */}
        <Card loading={loading}>
          {viewMode === 'month' && (
            <MonthView
              events={filteredEvents}
              onDateSelect={(date) => {
                setSelectedDate(date);
                onDateSelect?.(date);
              }}
              onEventDrop={handleEventDrop}
              enableDragDrop={!isMobile && !!onEventUpdate}
            />
          )}

          {viewMode === 'list' && (
            filteredEvents.length > 0 ? (
              <EventListView
                events={filteredEvents}
                selectedEventIds={selectedEventIds}
                onSelectEvent={handleSelectEvent}
                onSelectAll={handleSelectAll}
                onBatchDelete={handleBatchDelete}
                onNavigateToDocument={handleNavigateToDocument}
                getEventActionMenu={getEventActionMenu}
              />
            ) : (
              <Empty description="沒有符合條件的事件" />
            )
          )}

          {viewMode === 'timeline' && (
            filteredEvents.length > 0 ? (
              <TimelineView
                events={filteredEvents}
                onNavigateToDocument={handleNavigateToDocument}
              />
            ) : (
              <Empty description="沒有符合條件的事件" />
            )
          )}
        </Card>

        {/* 篩選面板 */}
        <CalendarFilters
          visible={showFilterModal}
          filters={filters}
          isMobile={isMobile}
          onClose={() => setShowFilterModal(false)}
          onFiltersChange={setFilters}
        />

        {/* 事件詳情模態框 */}
        <EventDetailModal
          visible={showEventModal}
          event={selectedEvent}
          isMobile={isMobile}
          onClose={() => setShowEventModal(false)}
          onOpenReminders={() => setShowReminderModal(true)}
        />

        {/* 事件表單模態框 */}
        <EventFormModal
          visible={showEventFormModal}
          mode={eventFormMode}
          event={selectedEvent ? { ...selectedEvent, all_day: selectedEvent.all_day ?? true } : null}
          onClose={() => {
            setShowEventFormModal(false);
            setSelectedEvent(null);
          }}
          onSuccess={() => {
            setShowEventFormModal(false);
            setSelectedEvent(null);
            // 觸發資料刷新
            onRefresh?.();
          }}
        />

        {/* 提醒設定模態框 */}
        <ReminderSettingsModal
          visible={showReminderModal}
          event={selectedEvent}
          onClose={() => setShowReminderModal(false)}
          onSuccess={() => {
            // 觸發資料刷新
            onRefresh?.();
          }}
        />
      </Space>
    </div>
  );
};

export default EnhancedCalendarView;
