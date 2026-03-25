/**
 * 增強型行事曆視圖組件
 * 提供多種視圖模式、事件篩選、提醒管理等功能
 *
 * 重構版本：拆分為多個子元件
 * - useCalendarViewModel.ts - 篩選/統計/批次操作邏輯
 *
 * @version 3.0.0
 */

import React, { useState, useCallback } from 'react';
import { Card, Space, Empty, App, Grid } from 'antd';
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
} from './views';

import type { CalendarEvent, EventReminder } from './views';
import { useCalendarViewModel } from './useCalendarViewModel';

// 擴展 dayjs 以支援 isBetween
dayjs.extend(isBetween);

const { useBreakpoint } = Grid;

interface EnhancedCalendarViewProps {
  events?: CalendarEvent[];
  loading?: boolean;
  onEventUpdate?: (eventId: number, updates: Partial<CalendarEvent>) => Promise<void>;
  onEventDelete?: (eventId: number) => Promise<void>;
  onBatchUpdateStatus?: (updates: Array<{ eventId: number; status: 'pending' | 'completed' | 'cancelled' }>) => Promise<{ successCount: number; failCount: number }>;
  onBatchDelete?: (eventIds: number[]) => Promise<{ successCount: number; failCount: number }>;
  onReminderUpdate?: (eventId: number, reminders: EventReminder[]) => Promise<void>;
  onDateSelect?: (date: Dayjs) => void;
  onRefresh?: () => void;
}

export const EnhancedCalendarView: React.FC<EnhancedCalendarViewProps> = ({
  events = [],
  loading = false,
  onEventUpdate,
  onEventDelete,
  onBatchUpdateStatus,
  onBatchDelete,
  onReminderUpdate: _onReminderUpdate,
  onDateSelect,
  onRefresh
}) => {
  const navigate = useNavigate();
  const { modal, notification } = App.useApp();

  // 響應式斷點
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  // 視圖模型（篩選、統計、批次操作）
  const vm = useCalendarViewModel({ events, onEventUpdate, onEventDelete, onBatchUpdateStatus, onBatchDelete, onRefresh });

  // 模態框狀態
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [, setSelectedDate] = useState<Dayjs>(dayjs());
  const [showEventModal, setShowEventModal] = useState(false);
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [showEventFormModal, setShowEventFormModal] = useState(false);
  const [eventFormMode, setEventFormMode] = useState<'create' | 'edit'>('create');

  // 事件拖曳處理（變更日期）
  const handleEventDrop = useCallback(async (eventId: number, newDate: Dayjs, originalDate: string) => {
    if (!onEventUpdate) {
      notification.warning({ title: '更新功能暫不可用' });
      return;
    }

    const originalDayjs = dayjs(originalDate);
    const daysDiff = newDate.diff(originalDayjs, 'day');
    const event = events.find(e => e.id === eventId);
    if (!event) {
      notification.error({ title: '找不到事件' });
      return;
    }

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
          title: `事件已標記為${newStatus === 'completed' ? '完成' : '待處理'}`
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
            notification.success({ title: '事件已刪除' });
          }
        });
      }
    }
  ];

  // 導航到公文詳情
  const handleNavigateToDocument = (documentId: number) => {
    navigate(`/documents/${documentId}`);
  };

  return (
    <div>
      <Space vertical size={isMobile ? 'middle' : 'large'} style={{ width: '100%' }}>
        {/* 工具列 */}
        <CalendarHeader
          viewMode={vm.viewMode}
          isMobile={isMobile}
          onViewModeChange={vm.setViewMode}
          onAddEvent={() => {
            setSelectedEvent(null);
            setEventFormMode('create');
            setShowEventFormModal(true);
          }}
          onOpenFilter={() => setShowFilterModal(true)}
        />

        {/* 統計數據 */}
        <CalendarStatistics
          statistics={vm.statistics}
          filteredCount={vm.filteredEvents.length}
          quickFilter={vm.quickFilter}
          quickFilterLabel={vm.quickFilterLabel}
          isMobile={isMobile}
          batchProcessing={vm.batchProcessing}
          onQuickFilter={vm.handleQuickFilter}
          onBatchMarkComplete={vm.handleBatchMarkComplete}
          onBatchMarkCancelled={vm.handleBatchMarkCancelled}
        />

        {/* 主要內容區域 */}
        <Card loading={loading}>
          {vm.viewMode === 'month' && (
            <MonthView
              events={vm.filteredEvents}
              onDateSelect={(date) => {
                setSelectedDate(date);
                onDateSelect?.(date);
              }}
              onEventDrop={handleEventDrop}
              enableDragDrop={!isMobile && !!onEventUpdate}
            />
          )}

          {vm.viewMode === 'list' && (
            vm.filteredEvents.length > 0 ? (
              <EventListView
                events={vm.filteredEvents}
                selectedEventIds={vm.selectedEventIds}
                onSelectEvent={vm.handleSelectEvent}
                onSelectAll={vm.handleSelectAll}
                onBatchDelete={vm.handleBatchDelete}
                onNavigateToDocument={handleNavigateToDocument}
                getEventActionMenu={getEventActionMenu}
              />
            ) : (
              <Empty description="沒有符合條件的事件" />
            )
          )}

          {vm.viewMode === 'timeline' && (
            vm.filteredEvents.length > 0 ? (
              <TimelineView
                events={vm.filteredEvents}
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
          filters={vm.filters}
          isMobile={isMobile}
          onClose={() => setShowFilterModal(false)}
          onFiltersChange={vm.setFilters}
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
            onRefresh?.();
          }}
        />

        {/* 提醒設定模態框 */}
        <ReminderSettingsModal
          visible={showReminderModal}
          event={selectedEvent}
          onClose={() => setShowReminderModal(false)}
          onSuccess={() => {
            onRefresh?.();
          }}
        />
      </Space>
    </div>
  );
};

export default EnhancedCalendarView;
