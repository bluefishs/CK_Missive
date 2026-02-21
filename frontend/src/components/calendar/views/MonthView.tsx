/**
 * 月視圖元件
 * 顯示 Ant Design Calendar 並渲染事件
 * 支援事件拖曳移動日期功能
 */

import React, { useState, useCallback } from 'react';
import { Calendar, App } from 'antd';
import type { CalendarProps } from 'antd';
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from './types';
import { EventCard } from './EventCard';
import { logger } from '../../../services/logger';

export interface MonthViewProps {
  events: CalendarEvent[];
  onDateSelect?: (date: Dayjs) => void;
  onEventDrop?: (eventId: number, newDate: Dayjs, originalDate: string) => Promise<void>;
  enableDragDrop?: boolean;
}

export const MonthView: React.FC<MonthViewProps> = ({
  events,
  onDateSelect,
  onEventDrop,
  enableDragDrop = true
}) => {
  const { notification } = App.useApp();
  const [dragOverDate, setDragOverDate] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // 獲取指定日期的事件
  const getEventsForDate = (date: Dayjs) => {
    return events.filter(event => {
      const eventStart = date.isSame(event.start_date, 'day') ||
                        date.isAfter(event.start_date, 'day');
      const eventEnd = date.isSame(event.end_date, 'day') ||
                      date.isBefore(event.end_date, 'day');
      return eventStart && eventEnd;
    });
  };

  // 拖曳開始
  const handleDragStart = useCallback(() => {
    setIsDragging(true);
  }, []);

  // 拖曳進入日期格子
  const handleDragOver = useCallback((e: React.DragEvent, dateStr: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverDate(dateStr);
  }, []);

  // 拖曳離開日期格子
  const handleDragLeave = useCallback(() => {
    setDragOverDate(null);
  }, []);

  // 放下事件
  const handleDrop = useCallback(async (e: React.DragEvent, targetDate: Dayjs) => {
    e.preventDefault();
    setDragOverDate(null);
    setIsDragging(false);

    if (!onEventDrop) {
      notification.warning({ message: '拖曳功能暫不可用' });
      return;
    }

    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
      const { eventId, originalDate } = data;

      // 檢查是否移動到同一天
      if (targetDate.isSame(originalDate, 'day')) {
        return;
      }

      await onEventDrop(eventId, targetDate, originalDate);
      notification.success({
        message: '事件已移動',
        description: `事件已移至 ${targetDate.format('YYYY-MM-DD')}`
      });
    } catch (error) {
      logger.error('拖曳失敗:', error);
      notification.error({
        message: '移動失敗',
        description: '無法移動事件，請稍後再試'
      });
    }
  }, [onEventDrop, notification]);

  // 日期格子渲染
  const dateCellRender = (value: Dayjs) => {
    const eventsForDate = getEventsForDate(value);
    const dateStr = value.format('YYYY-MM-DD');
    const isDropTarget = dragOverDate === dateStr;

    return (
      <div
        style={{
          minHeight: '60px',
          padding: '2px',
          backgroundColor: isDropTarget ? '#e6f7ff' : 'transparent',
          border: isDropTarget ? '2px dashed #1890ff' : '2px solid transparent',
          borderRadius: '4px',
          transition: 'all 0.2s ease'
        }}
        onDragOver={(e) => handleDragOver(e, dateStr)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, value)}
      >
        {eventsForDate.length === 0 ? (
          isDragging && (
            <div style={{
              color: '#999',
              fontSize: '10px',
              textAlign: 'center',
              paddingTop: '20px'
            }}>
              拖曳至此
            </div>
          )
        ) : (
          <ul className="events" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {eventsForDate.slice(0, 3).map((event) => (
              <EventCard
                key={event.id}
                event={event}
                draggable={enableDragDrop && !!onEventDrop}
                onDragStart={handleDragStart}
              />
            ))}
            {eventsForDate.length > 3 && (
              <li style={{ fontSize: '10px', color: '#666' }}>
                +{eventsForDate.length - 3} 更多
              </li>
            )}
          </ul>
        )}
      </div>
    );
  };

  const cellRender: CalendarProps<Dayjs>['cellRender'] = (current, info) => {
    if (info.type === 'date') return dateCellRender(current);
    return info.originNode;
  };

  return (
    <Calendar
      cellRender={cellRender}
      onSelect={(date) => {
        onDateSelect?.(date);
      }}
    />
  );
};

export default MonthView;
