/**
 * 事件列表視圖元件
 * 以列表形式顯示事件，支援批次選取和操作
 */

import React from 'react';
import {
  List, Space, Tag, Badge, Tooltip, Button, Checkbox, Dropdown, Popconfirm
} from 'antd';
import type { MenuProps } from 'antd';
import {
  ClockCircleOutlined, BellOutlined, GoogleOutlined, FileTextOutlined,
  SettingOutlined, DeleteOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CalendarEvent } from './types';
import { EVENT_TYPE_CONFIG, PRIORITY_CONFIG } from './constants';

export interface EventListViewProps {
  events: CalendarEvent[];
  selectedEventIds: number[];
  onSelectEvent: (eventId: number, checked: boolean) => void;
  onSelectAll: (checked: boolean) => void;
  onBatchDelete: () => void;
  onNavigateToDocument: (documentId: number) => void;
  getEventActionMenu: (event: CalendarEvent) => MenuProps['items'];
}

export const EventListView: React.FC<EventListViewProps> = ({
  events,
  selectedEventIds,
  onSelectEvent,
  onSelectAll,
  onBatchDelete,
  onNavigateToDocument,
  getEventActionMenu
}) => {
  return (
    <>
      {/* 批次操作工具列 */}
      {events.length > 0 && (
        <div style={{ marginBottom: 16, padding: '8px 12px', background: '#fafafa', borderRadius: 4 }}>
          <Space>
            <Checkbox
              indeterminate={selectedEventIds.length > 0 && selectedEventIds.length < events.length}
              checked={selectedEventIds.length === events.length && events.length > 0}
              onChange={(e) => onSelectAll(e.target.checked)}
            >
              全選 ({selectedEventIds.length}/{events.length})
            </Checkbox>
            {selectedEventIds.length > 0 && (
              <Popconfirm
                title={`確定刪除選中的 ${selectedEventIds.length} 個事件？`}
                onConfirm={onBatchDelete}
                okText="刪除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger size="small" icon={<DeleteOutlined />}>
                  批次刪除 ({selectedEventIds.length})
                </Button>
              </Popconfirm>
            )}
          </Space>
        </div>
      )}
      <List
        dataSource={events}
        renderItem={(event) => (
          <List.Item
            actions={[
              <Dropdown menu={{ items: getEventActionMenu(event) }} trigger={['click']}>
                <Button icon={<SettingOutlined />} size="small" aria-label="事件操作" />
              </Dropdown>
            ]}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
              <Checkbox
                checked={selectedEventIds.includes(event.id)}
                onChange={(e) => onSelectEvent(event.id, e.target.checked)}
                style={{ marginRight: 12, marginTop: 4 }}
              />
              <List.Item.Meta
                avatar={
                  <Badge
                    status={
                      event.status === 'completed' ? 'success' :
                      event.status === 'cancelled' ? 'error' : 'processing'
                    }
                    text=""
                  />
                }
                title={
                  <Space>
                    {EVENT_TYPE_CONFIG[event.event_type]?.icon}
                    <span>{event.title}</span>
                    <Tag color={EVENT_TYPE_CONFIG[event.event_type]?.color || 'default'}>
                      {EVENT_TYPE_CONFIG[event.event_type]?.name || event.event_type}
                    </Tag>
                    <Tag color={PRIORITY_CONFIG[event.priority]?.color ?? 'default'}>
                      {PRIORITY_CONFIG[event.priority]?.name ?? '未知'}
                    </Tag>
                    {event.reminder_enabled && (event.reminders?.length ?? 0) > 0 && (
                      <Tooltip title={`${event.reminders?.length ?? 0} 個提醒`}>
                        <BellOutlined style={{ color: '#fa8c16' }} />
                      </Tooltip>
                    )}
                    {event.google_event_id && (
                      <Tooltip title="已同步至 Google Calendar">
                        <GoogleOutlined style={{ color: '#1890ff' }} />
                      </Tooltip>
                    )}
                  </Space>
                }
                description={
                  <Space direction="vertical" size="small">
                    <div>{event.description}</div>
                    <Space>
                      <ClockCircleOutlined />
                      <span>{dayjs(event.start_date).format('YYYY-MM-DD HH:mm')}</span>
                      {event.end_date !== event.start_date && (
                        <span> ~ {dayjs(event.end_date).format('YYYY-MM-DD HH:mm')}</span>
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
                }
              />
            </div>
          </List.Item>
        )}
      />
    </>
  );
};

export default EventListView;
