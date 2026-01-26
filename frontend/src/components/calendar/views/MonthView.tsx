/**
 * 月視圖元件
 * 顯示 Ant Design Calendar 並渲染事件
 */

import React from 'react';
import { Calendar } from 'antd';
import type { CalendarProps } from 'antd';
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from './types';
import { EventCard } from './EventCard';

export interface MonthViewProps {
  events: CalendarEvent[];
  onDateSelect?: (date: Dayjs) => void;
}

export const MonthView: React.FC<MonthViewProps> = ({
  events,
  onDateSelect
}) => {
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

  // 日期格子渲染
  const dateCellRender = (value: Dayjs) => {
    const eventsForDate = getEventsForDate(value);
    if (eventsForDate.length === 0) return null;

    return (
      <ul className="events" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {eventsForDate.slice(0, 3).map((event) => (
          <EventCard key={event.id} event={event} />
        ))}
        {eventsForDate.length > 3 && (
          <li style={{ fontSize: '10px', color: '#666' }}>
            +{eventsForDate.length - 3} 更多
          </li>
        )}
      </ul>
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
