/**
 * 純粹行事曆頁面
 * 整合檢視所有日曆事件（僅顯示，不提供獨立事件創建功能）
 */

import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Card,
  Space,
  Typography,
  Row,
  Col,
  Badge,
  Statistic,
  App,
  Tag,
  Alert
} from 'antd';
import {
  CalendarOutlined,
  EyeOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import type { Moment } from 'moment';
import moment from 'moment';
import { pureCalendarService, PureCalendarEvent, EventCategory } from '../services/pureCalendarService';

const { Title, Text } = Typography;

interface CalendarStats {
  total_events: number;
  today_events: number;
  this_week_events: number;
  this_month_events: number;
  upcoming_events: number;
}

const PureCalendarPage: React.FC = () => {
  const { message } = App.useApp();
  const [events, setEvents] = useState<PureCalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Moment>(moment());
  const [stats, setStats] = useState<CalendarStats>({
    total_events: 0,
    today_events: 0,
    this_week_events: 0,
    this_month_events: 0,
    upcoming_events: 0
  });
  const [categories, setCategories] = useState<EventCategory[]>([]);

  // 載入事件資料
  const loadEvents = async () => {
    setLoading(true);
    try {
      const response = await pureCalendarService.getEvents();
      // 確保回應有正確的結構
      if (response && response.events) {
        setEvents(response.events);
      } else {
        // 如果沒有 events 屬性，假設回應本身就是事件陣列
        setEvents(Array.isArray(response) ? response : []);
      }
    } catch (error) {
      console.error('載入事件失敗:', error);
      message.error('載入事件失敗');
      setEvents([]); // 設定為空陣列以避免 undefined 錯誤
    } finally {
      setLoading(false);
    }
  };

  // 載入統計資料
  const loadStats = async () => {
    try {
      const statsData = await pureCalendarService.getStats();
      setStats(statsData);
    } catch (error) {
      console.error('載入統計失敗:', error);
      // 發生錯誤時保持預設值，避免 undefined
      setStats({
        total_events: 0,
        today_events: 0,
        this_week_events: 0,
        this_month_events: 0,
        upcoming_events: 0
      });
    }
  };

  // 載入分類資料
  const loadCategories = async () => {
    try {
      const response = await pureCalendarService.getCategories();
      // 確保回應有正確的結構
      if (response && response.categories) {
        setCategories(response.categories);
      } else {
        // 如果沒有 categories 屬性，假設回應本身就是分類陣列
        setCategories(Array.isArray(response) ? response : []);
      }
    } catch (error) {
      console.error('載入分類失敗:', error);
      // 發生錯誤時設定預設分類
      setCategories([
        {"value": "general", "label": "一般", "color": "#1890ff"},
        {"value": "meeting", "label": "會議", "color": "#52c41a"},
        {"value": "deadline", "label": "截止日期", "color": "#ff4d4f"},
        {"value": "reminder", "label": "提醒", "color": "#faad14"}
      ]);
    }
  };

  useEffect(() => {
    loadEvents();
    loadStats();
    loadCategories();
  }, []);

  // 獲取指定日期的事件
  const getEventsForDate = (date: Moment) => {
    const dateStr = date.format('YYYY-MM-DD');
    return events.filter(event => {
      const eventDate = moment(event.start_datetime).format('YYYY-MM-DD');
      return eventDate === dateStr;
    });
  };

  // 日曆單元格渲染
  const dateCellRender = (date: Moment) => {
    const dayEvents = getEventsForDate(date);

    return (
      <ul className="events" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {dayEvents.slice(0, 3).map(event => {
          const category = categories.find(cat => cat.value === event.category);
          return (
            <li key={event.id} style={{ marginBottom: 2 }}>
              <Badge
                color={category?.color || '#1890ff'}
                text={
                  <span style={{ fontSize: '11px' }}>
                    {event.title.length > 10 ? `${event.title.substring(0, 10)}...` : event.title}
                  </span>
                }
              />
            </li>
          );
        })}
        {dayEvents.length > 3 && (
          <li style={{ fontSize: '11px', color: '#999' }}>
            +{dayEvents.length - 3} 更多
          </li>
        )}
      </ul>
    );
  };

  // 格式化事件顯示文字
  const formatEventTitle = (event: PureCalendarEvent): string => {
    return event.title.length > 10 ? `${event.title.substring(0, 10)}...` : event.title;
  };

  // 日期選擇處理
  const onDateSelect = (date: Moment) => {
    setSelectedDate(date);
  };

  // 獲取優先級顏色
  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case 'high': return 'red';
      case 'normal': return 'blue';
      case 'low': return 'green';
      default: return 'blue';
    }
  };

  // 獲取優先級標籤
  const getPriorityLabel = (priority?: string) => {
    switch (priority) {
      case 'high': return '高';
      case 'normal': return '普通';
      case 'low': return '低';
      default: return '普通';
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Title level={2}>
            <CalendarOutlined /> 整合行事曆檢視
          </Title>
          <Alert
            message="整合檢視模式"
            description="此頁面整合顯示所有來源的日曆事件，包括公文相關事件。如需管理事件，請前往相應的功能頁面。"
            type="info"
            icon={<InfoCircleOutlined />}
            showIcon
            style={{ marginTop: 8 }}
          />
        </Col>
      </Row>

      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="總事件數"
              value={stats?.total_events || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日事件"
              value={stats?.today_events || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="本週事件"
              value={stats?.this_week_events || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="即將到來"
              value={stats?.upcoming_events || 0}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* 行事曆區域 */}
        <Col span={18}>
          <Card title="整合行事曆檢視">
            <Calendar
              cellRender={dateCellRender}
              onSelect={onDateSelect}
              loading={loading}
            />
          </Card>
        </Col>

        {/* 當日事件列表 */}
        <Col span={6}>
          <Card title={`${selectedDate.format('MM/DD')} 事件`}>
            <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
              {getEventsForDate(selectedDate).map(event => {
                const category = categories.find(cat => cat.value === event.category);
                return (
                  <Card
                    key={event.id}
                    size="small"
                    style={{ marginBottom: 8 }}
                  >
                    <div>
                      <Text strong>{event.title}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {moment(event.start_datetime).format('HH:mm')} -
                        {moment(event.end_datetime).format('HH:mm')}
                      </Text>
                      <br />
                      <Space>
                        <Tag color={category?.color}>{category?.label || '一般'}</Tag>
                        <Tag color={getPriorityColor(event.priority)}>
                          {getPriorityLabel(event.priority)}
                        </Tag>
                      </Space>
                      {event.description && (
                        <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                          {event.description}
                        </Text>
                      )}
                    </div>
                  </Card>
                );
              })}
              {getEventsForDate(selectedDate).length === 0 && (
                <Text type="secondary">此日無事件</Text>
              )}
            </div>
          </Card>
        </Col>
      </Row>

    </div>
  );
};

export default PureCalendarPage;