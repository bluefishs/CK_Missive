/**
 * 時間軸視圖元件
 * 以時間軸形式顯示事件（降冪排序：最新事件在上）
 */

import React from 'react';
import { Timeline, Card, Space, Typography, Tag, Button } from 'antd';
import { ClockCircleOutlined, BellOutlined, FileTextOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CalendarEvent } from './types';
import { EVENT_TYPE_CONFIG, PRIORITY_CONFIG } from './constants';

const { Text } = Typography;

export interface TimelineViewProps {
  events: CalendarEvent[];
  onNavigateToDocument: (documentId: number) => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  events,
  onNavigateToDocument
}) => {
  // 降冪排序：最新事件在上
  const sortedEvents = [...events].sort((a, b) =>
    dayjs(b.start_date).valueOf() - dayjs(a.start_date).valueOf()
  );

  return (
    <Timeline
      items={sortedEvents.map(event => ({
        color: EVENT_TYPE_CONFIG[event.event_type]?.color || 'default',
        dot: EVENT_TYPE_CONFIG[event.event_type]?.icon,
        children: (
          <Card size="small" style={{ marginBottom: 8 }}>
            <Space direction="vertical" size="small">
              <Space>
                <Text strong>{event.title}</Text>
                <Tag color={EVENT_TYPE_CONFIG[event.event_type]?.color || 'default'}>
                  {EVENT_TYPE_CONFIG[event.event_type]?.name || event.event_type}
                </Tag>
                <Tag color={PRIORITY_CONFIG[event.priority]?.color ?? 'default'}>
                  {PRIORITY_CONFIG[event.priority]?.name ?? '未知'}
                </Tag>
              </Space>
              <Text type="secondary">{event.description}</Text>
              <Space>
                <ClockCircleOutlined />
                <Text>{dayjs(event.start_date).format('YYYY-MM-DD HH:mm')}</Text>
                {event.reminder_enabled && (event.reminders?.length ?? 0) > 0 && (
                  <>
                    <BellOutlined style={{ color: '#fa8c16' }} />
                    <Text>{event.reminders?.length ?? 0} 個提醒</Text>
                  </>
                )}
              </Space>
              {event.document_id && (
                <Button
                  type="link"
                  size="small"
                  icon={<FileTextOutlined />}
                  onClick={() => onNavigateToDocument(event.document_id!)}
                  style={{ padding: 0 }}
                >
                  查看關聯公文
                </Button>
              )}
            </Space>
          </Card>
        )
      }))}
    />
  );
};

export default TimelineView;
