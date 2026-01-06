/**
 * 整合行事曆頁面
 * 合併 CalendarPage + PureCalendarPage 功能
 * 統一使用 dayjs 日期套件
 */
import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Typography,
  Calendar,
  Badge,
  List,
  Alert,
  Button,
  Space,
  Modal,
  Tag,
  Switch,
  message,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  SyncOutlined,
  GoogleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CalendarOutlined,
  AppstoreOutlined,
  ClockCircleOutlined,
  ScheduleOutlined,
} from '@ant-design/icons';
import type { CalendarProps } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { EnhancedCalendarView } from '../components/calendar/EnhancedCalendarView';
import { authService } from '../services/authService';
import { API_BASE_URL } from '../api/client';

// 啟用 dayjs 週計算插件
dayjs.extend(isoWeek);

const { Title, Text } = Typography;

// ============================================================================
// 型別定義
// ============================================================================

interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  document_id?: number;
  doc_number?: string;
  event_type?: string;
  priority?: number | string;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
}

interface CalendarStats {
  total_events: number;
  today_events: number;
  this_week_events: number;
  this_month_events: number;
  upcoming_events: number;
}

interface EventCategory {
  value: string;
  label: string;
  color: string;
}

interface GoogleCalendarStatus {
  google_calendar_available: boolean;
  connection_status: {
    status: string;
    message: string;
    calendars?: Array<{
      id: string;
      summary: string;
      primary: boolean;
    }>;
  };
  service_type: string;
  supported_event_types: Array<{
    type: string;
    name: string;
    color: string;
  }>;
  features: string[];
}

// 預設事件分類
const DEFAULT_CATEGORIES: EventCategory[] = [
  { value: 'reminder', label: '提醒', color: '#faad14' },
  { value: 'deadline', label: '截止日期', color: '#f5222d' },
  { value: 'meeting', label: '會議', color: '#722ed1' },
  { value: 'review', label: '審查', color: '#1890ff' },
];

// ============================================================================
// 主元件
// ============================================================================

const CalendarPage: React.FC = () => {
  // 狀態管理
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [googleStatus, setGoogleStatus] = useState<GoogleCalendarStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [showEventModal, setShowEventModal] = useState(false);
  const [useEnhancedView, setUseEnhancedView] = useState(false);
  const [categories] = useState<EventCategory[]>(DEFAULT_CATEGORIES);

  // ============================================================================
  // 計算統計資料 (使用 useMemo 優化效能)
  // ============================================================================
  const stats: CalendarStats = useMemo(() => {
    const now = dayjs();
    const todayStr = now.format('YYYY-MM-DD');
    const weekStart = now.startOf('isoWeek');
    const weekEnd = now.endOf('isoWeek');
    const monthStart = now.startOf('month');
    const monthEnd = now.endOf('month');

    const events = Array.isArray(calendarEvents) ? calendarEvents : [];

    const todayEvents = events.filter(e =>
      dayjs(e.start_datetime).format('YYYY-MM-DD') === todayStr
    ).length;

    const weekEvents = events.filter(e => {
      const eventDate = dayjs(e.start_datetime);
      return eventDate.isAfter(weekStart) && eventDate.isBefore(weekEnd);
    }).length;

    const monthEvents = events.filter(e => {
      const eventDate = dayjs(e.start_datetime);
      return eventDate.isAfter(monthStart) && eventDate.isBefore(monthEnd);
    }).length;

    const upcomingEvents = events.filter(e =>
      dayjs(e.start_datetime).isAfter(now)
    ).length;

    return {
      total_events: events.length,
      today_events: todayEvents,
      this_week_events: weekEvents,
      this_month_events: monthEvents,
      upcoming_events: upcomingEvents,
    };
  }, [calendarEvents]);

  // ============================================================================
  // API 請求
  // ============================================================================

  // 獲取行事曆事件
  const fetchCalendarEvents = async () => {
    try {
      setLoading(true);
      const api = authService.getAxiosInstance();
      const userInfo = authService.getUserInfo();
      const userId = userInfo?.id || 1;

      // 設定日期範圍：前2個月到後2個月
      const now = dayjs();
      const startDate = now.subtract(2, 'month').format('YYYY-MM-DD');
      const endDate = now.add(2, 'month').format('YYYY-MM-DD');

      const response = await api.post('/calendar/users/calendar-events', {
        user_id: userId,
        start_date: startDate,
        end_date: endDate
      });

      const data = response.data;
      if (data && Array.isArray(data.events)) {
        const events: CalendarEvent[] = data.events.map((event: any) => ({
          id: event.id,
          title: event.title,
          description: event.description,
          start_datetime: event.start_date,
          end_datetime: event.end_date,
          document_id: event.document_id,
          doc_number: event.doc_number,
          event_type: event.event_type,
          priority: event.priority,
          google_event_id: event.google_event_id,
          google_sync_status: event.google_sync_status || 'pending'
        }));
        setCalendarEvents(events);
      } else if (Array.isArray(data)) {
        setCalendarEvents(data);
      } else {
        setCalendarEvents([]);
      }
    } catch (error: any) {
      console.warn('無法載入行事曆事件:', error);
      setCalendarEvents([]);
    } finally {
      setLoading(false);
    }
  };

  // 獲取 Google Calendar 狀態
  const fetchGoogleStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/public/calendar-status`);
      if (response.ok) {
        const data = await response.json();
        setGoogleStatus({
          google_calendar_available: data.google_calendar_integration || false,
          connection_status: {
            status: data.google_status?.configured ? 'connected' : 'disconnected',
            message: data.message || '狀態未知',
            calendars: data.google_status?.calendar_id ? [{
              id: data.google_status.calendar_id,
              summary: 'Primary Calendar',
              primary: true
            }] : []
          },
          service_type: data.endpoint_type || 'basic',
          supported_event_types: DEFAULT_CATEGORIES.map(c => ({
            type: c.value,
            name: c.label,
            color: c.color
          })),
          features: data.features || ['本地行事曆', '事件提醒']
        });
      } else {
        setGoogleStatus({
          google_calendar_available: false,
          connection_status: {
            status: response.status === 403 ? 'auth_required' : 'service_unavailable',
            message: response.status === 403 ? '需要登入才能存取行事曆功能' : '行事曆服務暫時無法使用'
          },
          service_type: '行事曆管理系統',
          supported_event_types: DEFAULT_CATEGORIES.map(c => ({
            type: c.value,
            name: c.label,
            color: c.color
          })),
          features: ['基本行事曆檢視', '事件提醒功能', '本地事件儲存']
        });
      }
    } catch (error) {
      console.error('獲取 Google Calendar 狀態失敗:', error);
      setGoogleStatus({
        google_calendar_available: false,
        connection_status: { status: 'error', message: '無法連接到行事曆服務' },
        service_type: '行事曆管理系統',
        supported_event_types: DEFAULT_CATEGORIES.map(c => ({
          type: c.value,
          name: c.label,
          color: c.color
        })),
        features: ['基本行事曆檢視', '事件提醒功能', '本地事件儲存']
      });
    }
  };

  // 手動同步到 Google Calendar
  const handleBulkSync = async () => {
    try {
      setLoading(true);
      message.warning('同步功能暫時不可用，請稍後再試');
    } catch (error) {
      console.error('批量同步失敗:', error);
      Modal.error({
        title: '同步失敗',
        content: '無法執行批量同步，請檢查網路連接和 Google Calendar 設定',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendarEvents();
    fetchGoogleStatus();
  }, []);

  // ============================================================================
  // 事件處理函數
  // ============================================================================

  // 取得指定日期的事件
  const getEventsForDate = (date: Dayjs): CalendarEvent[] => {
    const dateStr = date.format('YYYY-MM-DD');
    return (Array.isArray(calendarEvents) ? calendarEvents : []).filter(event =>
      dayjs(event.start_datetime).format('YYYY-MM-DD') === dateStr ||
      dayjs(event.end_datetime).format('YYYY-MM-DD') === dateStr
    );
  };

  // 取得事件顏色
  const getEventColor = (eventType?: string): string => {
    const category = categories.find(c => c.value === eventType);
    return category?.color || '#1890ff';
  };

  // 取得優先級標籤
  const getPriorityTag = (priority?: number | string) => {
    const p = typeof priority === 'string' ? parseInt(priority, 10) : priority;
    if (p === undefined || p === null) return null;
    if (p >= 4) return <Tag color="red">高優先</Tag>;
    if (p >= 2) return <Tag color="orange">中優先</Tag>;
    return <Tag color="green">低優先</Tag>;
  };

  // 日曆單元格渲染
  const dateCellRender = (value: Dayjs) => {
    const dayEvents = getEventsForDate(value);
    return (
      <ul className="events" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {dayEvents.slice(0, 3).map((event, index) => (
          <li key={index} style={{ marginBottom: 2 }}>
            <Badge
              color={getEventColor(event.event_type)}
              text={
                <span style={{ fontSize: '11px' }}>
                  {event.title.length > 10 ? `${event.title.substring(0, 10)}...` : event.title}
                </span>
              }
            />
          </li>
        ))}
        {dayEvents.length > 3 && (
          <li style={{ fontSize: '11px', color: '#999' }}>+{dayEvents.length - 3} 更多</li>
        )}
      </ul>
    );
  };

  const monthCellRender = (value: Dayjs) => {
    const monthEvents = (Array.isArray(calendarEvents) ? calendarEvents : []).filter(event =>
      dayjs(event.start_datetime).month() === value.month() &&
      dayjs(event.start_datetime).year() === value.year()
    );
    return monthEvents.length > 0 ? (
      <div className="notes-month">
        <section>{monthEvents.length}</section>
        <span>事件</span>
      </div>
    ) : null;
  };

  const cellRender: CalendarProps<Dayjs>['cellRender'] = (current, info) => {
    if (info.type === 'date') return dateCellRender(current);
    if (info.type === 'month') return monthCellRender(current);
    return info.originNode;
  };

  const onDateSelect = (date: Dayjs) => {
    setSelectedDate(date);
    const eventsForDate = getEventsForDate(date);
    if (eventsForDate.length > 0) {
      setShowEventModal(true);
    }
  };

  // 處理事件更新
  const handleEventUpdate = async (eventId: number, updates: any) => {
    try {
      console.log('更新事件:', eventId, updates);
      await fetchCalendarEvents();
    } catch (error) {
      console.error('更新事件失敗:', error);
    }
  };

  // 處理事件刪除
  const handleEventDelete = async (eventId: number) => {
    try {
      console.log('刪除事件:', eventId);
      await fetchCalendarEvents();
    } catch (error) {
      console.error('刪除事件失敗:', error);
    }
  };

  const selectedDateEvents = getEventsForDate(selectedDate);

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <div style={{ padding: '24px' }}>
      {/* 標題列 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={18}>
          <Title level={2}>
            <CalendarOutlined style={{ marginRight: 8 }} />
            行事曆管理
          </Title>
          <Text type="secondary">整合顯示公文相關事件，支援 Google Calendar 同步</Text>
        </Col>
        <Col span={6} style={{ textAlign: 'right' }}>
          <Space>
            <Text>視圖：</Text>
            <Switch
              checkedChildren={<AppstoreOutlined />}
              unCheckedChildren={<CalendarOutlined />}
              checked={useEnhancedView}
              onChange={setUseEnhancedView}
            />
            <Text type="secondary">{useEnhancedView ? '增強' : '傳統'}</Text>
          </Space>
        </Col>
      </Row>

      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="總事件數"
              value={stats.total_events}
              prefix={<ScheduleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="今日事件"
              value={stats.today_events}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="本週事件"
              value={stats.this_week_events}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="即將到來"
              value={stats.upcoming_events}
              prefix={<SyncOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Google Calendar 狀態 (可折疊) */}
      {googleStatus && (
        <Card
          size="small"
          title={
            <Space>
              <GoogleOutlined style={{ color: '#1890ff' }} />
              Google Calendar 整合
              {googleStatus.google_calendar_available ? (
                <Tag color="success" icon={<CheckCircleOutlined />}>已連接</Tag>
              ) : (
                <Tag color="default" icon={<ExclamationCircleOutlined />}>未連接</Tag>
              )}
            </Space>
          }
          extra={
            <Button
              size="small"
              type="primary"
              icon={<SyncOutlined spin={loading} />}
              loading={loading}
              onClick={handleBulkSync}
            >
              同步
            </Button>
          }
          style={{ marginBottom: 24 }}
        >
          <Space wrap>
            <Text type="secondary">{googleStatus.connection_status?.message}</Text>
            {googleStatus.features?.map((feature, index) => (
              <Tag key={index}>{feature}</Tag>
            ))}
          </Space>
        </Card>
      )}

      {/* 主要內容區 */}
      <Row gutter={16}>
        {/* 行事曆區域 */}
        <Col span={18}>
          {useEnhancedView ? (
            <EnhancedCalendarView
              events={calendarEvents.map(event => ({
                ...event,
                event_type: (event.event_type || 'reminder') as any,
                priority: typeof event.priority === 'number' ? event.priority : 3,
                status: 'pending' as any,
                reminder_enabled: true,
                reminders: []
              }))}
              loading={loading}
              onEventUpdate={handleEventUpdate}
              onEventDelete={handleEventDelete}
            />
          ) : (
            <Card title="行事曆檢視" loading={loading}>
              <Calendar cellRender={cellRender} onSelect={onDateSelect} />
            </Card>
          )}
        </Col>

        {/* 側邊事件列表 */}
        <Col span={6}>
          <Card
            title={`${selectedDate.format('MM/DD')} 事件 (${selectedDateEvents.length})`}
            style={{ height: '100%' }}
          >
            <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
              {selectedDateEvents.length > 0 ? (
                selectedDateEvents.map(event => (
                  <Card
                    key={event.id}
                    size="small"
                    style={{ marginBottom: 8 }}
                    hoverable
                  >
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 4 }}>
                        {event.title}
                      </Text>
                      <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                        {dayjs(event.start_datetime).format('HH:mm')} -
                        {dayjs(event.end_datetime).format('HH:mm')}
                      </Text>
                      <Space style={{ marginTop: 4 }} wrap>
                        <Tag color={getEventColor(event.event_type)}>
                          {categories.find(c => c.value === event.event_type)?.label || '提醒'}
                        </Tag>
                        {getPriorityTag(event.priority)}
                        {event.google_event_id && (
                          <Tag color="blue" icon={<GoogleOutlined />}>已同步</Tag>
                        )}
                      </Space>
                      {event.description && (
                        <Text
                          type="secondary"
                          style={{ fontSize: '12px', display: 'block', marginTop: 4 }}
                          ellipsis={{ tooltip: event.description }}
                        >
                          {event.description.substring(0, 50)}
                          {event.description.length > 50 ? '...' : ''}
                        </Text>
                      )}
                      {event.doc_number && (
                        <Text type="secondary" style={{ fontSize: '11px', display: 'block' }}>
                          公文: {event.doc_number}
                        </Text>
                      )}
                    </div>
                  </Card>
                ))
              ) : (
                <Text type="secondary">此日無事件</Text>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 事件詳情模態框 */}
      <Modal
        title={`${selectedDate.format('YYYY年MM月DD日')} 的事件`}
        open={showEventModal}
        onCancel={() => setShowEventModal(false)}
        footer={null}
        width={600}
      >
        <List
          dataSource={selectedDateEvents}
          renderItem={(event) => (
            <List.Item>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Badge
                    color={getEventColor(event.event_type)}
                    text={<Text strong>{event.title}</Text>}
                  />
                  {event.google_event_id && (
                    <Tag color="blue" style={{ marginLeft: '8px' }}>
                      <GoogleOutlined /> 已同步
                    </Tag>
                  )}
                </div>
                <Space>
                  <Tag color={getEventColor(event.event_type)}>
                    {categories.find(c => c.value === event.event_type)?.label || '提醒'}
                  </Tag>
                  {getPriorityTag(event.priority)}
                </Space>
                {event.description && (
                  <Text type="secondary">{event.description}</Text>
                )}
                {event.document_id && (
                  <Text type="secondary">
                    相關公文: {event.doc_number || `ID ${event.document_id}`}
                  </Text>
                )}
              </Space>
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

export default CalendarPage;
