/**
 * 增強型行事曆視圖組件
 * 提供多種視圖模式、事件篩選、提醒管理等功能
 */

import React, { useState, useMemo } from 'react';
import {
  Card, Typography, Calendar, Badge, List, Modal, Tag, Button, Space, Select,
  DatePicker, Row, Col, Tooltip, Dropdown, Input, Form,
  notification, Timeline, Statistic, Empty, Radio
} from 'antd';
import {
  GoogleOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  FilterOutlined, BellOutlined, ClockCircleOutlined, EditOutlined, DeleteOutlined,
  EyeOutlined, PlusOutlined, SettingOutlined, CalendarOutlined, UnorderedListOutlined,
  TableOutlined, AlertOutlined
} from '@ant-design/icons';
import type { CalendarProps, MenuProps } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
import { EventFormModal } from './EventFormModal';
import { ReminderSettingsModal } from './ReminderSettingsModal';

// 擴展 dayjs 以支援 isBetween
dayjs.extend(isBetween);

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Search } = Input;

interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  all_day?: boolean;
  event_type: 'deadline' | 'meeting' | 'review' | 'reminder' | 'reference';
  priority: number;
  status: 'pending' | 'completed' | 'cancelled';
  document_id?: number;
  assigned_user_id?: number;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
  reminder_enabled: boolean;
  reminders?: EventReminder[];
}

interface EventReminder {
  id: number;
  reminder_time: string;
  notification_type: 'email' | 'system';
  status: 'pending' | 'sent' | 'failed';
  is_sent: boolean;
  retry_count: number;
}

interface FilterState {
  eventTypes: string[];
  priorities: number[];
  statuses: string[];
  dateRange: [Dayjs, Dayjs] | null;
  searchText: string;
  assignedUserId?: number;
  hasReminders?: boolean;
}

type ViewMode = 'month' | 'week' | 'list' | 'timeline';

const EVENT_TYPE_CONFIG = {
  deadline: { name: '截止提醒', color: 'red', icon: <AlertOutlined /> },
  meeting: { name: '會議安排', color: 'purple', icon: <CalendarOutlined /> },
  review: { name: '審核提醒', color: 'blue', icon: <EyeOutlined /> },
  reminder: { name: '一般提醒', color: 'orange', icon: <BellOutlined /> },
  reference: { name: '參考事件', color: 'default', icon: <UnorderedListOutlined /> }
};

const PRIORITY_CONFIG: Record<number, { name: string; color: string }> = {
  1: { name: '緊急', color: 'red' },
  2: { name: '重要', color: 'orange' },
  3: { name: '普通', color: 'blue' },
  4: { name: '低', color: 'green' },
  5: { name: '最低', color: 'default' }
};

interface EnhancedCalendarViewProps {
  events?: CalendarEvent[];
  loading?: boolean;
  onEventUpdate?: (eventId: number, updates: Partial<CalendarEvent>) => Promise<void>;
  onEventDelete?: (eventId: number) => Promise<void>;
  onReminderUpdate?: (eventId: number, reminders: any[]) => Promise<void>;
}

export const EnhancedCalendarView: React.FC<EnhancedCalendarViewProps> = ({
  events = [],
  loading = false,
  onEventUpdate,
  onEventDelete,
  onReminderUpdate
}) => {
  // 狀態管理
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
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

  // 篩選後的事件
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      // 事件類型篩選
      if (filters.eventTypes.length > 0 && !filters.eventTypes.includes(event.event_type)) {
        return false;
      }

      // 優先級篩選
      if (filters.priorities.length > 0 && !filters.priorities.includes(event.priority)) {
        return false;
      }

      // 狀態篩選
      if (filters.statuses.length > 0 && !filters.statuses.includes(event.status)) {
        return false;
      }

      // 日期範圍篩選
      if (filters.dateRange) {
        const eventDate = dayjs(event.start_date);
        const [start, end] = filters.dateRange;
        if (!eventDate.isBetween(start, end, 'day', '[]')) {
          return false;
        }
      }

      // 文字搜尋篩選
      if (filters.searchText) {
        const searchLower = filters.searchText.toLowerCase();
        if (!event.title.toLowerCase().includes(searchLower) &&
            !event.description?.toLowerCase().includes(searchLower)) {
          return false;
        }
      }

      // 提醒篩選
      if (filters.hasReminders !== undefined) {
        const hasReminders = event.reminder_enabled && event.reminders && event.reminders.length > 0;
        if (hasReminders !== filters.hasReminders) {
          return false;
        }
      }

      return true;
    });
  }, [events, filters]);

  // 獲取指定日期的事件
  const getEventsForDate = (date: Dayjs) => {
    return filteredEvents.filter(event => {
      const eventStart = dayjs(event.start_date);
      const eventEnd = dayjs(event.end_date);
      return date.isBetween(eventStart, eventEnd, 'day', '[]');
    });
  };

  // 統計數據
  const statistics = useMemo(() => {
    const total = filteredEvents.length;
    const pending = filteredEvents.filter(e => e.status === 'pending').length;
    const completed = filteredEvents.filter(e => e.status === 'completed').length;
    const withReminders = filteredEvents.filter(e => e.reminder_enabled && (e.reminders?.length ?? 0) > 0).length;
    const overdue = filteredEvents.filter(e =>
      e.status === 'pending' && dayjs(e.start_date).isBefore(dayjs(), 'day')
    ).length;

    return { total, pending, completed, withReminders, overdue };
  }, [filteredEvents]);

  // 行事曆渲染
  const dateCellRender = (value: Dayjs) => {
    const eventsForDate = getEventsForDate(value);
    if (eventsForDate.length === 0) return null;

    return (
      <ul className="events" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {eventsForDate.slice(0, 3).map((event, index) => (
          <li key={event.id} style={{ marginBottom: '2px' }}>
            <Tooltip title={`${event.title} - ${EVENT_TYPE_CONFIG[event.event_type].name}`}>
              <Badge
                status={event.status === 'completed' ? 'success' :
                       event.status === 'cancelled' ? 'error' : 'processing'}
                text={
                  <span style={{
                    fontSize: '10px',
                    color: EVENT_TYPE_CONFIG[event.event_type].color === 'red' ? '#ff4d4f' :
                           EVENT_TYPE_CONFIG[event.event_type].color === 'orange' ? '#fa8c16' :
                           EVENT_TYPE_CONFIG[event.event_type].color === 'blue' ? '#1890ff' :
                           EVENT_TYPE_CONFIG[event.event_type].color === 'purple' ? '#722ed1' : '#666'
                  }}>
                    {event.title.substring(0, 8)}
                    {event.title.length > 8 && '...'}
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
    {
      type: 'divider'
    },
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
        Modal.confirm({
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

  // 列表視圖渲染
  const renderListView = () => (
    <List
      dataSource={filteredEvents}
      renderItem={(event) => (
        <List.Item
          actions={[
            <Dropdown menu={{ items: getEventActionMenu(event) }} trigger={['click']}>
              <Button icon={<SettingOutlined />} size="small" />
            </Dropdown>
          ]}
        >
          <List.Item.Meta
            avatar={
              <Badge
                status={event.status === 'completed' ? 'success' :
                       event.status === 'cancelled' ? 'error' : 'processing'}
                text=""
              />
            }
            title={
              <Space>
                {EVENT_TYPE_CONFIG[event.event_type].icon}
                <span>{event.title}</span>
                <Tag color={EVENT_TYPE_CONFIG[event.event_type].color}>
                  {EVENT_TYPE_CONFIG[event.event_type].name}
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
              </Space>
            }
          />
        </List.Item>
      )}
    />
  );

  // 時間軸視圖渲染
  const renderTimelineView = () => {
    const sortedEvents = [...filteredEvents].sort((a, b) =>
      dayjs(a.start_date).valueOf() - dayjs(b.start_date).valueOf()
    );

    return (
      <Timeline
        items={sortedEvents.map(event => ({
          color: EVENT_TYPE_CONFIG[event.event_type].color,
          dot: EVENT_TYPE_CONFIG[event.event_type].icon,
          children: (
            <Card size="small" style={{ marginBottom: 8 }}>
              <Space direction="vertical" size="small">
                <Space>
                  <Text strong>{event.title}</Text>
                  <Tag color={EVENT_TYPE_CONFIG[event.event_type].color}>
                    {EVENT_TYPE_CONFIG[event.event_type].name}
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
              </Space>
            </Card>
          )
        }))}
      />
    );
  };

  // 篩選面板
  const renderFilterPanel = () => (
    <Modal
      title="事件篩選"
      open={showFilterModal}
      onCancel={() => setShowFilterModal(false)}
      onOk={() => setShowFilterModal(false)}
      width={600}
    >
      <Form layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="事件類型">
              <Select
                mode="multiple"
                placeholder="選擇事件類型"
                value={filters.eventTypes}
                onChange={(value) => setFilters(prev => ({ ...prev, eventTypes: value }))}
                options={Object.entries(EVENT_TYPE_CONFIG).map(([key, config]) => ({
                  label: config.name,
                  value: key
                }))}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="優先級">
              <Select
                mode="multiple"
                placeholder="選擇優先級"
                value={filters.priorities}
                onChange={(value) => setFilters(prev => ({ ...prev, priorities: value }))}
                options={Object.entries(PRIORITY_CONFIG).map(([key, config]) => ({
                  label: config.name,
                  value: Number(key)
                }))}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="狀態">
              <Select
                mode="multiple"
                placeholder="選擇狀態"
                value={filters.statuses}
                onChange={(value) => setFilters(prev => ({ ...prev, statuses: value }))}
                options={[
                  { label: '待處理', value: 'pending' },
                  { label: '已完成', value: 'completed' },
                  { label: '已取消', value: 'cancelled' }
                ]}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="日期範圍">
              <RangePicker
                value={filters.dateRange}
                onChange={(dates) => setFilters(prev => ({
                  ...prev,
                  dateRange: dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null
                }))}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label="關鍵字搜尋">
          <Search
            placeholder="搜尋事件標題或描述"
            value={filters.searchText}
            onChange={(e) => setFilters(prev => ({ ...prev, searchText: e.target.value }))}
            allowClear
          />
        </Form.Item>
        <Form.Item label="提醒設定">
          <Radio.Group
            value={filters.hasReminders}
            onChange={(e) => setFilters(prev => ({ ...prev, hasReminders: e.target.value }))}
          >
            <Radio value={undefined}>全部</Radio>
            <Radio value={true}>有提醒</Radio>
            <Radio value={false}>無提醒</Radio>
          </Radio.Group>
        </Form.Item>
      </Form>
    </Modal>
  );

  // 事件詳情模態框
  const renderEventModal = () => (
    <Modal
      title="事件詳情"
      open={showEventModal}
      onCancel={() => setShowEventModal(false)}
      footer={[
        <Button key="close" onClick={() => setShowEventModal(false)}>
          關閉
        </Button>,
        <Button
          key="reminders"
          icon={<BellOutlined />}
          onClick={() => {
            setShowEventModal(false);
            setShowReminderModal(true);
          }}
        >
          提醒設定
        </Button>
      ]}
      width={600}
    >
      {selectedEvent && (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>{selectedEvent.title}</Title>
            <Space wrap>
              <Tag color={EVENT_TYPE_CONFIG[selectedEvent.event_type].color}>
                {EVENT_TYPE_CONFIG[selectedEvent.event_type].name}
              </Tag>
              <Tag color={PRIORITY_CONFIG[selectedEvent.priority]?.color ?? 'default'}>
                {PRIORITY_CONFIG[selectedEvent.priority]?.name ?? '未知'}
              </Tag>
              <Tag color={selectedEvent.status === 'completed' ? 'success' : 'processing'}>
                {selectedEvent.status === 'completed' ? '已完成' :
                 selectedEvent.status === 'cancelled' ? '已取消' : '待處理'}
              </Tag>
            </Space>
          </div>

          {selectedEvent.description && (
            <div>
              <Text strong>描述：</Text>
              <div>{selectedEvent.description}</div>
            </div>
          )}

          <div>
            <Text strong>時間：</Text>
            <div>{dayjs(selectedEvent.start_date).format('YYYY-MM-DD HH:mm')}</div>
            {selectedEvent.end_date !== selectedEvent.start_date && (
              <div>至 {dayjs(selectedEvent.end_date).format('YYYY-MM-DD HH:mm')}</div>
            )}
          </div>

          {selectedEvent.reminders && selectedEvent.reminders.length > 0 && (
            <div>
              <Text strong>提醒設定：</Text>
              <List
                size="small"
                dataSource={selectedEvent.reminders}
                renderItem={(reminder) => (
                  <List.Item>
                    <Space>
                      <Badge
                        status={reminder.status === 'sent' ? 'success' :
                               reminder.status === 'failed' ? 'error' : 'processing'}
                      />
                      <span>{dayjs(reminder.reminder_time).format('YYYY-MM-DD HH:mm')}</span>
                      <Tag>{reminder.notification_type === 'email' ? '郵件' : '系統通知'}</Tag>
                      {reminder.is_sent && <Text type="success">已發送</Text>}
                      {reminder.retry_count > 0 && (
                        <Text type="warning">重試 {reminder.retry_count} 次</Text>
                      )}
                    </Space>
                  </List.Item>
                )}
              />
            </div>
          )}
        </Space>
      )}
    </Modal>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 標題和工具列 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2}>增強型行事曆</Title>
            <Text type="secondary">提供多種視圖模式和進階篩選功能</Text>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setSelectedEvent(null);
                setEventFormMode('create');
                setShowEventFormModal(true);
              }}
            >
              新增事件
            </Button>
            <Button
              icon={<FilterOutlined />}
              onClick={() => setShowFilterModal(true)}
            >
              篩選
            </Button>
            <Radio.Group
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              buttonStyle="solid"
            >
              <Radio.Button value="month">
                <CalendarOutlined /> 月檢視
              </Radio.Button>
              <Radio.Button value="list">
                <UnorderedListOutlined /> 列表
              </Radio.Button>
              <Radio.Button value="timeline">
                <TableOutlined /> 時間軸
              </Radio.Button>
            </Radio.Group>
          </Space>
        </div>

        {/* 統計數據 */}
        <Card>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="總事件數"
                value={statistics.total}
                prefix={<CalendarOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="待處理"
                value={statistics.pending}
                valueStyle={{ color: '#faad14' }}
                prefix={<ClockCircleOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="已完成"
                value={statistics.completed}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="有提醒"
                value={statistics.withReminders}
                prefix={<BellOutlined />}
              />
            </Col>
          </Row>
          {statistics.overdue > 0 && (
            <div style={{ marginTop: 16 }}>
              <Tag color="red">
                <ExclamationCircleOutlined /> {statistics.overdue} 個事件已逾期
              </Tag>
            </div>
          )}
        </Card>

        {/* 主要內容區域 */}
        <Card loading={loading}>
          {viewMode === 'month' && (
            <Calendar
              cellRender={cellRender}
              onSelect={(date) => {
                const eventsForDate = getEventsForDate(date);
                if (eventsForDate.length > 0) {
                  setSelectedDate(date);
                  // 可以在這裡打開當日事件列表
                }
              }}
            />
          )}

          {viewMode === 'list' && (
            filteredEvents.length > 0 ? renderListView() :
            <Empty description="沒有符合條件的事件" />
          )}

          {viewMode === 'timeline' && (
            filteredEvents.length > 0 ? renderTimelineView() :
            <Empty description="沒有符合條件的事件" />
          )}
        </Card>

        {/* 模態框 */}
        {renderFilterPanel()}
        {renderEventModal()}

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
            // 重新載入事件列表
            notification.success({ message: '事件操作成功，請重新載入頁面' });
          }}
        />

        {/* 提醒設定模態框 */}
        <ReminderSettingsModal
          visible={showReminderModal}
          event={selectedEvent}
          onClose={() => {
            setShowReminderModal(false);
          }}
          onSuccess={() => {
            notification.success({ message: '提醒設定已更新' });
          }}
        />
      </Space>
    </div>
  );
};

export default EnhancedCalendarView;