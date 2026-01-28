/**
 * 事件卡片元件
 * 用於在日曆日期格子中顯示事件摘要
 * 支援拖曳功能
 */

import React from 'react';
import { Badge, Tooltip } from 'antd';
import { GoogleOutlined, BellOutlined, HolderOutlined } from '@ant-design/icons';
import type { CalendarEvent } from './types';
import { EVENT_TYPE_CONFIG, EVENT_TYPE_COLOR_VALUES } from './constants';

export interface EventCardProps {
  event: CalendarEvent;
  truncateLength?: number;
  draggable?: boolean;
  onDragStart?: (event: CalendarEvent) => void;
}

export const EventCard: React.FC<EventCardProps> = ({
  event,
  truncateLength = 8,
  draggable = false,
  onDragStart
}) => {
  const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
  const colorKey = typeConfig?.color || 'default';
  const colorValue = EVENT_TYPE_COLOR_VALUES[colorKey] || EVENT_TYPE_COLOR_VALUES.default;

  const handleDragStart = (e: React.DragEvent) => {
    // 設定拖曳資料
    e.dataTransfer.setData('text/plain', JSON.stringify({
      eventId: event.id,
      originalDate: event.start_date
    }));
    e.dataTransfer.effectAllowed = 'move';
    onDragStart?.(event);
  };

  return (
    <li
      style={{
        marginBottom: '2px',
        cursor: draggable ? 'grab' : 'default',
        userSelect: 'none'
      }}
      draggable={draggable}
      onDragStart={handleDragStart}
    >
      <Tooltip title={`${event.title} - ${typeConfig?.name || event.event_type}${draggable ? ' (可拖曳移動)' : ''}`}>
        <Badge
          status={
            event.status === 'completed' ? 'success' :
            event.status === 'cancelled' ? 'error' : 'processing'
          }
          text={
            <span style={{ fontSize: '10px', color: colorValue }}>
              {draggable && <HolderOutlined style={{ marginRight: '2px', color: '#999' }} />}
              {event.title.substring(0, truncateLength)}
              {event.title.length > truncateLength && '...'}
            </span>
          }
        />
        {event.google_event_id && (
          <GoogleOutlined style={{ fontSize: '8px', marginLeft: '2px', color: '#1890ff' }} />
        )}
        {event.reminder_enabled && (event.reminders?.length ?? 0) > 0 && (
          <BellOutlined style={{ fontSize: '8px', marginLeft: '2px', color: '#fa8c16' }} />
        )}
      </Tooltip>
    </li>
  );
};

export default EventCard;
