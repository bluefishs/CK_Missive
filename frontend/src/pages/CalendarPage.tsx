/**
 * 整合行事曆頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（事件列表、Google 狀態）
 * - Zustand: 不使用（本頁面無需跨頁面共享狀態）
 * - 統一使用 dayjs 日期套件
 *
 * @version 2.0.0 - 優化為 React Query 架構
 * @date 2026-01-08
 */
import React, { useState, useCallback } from 'react';
import {
  Card,
  Typography,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Dropdown,
  App,
  Drawer,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  SyncOutlined,
  GoogleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CalendarOutlined,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
  MenuOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { EnhancedCalendarView } from '../components/calendar/EnhancedCalendarView';
import { useCalendarPage } from '../hooks';
import { useResponsive } from '../hooks';
import type { CalendarEvent, EventCategory } from '../api/calendarApi';

// 啟用 dayjs 週計算插件
dayjs.extend(isoWeek);

const { Title, Text } = Typography;

// ============================================================================
// 主元件
// ============================================================================

const CalendarPage: React.FC = () => {
  // ============================================================================
  // React Query: 唯一的伺服器資料來源
  // ============================================================================

  const {
    events: calendarEvents,
    categories,
    googleStatus,
    isLoading: loading,
    updateEvent,
    deleteEvent,
    bulkSync,
    isSyncing,
    refetch,
  } = useCalendarPage();

  // Antd 應用程式上下文 (避免靜態方法警告)
  const { message, modal } = App.useApp();

  // ============================================================================
  // 響應式設計 (使用標準化 useResponsive hook)
  // ============================================================================
  const { isMobile, isTablet, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // ============================================================================
  // UI 狀態（本地狀態）
  // ============================================================================

  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [sidebarVisible, setSidebarVisible] = useState(false);

  // ============================================================================
  // 事件處理函數
  // ============================================================================

  // 取得指定日期的事件
  const getEventsForDate = useCallback(
    (date: Dayjs): CalendarEvent[] => {
      const dateStr = date.format('YYYY-MM-DD');
      return (Array.isArray(calendarEvents) ? calendarEvents : []).filter(
        (event) =>
          dayjs(event.start_datetime).format('YYYY-MM-DD') === dateStr ||
          dayjs(event.end_datetime).format('YYYY-MM-DD') === dateStr
      );
    },
    [calendarEvents]
  );

  // 取得事件顏色
  const getEventColor = useCallback(
    (eventType?: string): string => {
      const category = categories.find((c: EventCategory) => c.value === eventType);
      return category?.color || '#1890ff';
    },
    [categories]
  );

  // 取得優先級標籤
  const getPriorityTag = (priority?: number | string) => {
    const p = typeof priority === 'string' ? parseInt(priority, 10) : priority;
    if (p === undefined || p === null) return null;
    if (p >= 4) return <Tag color="red">高優先</Tag>;
    if (p >= 2) return <Tag color="orange">中優先</Tag>;
    return <Tag color="green">低優先</Tag>;
  };

  // 手動同步到 Google Calendar
  const handleBulkSync = async () => {
    try {
      const result = await bulkSync();
      if (result.success) {
        message.success(`同步成功：${result.synced_count} 個事件已同步至 Google Calendar`);
      } else if (result.synced_count > 0) {
        message.warning(`部分同步：${result.synced_count} 成功，${result.failed_count} 失敗`);
      } else {
        message.info(result.message || '沒有需要同步的事件');
      }
    } catch (error: any) {
      console.error('同步失敗:', error);
      message.error(error.response?.data?.detail || '同步失敗，請稍後再試');
    }
  };

  // 處理事件更新
  const handleEventUpdate = async (eventId: number, updates: any) => {
    try {
      await updateEvent({ eventId, updates });
    } catch (error) {
      console.error('更新事件失敗:', error);
    }
  };

  // 處理事件刪除
  const handleEventDelete = async (eventId: number) => {
    try {
      await deleteEvent(eventId);
    } catch (error) {
      console.error('刪除事件失敗:', error);
    }
  };

  // 事件操作選單（側邊欄用）
  const getEventActionMenu = (event: CalendarEvent): MenuProps['items'] => [
    {
      key: 'edit',
      label: '編輯事件',
      icon: <EditOutlined />,
      onClick: () => {
        message.info('請在行事曆中點選該事件進行編輯');
      }
    },
    {
      key: 'delete',
      label: '刪除事件',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {
        modal.confirm({
          title: '確認刪除',
          content: `確定要刪除事件「${event.title}」嗎？`,
          okText: '刪除',
          okButtonProps: { danger: true },
          cancelText: '取消',
          onOk: async () => {
            await handleEventDelete(event.id);
            message.success('事件已刪除');
          }
        });
      }
    }
  ];

  // 側邊欄使用的選中日期事件
  const selectedDateEvents = getEventsForDate(selectedDate);

  // ============================================================================
  // 側邊欄內容（共用於桌面版和行動版抽屜）
  // ============================================================================
  const renderSidebarContent = () => (
    <div style={{ maxHeight: isMobile ? 'calc(100vh - 120px)' : '600px', overflowY: 'auto' }}>
      {selectedDateEvents.length > 0 ? (
        selectedDateEvents.map((event) => (
          <Card
            key={event.id}
            size="small"
            style={{ marginBottom: 8 }}
            hoverable
            extra={
              <Dropdown menu={{ items: getEventActionMenu(event) }} trigger={['click']}>
                <Button type="text" size="small" icon={<MoreOutlined />} />
              </Dropdown>
            }
          >
            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>
                {event.title}
              </Text>
              <Text
                type="secondary"
                style={{ fontSize: '12px', display: 'block' }}
              >
                {dayjs(event.start_datetime).format('HH:mm')} -
                {dayjs(event.end_datetime).format('HH:mm')}
              </Text>
              <Space style={{ marginTop: 4 }} wrap>
                <Tag color={getEventColor(event.event_type)}>
                  {categories.find((c: EventCategory) => c.value === event.event_type)
                    ?.label || '提醒'}
                </Tag>
                {getPriorityTag(event.priority)}
                {event.google_event_id && (
                  <Tag color="blue" icon={<GoogleOutlined />}>
                    已同步
                  </Tag>
                )}
              </Space>
              {event.description && (
                <Text
                  type="secondary"
                  style={{ fontSize: '12px', display: 'block', marginTop: 4 }}
                >
                  {event.description.substring(0, 50)}
                  {event.description.length > 50 ? '...' : ''}
                </Text>
              )}
              {event.doc_number && (
                <Text
                  type="secondary"
                  style={{ fontSize: '11px', display: 'block' }}
                >
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
  );

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <div style={{ padding: pagePadding }}>
      {/* 標題列 */}
      <Row gutter={[8, 8]} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Title level={isMobile ? 4 : 2} style={{ marginBottom: 0 }}>
            <CalendarOutlined style={{ marginRight: 8 }} />
            {isMobile ? '行事曆' : '行事曆管理'}
          </Title>
        </Col>
        <Col>
          <Space size={isMobile ? 4 : 8} wrap>
            {/* 行動版：顯示側邊欄切換按鈕 */}
            {isMobile && (
              <Button
                type="default"
                icon={<MenuOutlined />}
                onClick={() => setSidebarVisible(true)}
              >
                {selectedDateEvents.length > 0 && (
                  <Tag color="blue" style={{ marginLeft: 4 }}>
                    {selectedDateEvents.length}
                  </Tag>
                )}
              </Button>
            )}
            {googleStatus && (
              <>
                {!isMobile && (
                  <Tag
                    color={googleStatus.google_calendar_available ? 'success' : 'default'}
                    icon={googleStatus.google_calendar_available ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                  >
                    <GoogleOutlined style={{ marginRight: 4 }} />
                    {googleStatus.google_calendar_available ? '已連接 Google' : '未連接'}
                  </Tag>
                )}
                <Button
                  size={isMobile ? 'middle' : 'small'}
                  type="primary"
                  icon={<SyncOutlined spin={isSyncing} />}
                  loading={isSyncing}
                  onClick={handleBulkSync}
                >
                  {isMobile ? '' : '同步'}
                </Button>
              </>
            )}
          </Space>
        </Col>
      </Row>

      {/* 主要內容區 */}
      <Row gutter={[16, 16]}>
        {/* 行事曆區域 - 響應式寬度 */}
        <Col xs={24} md={24} lg={18} xl={18}>
          <EnhancedCalendarView
            events={calendarEvents.map((event) => ({
              id: event.id,
              title: event.title,
              description: event.description,
              start_date: event.start_datetime,
              end_date: event.end_datetime,
              event_type: (event.event_type || 'reminder') as
                | 'deadline'
                | 'meeting'
                | 'review'
                | 'reminder'
                | 'reference',
              priority: typeof event.priority === 'number' ? event.priority : 3,
              status: 'pending' as const,
              document_id: event.document_id,
              google_event_id: event.google_event_id,
              google_sync_status: event.google_sync_status,
              reminder_enabled: true,
              reminders: [],
            }))}
            loading={loading}
            onEventUpdate={handleEventUpdate}
            onEventDelete={handleEventDelete}
            onDateSelect={(date) => {
              setSelectedDate(date);
              // 行動版：選擇日期後自動開啟側邊欄
              if (isMobile) {
                setSidebarVisible(true);
              }
            }}
            onRefresh={refetch}
          />
        </Col>

        {/* 桌面版側邊事件列表 - lg 以上顯示 */}
        {!isMobile && (
          <Col xs={0} md={0} lg={6} xl={6}>
            <Card
              title={`${selectedDate.format('MM/DD')} 事件 (${selectedDateEvents.length})`}
              style={{ height: '100%' }}
            >
              {renderSidebarContent()}
            </Card>
          </Col>
        )}
      </Row>

      {/* 行動版側邊欄抽屜 */}
      <Drawer
        title={
          <Space>
            <CalendarOutlined />
            {selectedDate.format('MM/DD')} 事件 ({selectedDateEvents.length})
          </Space>
        }
        placement="right"
        onClose={() => setSidebarVisible(false)}
        open={sidebarVisible}
        width={isMobile ? '85%' : 350}
        styles={{
          body: { padding: '12px' }
        }}
      >
        {renderSidebarContent()}
      </Drawer>
    </div>
  );
};

export default CalendarPage;
