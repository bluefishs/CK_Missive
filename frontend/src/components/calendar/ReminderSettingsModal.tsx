/**
 * 提醒設定模態框
 * 用於設定和管理日曆事件的提醒功能
 */
import React, { useState, useEffect } from 'react';
import { logger } from '../../services/logger';
import {
  Modal, Select, Button, Space,
  List, Tag, Tooltip, notification, Empty, Spin, Typography, Row, Col, Grid
} from 'antd';

const { useBreakpoint } = Grid;
import {
  BellOutlined, DeleteOutlined, PlusOutlined,
  MailOutlined, NotificationOutlined, ClockCircleOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { apiClient } from '../../api/client';
import type { CalendarEvent } from '../../types/api';

const { Text } = Typography;

/** 提醒設定專用的事件提醒型別（包含 reminder_type 欄位） */
interface EventReminder {
  id: number;
  reminder_time: string;
  reminder_type: string;  // 此元件使用 reminder_type 而非 notification_type
  status: 'pending' | 'sent' | 'failed';
  is_sent: boolean;
  retry_count: number;
  message?: string;
}

/** 提醒設定用的事件型別（CalendarEvent 的子集） */
type ReminderEvent = Pick<CalendarEvent, 'id' | 'title' | 'start_date' | 'reminder_enabled'>;

interface ReminderSettingsModalProps {
  visible: boolean;
  event: ReminderEvent | null;
  onClose: () => void;
  onSuccess?: () => void;
}

const REMINDER_TIMES = [
  { value: 0, label: '事件開始時' },
  { value: 5, label: '5 分鐘前' },
  { value: 15, label: '15 分鐘前' },
  { value: 30, label: '30 分鐘前' },
  { value: 60, label: '1 小時前' },
  { value: 120, label: '2 小時前' },
  { value: 1440, label: '1 天前' },
  { value: 2880, label: '2 天前' },
  { value: 10080, label: '1 週前' }
];

const REMINDER_TYPES = [
  { value: 'email', label: '郵件通知', icon: <MailOutlined /> },
  { value: 'system', label: '系統通知', icon: <NotificationOutlined /> }
];

export const ReminderSettingsModal: React.FC<ReminderSettingsModalProps> = ({
  visible,
  event,
  onClose,
  onSuccess
}) => {
  // 注意：此元件不使用 Form，移除未使用的 useForm 避免 Antd 警告
  const [loading, setLoading] = useState(false);
  const [reminders, setReminders] = useState<EventReminder[]>([]);
  const [newReminderMinutes, setNewReminderMinutes] = useState<number>(60);
  const [newReminderType, setNewReminderType] = useState<string>('email');

  // 響應式斷點
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  // 載入現有提醒設定
  useEffect(() => {
    if (visible && event) {
      loadReminders();
    }
  }, [visible, event]);

  const loadReminders = async () => {
    if (!event) return;

    setLoading(true);
    try {
      const response = await apiClient.post<{ success: boolean; reminders?: EventReminder[] }>(
        `/reminder-management/events/${event.id}/reminders`,
        {}
      );
      if (response.success && response.reminders) {
        setReminders(response.reminders);
      }
    } catch (error) {
      logger.error('Failed to load reminders:', error);
      // 如果 API 失敗，使用空陣列
      setReminders([]);
    } finally {
      setLoading(false);
    }
  };

  // 新增提醒
  const handleAddReminder = async () => {
    if (!event) return;

    setLoading(true);
    try {
      const eventTime = dayjs(event.start_date);
      const reminderTime = eventTime.subtract(newReminderMinutes, 'minute');

      const response = await apiClient.post<{ success: boolean }>(
        `/reminder-management/events/${event.id}/reminders/update-template`,
        {
          reminder_type: newReminderType,
          reminder_minutes: newReminderMinutes,
          reminder_time: reminderTime.toISOString(),
          action: 'add'
        }
      );

      if (response.success) {
        notification.success({ message: '提醒已新增' });
        await loadReminders();
        onSuccess?.();
      }
    } catch (error: unknown) {
      logger.error('Failed to add reminder:', error);
      notification.error({
        message: '新增提醒失敗',
        description: error instanceof Error ? error.message : '請稍後再試'
      });
    } finally {
      setLoading(false);
    }
  };

  // 刪除提醒
  const handleDeleteReminder = async (reminderId: number) => {
    if (!event) return;

    setLoading(true);
    try {
      const response = await apiClient.post<{ success: boolean }>(
        `/reminder-management/events/${event.id}/reminders/update-template`,
        {
          reminder_id: reminderId,
          action: 'delete'
        }
      );

      if (response.success) {
        notification.success({ message: '提醒已刪除' });
        await loadReminders();
        onSuccess?.();
      }
    } catch (error: unknown) {
      logger.error('Failed to delete reminder:', error);
      notification.error({
        message: '刪除提醒失敗',
        description: error instanceof Error ? error.message : '請稍後再試'
      });
    } finally {
      setLoading(false);
    }
  };

  // 發送測試提醒
  const handleSendTestReminder = async () => {
    if (!event) return;

    setLoading(true);
    try {
      const response = await apiClient.post<{ success: boolean }>(
        '/reminder-management/send-test-reminder',
        {
          event_id: event.id,
          reminder_type: 'email'
        }
      );

      if (response.success) {
        notification.success({ message: '測試提醒已發送' });
      }
    } catch (error: unknown) {
      logger.error('Failed to send test reminder:', error);
      notification.error({
        message: '發送測試提醒失敗',
        description: error instanceof Error ? error.message : '請稍後再試'
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusTag = (status: string, isSent: boolean) => {
    if (isSent) {
      return <Tag color="success" icon={<CheckCircleOutlined />}>已發送</Tag>;
    }
    switch (status) {
      case 'pending':
        return <Tag color="processing" icon={<ClockCircleOutlined />}>待發送</Tag>;
      case 'sent':
        return <Tag color="success" icon={<CheckCircleOutlined />}>已發送</Tag>;
      case 'failed':
        return <Tag color="error" icon={<ExclamationCircleOutlined />}>發送失敗</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  return (
    <Modal
      title={
        <Space>
          <BellOutlined />
          <span>提醒設定</span>
          {event && !isMobile && <Text type="secondary">- {event.title.substring(0, 30)}{event.title.length > 30 && '...'}</Text>}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={isMobile ? '95%' : 600}
      style={{ maxWidth: '95vw' }}
      footer={[
        <Button key="test" onClick={handleSendTestReminder} loading={loading}>
          {isMobile ? '測試' : '發送測試提醒'}
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>
          完成
        </Button>
      ]}
    >
      <Spin spinning={loading}>
        {event ? (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* 事件資訊 */}
            <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
              <Text strong>事件時間：</Text>
              <Text>{dayjs(event.start_date).format('YYYY-MM-DD HH:mm')}</Text>
            </div>

            {/* 新增提醒 */}
            <div>
              <Text strong style={{ marginBottom: '8px', display: 'block' }}>新增提醒：</Text>
              <Row gutter={8}>
                <Col span={10}>
                  <Select
                    value={newReminderMinutes}
                    onChange={setNewReminderMinutes}
                    style={{ width: '100%' }}
                    options={REMINDER_TIMES}
                  />
                </Col>
                <Col span={8}>
                  <Select
                    value={newReminderType}
                    onChange={setNewReminderType}
                    style={{ width: '100%' }}
                  >
                    {REMINDER_TYPES.map(type => (
                      <Select.Option key={type.value} value={type.value}>
                        <Space>{type.icon}{type.label}</Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Col>
                <Col span={6}>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleAddReminder}
                    style={{ width: '100%' }}
                  >
                    新增
                  </Button>
                </Col>
              </Row>
            </div>

            {/* 現有提醒列表 */}
            <div>
              <Text strong style={{ marginBottom: '8px', display: 'block' }}>現有提醒：</Text>
              {reminders.length > 0 ? (
                <List
                  size="small"
                  dataSource={reminders}
                  renderItem={(reminder) => (
                    <List.Item
                      actions={[
                        <Tooltip title="刪除提醒">
                          <Button
                            type="text"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={() => handleDeleteReminder(reminder.id)}
                            size="small"
                          />
                        </Tooltip>
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          reminder.reminder_type === 'email' ? (
                            <MailOutlined style={{ fontSize: '20px', color: '#1890ff' }} />
                          ) : (
                            <NotificationOutlined style={{ fontSize: '20px', color: '#52c41a' }} />
                          )
                        }
                        title={
                          <Space>
                            <Text>{dayjs(reminder.reminder_time).format('YYYY-MM-DD HH:mm')}</Text>
                            {getStatusTag(reminder.status, reminder.is_sent)}
                          </Space>
                        }
                        description={
                          <Space>
                            <Tag>{reminder.reminder_type === 'email' ? '郵件' : '系統'}</Tag>
                            {reminder.retry_count > 0 && (
                              <Text type="warning">重試 {reminder.retry_count} 次</Text>
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="尚未設定提醒" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </Space>
        ) : (
          <Empty description="請選擇一個事件" />
        )}
      </Spin>
    </Modal>
  );
};

export default ReminderSettingsModal;
