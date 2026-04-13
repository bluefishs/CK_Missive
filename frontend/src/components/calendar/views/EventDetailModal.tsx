/**
 * 事件詳情模態框元件
 */

import React from 'react';
import { Modal, Space, Typography, Tag, Badge, Button, Flex } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CalendarEvent } from './types';
import { EVENT_TYPE_CONFIG, PRIORITY_CONFIG } from './constants';

const { Title, Text } = Typography;

export interface EventDetailModalProps {
  open: boolean;
  event: CalendarEvent | null;
  isMobile: boolean;
  onClose: () => void;
  onOpenReminders: () => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({
  open,
  event,
  isMobile,
  onClose,
  onOpenReminders
}) => {
  if (!event) return null;

  return (
    <Modal
      title="事件詳情"
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          關閉
        </Button>,
        <Button
          key="reminders"
          icon={<BellOutlined />}
          onClick={() => {
            onClose();
            onOpenReminders();
          }}
        >
          {isMobile ? '' : '提醒設定'}
        </Button>
      ]}
      width={isMobile ? '95%' : 600}
      style={{ maxWidth: '95vw' }}
    >
      <Space vertical size="large" style={{ width: '100%' }}>
        <div>
          <Title level={4}>{event.title}</Title>
          <Space wrap>
            <Tag color={EVENT_TYPE_CONFIG[event.event_type]?.color || 'default'}>
              {EVENT_TYPE_CONFIG[event.event_type]?.name || event.event_type}
            </Tag>
            <Tag color={PRIORITY_CONFIG[event.priority]?.color ?? 'default'}>
              {PRIORITY_CONFIG[event.priority]?.name ?? '未知'}
            </Tag>
            <Tag color={event.status === 'completed' ? 'success' : 'processing'}>
              {event.status === 'completed' ? '已完成' :
               event.status === 'cancelled' ? '已取消' : '待處理'}
            </Tag>
          </Space>
        </div>

        {event.description && (
          <div>
            <Text strong>描述：</Text>
            <div>{event.description}</div>
          </div>
        )}

        <div>
          <Text strong>時間：</Text>
          <div>{dayjs(event.start_date).format('YYYY-MM-DD HH:mm')}</div>
          {event.end_date !== event.start_date && (
            <div>至 {dayjs(event.end_date).format('YYYY-MM-DD HH:mm')}</div>
          )}
        </div>

        {event.reminders && event.reminders.length > 0 && (
          <div>
            <Text strong>提醒設定：</Text>
            <Flex vertical>
              {event.reminders.map((reminder, index) => (
                <div key={index} style={{ padding: '8px 0', borderBottom: index < (event.reminders?.length ?? 0) - 1 ? '1px solid #f0f0f0' : undefined }}>
                  <Space>
                    <Badge
                      status={
                        reminder.status === 'sent' ? 'success' :
                        reminder.status === 'failed' ? 'error' : 'processing'
                      }
                    />
                    <span>{dayjs(reminder.reminder_time).format('YYYY-MM-DD HH:mm')}</span>
                    <Tag>{reminder.notification_type === 'email' ? '郵件' : '系統通知'}</Tag>
                    {reminder.is_sent && <Text type="success">已發送</Text>}
                    {reminder.retry_count > 0 && (
                      <Text type="warning">重試 {reminder.retry_count} 次</Text>
                    )}
                  </Space>
                </div>
              ))}
            </Flex>
          </div>
        )}
      </Space>
    </Modal>
  );
};

export default EventDetailModal;
