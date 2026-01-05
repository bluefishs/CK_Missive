import React, { useState, useEffect } from 'react';
import { Card, Typography, Calendar, Badge, List, Alert, Button, Space, Modal, Tag, Tabs, Switch, message } from 'antd';
import { SyncOutlined, GoogleOutlined, CheckCircleOutlined, ExclamationCircleOutlined, CalendarOutlined, AppstoreOutlined } from '@ant-design/icons';
import type { CalendarProps } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { EnhancedCalendarView } from '../components/calendar/EnhancedCalendarView';
import { authService } from '../services/authService';

const { Title, Text } = Typography;

interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime: string;
  document_id?: number;
  google_event_id?: string;
  google_sync_status?: 'pending' | 'synced' | 'failed';
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

const CalendarPage: React.FC = () => {
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [googleStatus, setGoogleStatus] = useState<GoogleCalendarStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(null);
  const [showEventModal, setShowEventModal] = useState(false);
  const [useEnhancedView, setUseEnhancedView] = useState(false);

  // 獲取行事曆事件
  const fetchCalendarEvents = async () => {
    try {
      setLoading(true);
      const api = authService.getAxiosInstance();
      const userInfo = authService.getUserInfo();

      // 取得當前使用者 ID，若無則使用預設值 1
      const userId = userInfo?.id || 1;

      // 設定預設日期範圍：前1個月到後1個月
      const now = dayjs();
      const startDate = now.subtract(1, 'month').format('YYYY-MM-DD');
      const endDate = now.add(1, 'month').format('YYYY-MM-DD');

      // 呼叫正確的API端點並提供日期範圍
      const response = await api.get(`/calendar/users/${userId}/calendar-events`, {
        params: {
          start_date: startDate,
          end_date: endDate
        }
      });

      // 處理 API 回應格式 { events: [], total, ... }
      const data = response.data;
      if (data && Array.isArray(data.events)) {
        // 轉換 API 回應格式以符合前端介面
        const events: CalendarEvent[] = data.events.map((event: any) => ({
          id: event.id,
          title: event.title,
          description: event.description,
          start_datetime: event.start_date,
          end_datetime: event.end_date,
          document_id: event.document_id,
          google_event_id: event.google_event_id,
          google_sync_status: event.google_sync_status || 'pending'
        }));
        setCalendarEvents(events);
      } else if (Array.isArray(data)) {
        // 向後相容：若直接回傳陣列
        setCalendarEvents(data);
      } else {
        setCalendarEvents([]);
      }
    } catch (error: any) {
      console.warn('無法載入行事曆事件，使用空清單', error);
      setCalendarEvents([]);
    } finally {
      setLoading(false);
    }
  };

  // 獲取 Google Calendar 狀態
  const fetchGoogleStatus = async () => {
    try {
      const response = await fetch('/api/public/calendar-status');
      if (response.ok) {
        const data = await response.json();
        // 轉換API回應格式為前端期待的格式
        const transformedStatus: GoogleCalendarStatus = {
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
          supported_event_types: [
            { type: 'reminder', name: '提醒', color: '#1890ff' },
            { type: 'deadline', name: '截止日期', color: '#f5222d' },
            { type: 'meeting', name: '會議', color: '#52c41a' },
            { type: 'review', name: '審查', color: '#faad14' }
          ],
          features: data.features || ['本地行事曆', '事件提醒']
        };
        setGoogleStatus(transformedStatus);
      } else if (response.status === 403) {
        console.warn('權限不足，載入預設狀態');
        setGoogleStatus({
          google_calendar_available: false,
          connection_status: {
            status: 'auth_required',
            message: '需要登入才能存取行事曆功能'
          },
          service_type: '行事曆管理系統',
          supported_event_types: [
            { type: 'deadline', name: '截止提醒', color: '紅色' },
            { type: 'reminder', name: '一般提醒', color: '黃色' },
            { type: 'meeting', name: '會議安排', color: '紫色' },
            { type: 'review', name: '審核提醒', color: '藍色' }
          ],
          features: [
            '基本行事曆檢視',
            '事件提醒功能',
            '本地事件儲存'
          ]
        });
      } else {
        console.warn('無法載入 Google Calendar 狀態，使用預設值');
        setGoogleStatus({
          google_calendar_available: false,
          connection_status: {
            status: 'service_unavailable',
            message: '行事曆服務暫時無法使用，請稍後再試'
          },
          service_type: '行事曆管理系統',
          supported_event_types: [
            { type: 'deadline', name: '截止提醒', color: '紅色' },
            { type: 'reminder', name: '一般提醒', color: '黃色' },
            { type: 'meeting', name: '會議安排', color: '紫色' },
            { type: 'review', name: '審核提醒', color: '藍色' }
          ],
          features: [
            '基本行事曆檢視',
            '事件提醒功能',
            '本地事件儲存'
          ]
        });
      }
    } catch (error) {
      console.error('獲取 Google Calendar 狀態失敗:', error);
      setGoogleStatus({
        google_calendar_available: false,
        connection_status: {
          status: 'error',
          message: '無法連接到行事曆服務'
        },
        service_type: '行事曆管理系統',
        supported_event_types: [
          { type: 'deadline', name: '截止提醒', color: '紅色' },
          { type: 'reminder', name: '一般提醒', color: '黃色' },
          { type: 'meeting', name: '會議安排', color: '紫色' },
          { type: 'review', name: '審核提醒', color: '藍色' }
        ],
        features: [
          '基本行事曆檢視',
          '事件提醒功能',
          '本地事件儲存'
        ]
      });
    }
  };

  // 手動同步到 Google Calendar
  const handleBulkSync = async () => {
    try {
      setLoading(true);
      // TODO: 實作 bulk-sync 端點
      message.warning('同步功能暫時不可用，請稍後再試');
      // const response = await fetch('/api/calendar/bulk-sync', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({
      //     document_ids: null,  // 同步所有文件
      //     user_calendar_id: null  // 使用預設日曆
      //   })
      // });

      // if (response.ok) {
      //   const result = await response.json();
      //   Modal.success({
      //     title: '同步成功',
      //     content: result.message || result.description,
      //   });
      //   // 重新載入事件
      //   await fetchCalendarEvents();
      // } else {
      //   const error = await response.json();
      //   Modal.error({
      //     title: '同步失敗',
      //     content: error.detail || '批量同步失敗，請檢查 Google Calendar 設定',
      //   });
      // }
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

  const getListData = (value: Dayjs) => {
    const dateStr = value.format('YYYY-MM-DD');
    const eventsForDate = (Array.isArray(calendarEvents) ? calendarEvents : []).filter(event => 
      dayjs(event.start_datetime).format('YYYY-MM-DD') === dateStr ||
      dayjs(event.end_datetime).format('YYYY-MM-DD') === dateStr
    );

    return eventsForDate.map(event => ({
      type: event.google_sync_status === 'synced' ? 'success' : 
            event.google_sync_status === 'failed' ? 'error' : 'warning',
      content: event.title,
      event: event
    }));
  };

  const getMonthData = (value: Dayjs) => {
    const monthEvents = (Array.isArray(calendarEvents) ? calendarEvents : []).filter(event => 
      dayjs(event.start_datetime).month() === value.month() &&
      dayjs(event.start_datetime).year() === value.year()
    );
    return monthEvents.length;
  };

  const monthCellRender = (value: Dayjs) => {
    const num = getMonthData(value);
    return num > 0 ? (
      <div className="notes-month">
        <section>{num}</section>
        <span>事件總數</span>
      </div>
    ) : null;
  };

  const dateCellRender = (value: Dayjs) => {
    const listData = getListData(value);
    return (
      <ul className="events" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {listData.map((item, index) => (
          <li key={index}>
            <Badge 
              status={item.type as any} 
              text={item.content}
              style={{ fontSize: '12px' }}
            />
            {(item as any).event?.google_event_id && (
              <GoogleOutlined style={{ fontSize: '10px', marginLeft: '4px', color: '#1890ff' }} />
            )}
          </li>
        ))}
      </ul>
    );
  };

  const cellRender: CalendarProps<Dayjs>['cellRender'] = (current, info) => {
    if (info.type === 'date') return dateCellRender(current);
    if (info.type === 'month') return monthCellRender(current);
    return info.originNode;
  };

  const onDateSelect = (date: Dayjs) => {
    setSelectedDate(date);
    const eventsForDate = getListData(date);
    if (eventsForDate.length > 0) {
      setShowEventModal(true);
    }
  };

  const selectedDateEvents = selectedDate ? getListData(selectedDate) : [];

  // 處理事件更新
  const handleEventUpdate = async (eventId: number, updates: any) => {
    try {
      // TODO: 實作API呼叫
      console.log('更新事件:', eventId, updates);
      await fetchCalendarEvents();
    } catch (error) {
      console.error('更新事件失敗:', error);
    }
  };

  // 處理事件刪除
  const handleEventDelete = async (eventId: number) => {
    try {
      // TODO: 實作API呼叫
      console.log('刪除事件:', eventId);
      await fetchCalendarEvents();
    } catch (error) {
      console.error('刪除事件失敗:', error);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2}>行事曆管理</Title>
            <Text type="secondary">顯示公文相關事件與 Google Calendar 同步狀態</Text>
          </div>
          <Space>
            <Text>視圖模式：</Text>
            <Switch
              checkedChildren={<AppstoreOutlined />}
              unCheckedChildren={<CalendarOutlined />}
              checked={useEnhancedView}
              onChange={setUseEnhancedView}
            />
            <Text type="secondary">{useEnhancedView ? '增強模式' : '傳統模式'}</Text>
          </Space>
        </div>

        {/* Google Calendar 狀態卡片 */}
        {googleStatus && (
          <Card 
            title={
              <Space>
                <GoogleOutlined style={{ color: '#1890ff' }} />
                Google Calendar 整合狀態
              </Space>
            }
            extra={
              <Button 
                type="primary" 
                icon={<SyncOutlined spin={loading} />}
                loading={loading}
                onClick={handleBulkSync}
              >
                批量同步
              </Button>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>服務狀態：</Text>
                {googleStatus.google_calendar_available ? (
                  <Tag color="success" icon={<CheckCircleOutlined />}>已連接</Tag>
                ) : (
                  <Tag color="error" icon={<ExclamationCircleOutlined />}>未連接</Tag>
                )}
              </div>
              <div>
                <Text strong>連接狀態：</Text>
                <Text type={googleStatus.connection_status?.status === 'success' ? 'success' : 'danger'}>
                  {googleStatus.connection_status?.message || '狀態未知'}
                </Text>
              </div>
              {googleStatus.connection_status?.calendars && (
                <div>
                  <Text strong>可用日曆：</Text>
                  <Space wrap>
                    {googleStatus.connection_status.calendars.map((calendar, index) => (
                      <Tag key={index} color={calendar.primary ? 'blue' : 'default'}>
                        {calendar.summary} {calendar.primary && '(主要)'}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}
              <div>
                <Text strong>同步方式：</Text>
                <Text>{googleStatus.service_type}</Text>
              </div>
              <div>
                <Text strong>支援事件類型：</Text>
                <Space wrap>
                  {(googleStatus.supported_event_types || []).map((eventType, index) => (
                    <Tag key={index} color="processing">
                      {eventType.name} ({eventType.color})
                    </Tag>
                  ))}
                </Space>
              </div>
              <div>
                <Text strong>功能：</Text>
                <Space wrap>
                  {(googleStatus.features || []).map((feature, index) => (
                    <Tag key={index}>{feature}</Tag>
                  ))}
                </Space>
              </div>
            </Space>
          </Card>
        )}

        {!googleStatus?.google_calendar_available && googleStatus?.connection_status && (
          <Alert
            message={
              googleStatus.connection_status?.status === 'auth_required' ? '需要登入' :
              googleStatus.connection_status?.status === 'service_unavailable' ? '服務暫時無法使用' :
              '行事曆服務狀態'
            }
            description={googleStatus.connection_status?.message || '狀態未知'}
            type={
              googleStatus.connection_status?.status === 'auth_required' ? 'info' :
              googleStatus.connection_status?.status === 'service_unavailable' ? 'warning' :
              'warning'
            }
            showIcon
          />
        )}

        {/* 主要行事曆 */}
        {useEnhancedView ? (
          <EnhancedCalendarView
            events={calendarEvents.map(event => ({
              ...event,
              event_type: 'reminder' as any, // 默認類型，實際應從API獲取
              priority: 3, // 默認優先級
              status: 'pending' as any, // 默認狀態
              reminder_enabled: true,
              reminders: [] // 實際應從API獲取
            }))}
            loading={loading}
            onEventUpdate={handleEventUpdate}
            onEventDelete={handleEventDelete}
          />
        ) : (
          <Card title="行事曆檢視" loading={loading}>
            <Calendar
              cellRender={cellRender}
              onSelect={onDateSelect}
            />
          </Card>
        )}

        {/* 事件詳情模態框 */}
        <Modal
          title={`${selectedDate?.format('YYYY年MM月DD日')} 的事件`}
          open={showEventModal}
          onCancel={() => setShowEventModal(false)}
          footer={null}
        >
          <List
            dataSource={selectedDateEvents}
            renderItem={(item: any) => (
              <List.Item>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Badge 
                      status={item.type as any} 
                      text={item.content}
                    />
                    {item.event?.google_event_id && (
                      <Tag color="blue" style={{ marginLeft: '8px' }}>
                        <GoogleOutlined /> 已同步
                      </Tag>
                    )}
                  </div>
                  {item.event?.description && (
                    <Text type="secondary">{item.event.description}</Text>
                  )}
                  {item.event?.document_id && (
                    <Text type="secondary">
                      相關公文ID: {item.event.document_id}
                    </Text>
                  )}
                </Space>
              </List.Item>
            )}
          />
        </Modal>
      </Space>
    </div>
  );
};

export default CalendarPage;