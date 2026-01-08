/**
 * 整合式事件建立模態框
 * 在公文頁面一站式完成：事件建立 + 提醒設定 + Google 同步
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal, Form, Input, Select, DatePicker, Switch, InputNumber,
  Row, Col, Space, Button, notification, Spin, Divider, Card,
  List, Tag, Tooltip, Typography, Grid, Collapse
} from 'antd';

const { useBreakpoint } = Grid;
const { Panel } = Collapse;
import {
  BellOutlined, CalendarOutlined, AlertOutlined, PlusOutlined,
  DeleteOutlined, MailOutlined, NotificationOutlined, GoogleOutlined,
  FileTextOutlined, ClockCircleOutlined, EnvironmentOutlined
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { apiClient } from '../../api/client';
import debounce from 'lodash/debounce';

const { TextArea } = Input;
const { Text } = Typography;

// ============================================================================
// 型別定義
// ============================================================================

interface ReminderConfig {
  minutes_before: number;
  notification_type: 'email' | 'system';
}

interface DocumentInfo {
  id: number;
  doc_number?: string;
  subject?: string;
  doc_date?: string;
  send_date?: string;
  receive_date?: string;
  sender?: string;
  receiver?: string;
  assignee?: string;
  priority_level?: string;
  doc_type?: string;
  content?: string;
  notes?: string;
  contract_case?: string;
}

interface IntegratedEventModalProps {
  visible: boolean;
  document?: DocumentInfo | null;
  onClose: () => void;
  onSuccess?: (eventId: number) => void;
}

// ============================================================================
// 常數定義
// ============================================================================

const EVENT_TYPE_OPTIONS = [
  { value: 'deadline', label: '截止提醒', icon: <AlertOutlined style={{ color: '#f5222d' }} /> },
  { value: 'meeting', label: '會議安排', icon: <CalendarOutlined style={{ color: '#722ed1' }} /> },
  { value: 'review', label: '審核提醒', icon: <ClockCircleOutlined style={{ color: '#1890ff' }} /> },
  { value: 'reminder', label: '一般提醒', icon: <BellOutlined style={{ color: '#fa8c16' }} /> },
  { value: 'reference', label: '參考事件', icon: <FileTextOutlined style={{ color: '#666' }} /> }
];

const PRIORITY_OPTIONS = [
  { value: 1, label: '緊急', color: '#f5222d' },
  { value: 2, label: '重要', color: '#fa8c16' },
  { value: 3, label: '普通', color: '#1890ff' },
  { value: 4, label: '低', color: '#52c41a' },
  { value: 5, label: '最低', color: '#d9d9d9' }
];

const REMINDER_TIME_OPTIONS = [
  { value: 0, label: '事件開始時' },
  { value: 5, label: '5 分鐘前' },
  { value: 15, label: '15 分鐘前' },
  { value: 30, label: '30 分鐘前' },
  { value: 60, label: '1 小時前' },
  { value: 120, label: '2 小時前' },
  { value: 480, label: '8 小時前' },
  { value: 1440, label: '1 天前' },
  { value: 2880, label: '2 天前' },
  { value: 10080, label: '1 週前' }
];

const REMINDER_TYPE_OPTIONS = [
  { value: 'system', label: '系統通知', icon: <NotificationOutlined /> },
  { value: 'email', label: '郵件通知', icon: <MailOutlined /> }
];

// ============================================================================
// 主元件
// ============================================================================

export const IntegratedEventModal: React.FC<IntegratedEventModalProps> = ({
  visible,
  document,
  onClose,
  onSuccess
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [allDay, setAllDay] = useState(true);
  const [reminderEnabled, setReminderEnabled] = useState(true);
  const [syncToGoogle, setSyncToGoogle] = useState(false);
  const [reminders, setReminders] = useState<ReminderConfig[]>([
    { minutes_before: 1440, notification_type: 'system' }  // 預設 1 天前系統通知
  ]);
  const [newReminderMinutes, setNewReminderMinutes] = useState<number>(60);
  const [newReminderType, setNewReminderType] = useState<'email' | 'system'>('system');

  // 響應式斷點
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  // ============================================================================
  // 輔助函數
  // ============================================================================

  /** 根據公文內容判斷事件類型 */
  const determineEventType = useCallback((doc: DocumentInfo): string => {
    const content = (doc.content || '').toLowerCase();
    const subject = (doc.subject || '').toLowerCase();
    const docType = (doc.doc_type || '').toLowerCase();

    if (docType.includes('會議') || content.includes('會議') || subject.includes('會議')) {
      return 'meeting';
    }
    if (content.includes('審查') || content.includes('審核') || subject.includes('審查')) {
      return 'review';
    }
    if (content.includes('截止') || content.includes('期限') || subject.includes('截止')) {
      return 'deadline';
    }
    return 'reminder';
  }, []);

  /** 根據公文內容判斷優先級 */
  const determinePriority = useCallback((doc: DocumentInfo): number => {
    if (doc.priority_level) {
      const num = parseInt(doc.priority_level, 10);
      if (num >= 1 && num <= 5) return num;
    }
    const docType = (doc.doc_type || '').toLowerCase();
    if (docType.includes('急件') || docType.includes('特急')) return 1;
    if (docType.includes('會議')) return 2;
    return 3;
  }, []);

  /** 確定事件日期 */
  const determineEventDate = useCallback((doc: DocumentInfo): Dayjs => {
    if (doc.send_date) return dayjs(doc.send_date);
    if (doc.receive_date) return dayjs(doc.receive_date);
    if (doc.doc_date) return dayjs(doc.doc_date);
    return dayjs();
  }, []);

  /** 構建事件描述 */
  const buildDescription = useCallback((doc: DocumentInfo): string => {
    const parts = [
      `公文字號: ${doc.doc_number || '未指定'}`,
      `主旨: ${doc.subject || '未指定'}`,
      `發文單位: ${doc.sender || '未知'}`,
    ];
    if (doc.receiver) parts.push(`受文者: ${doc.receiver}`);
    if (doc.contract_case) parts.push(`關聯案件: ${doc.contract_case}`);
    if (doc.assignee) parts.push(`業務同仁: ${doc.assignee}`);
    if (doc.notes) parts.push(`備註: ${doc.notes}`);
    return parts.join('\n');
  }, []);

  // ============================================================================
  // 初始化表單
  // ============================================================================

  useEffect(() => {
    if (visible && document) {
      const eventType = determineEventType(document);
      const eventDate = determineEventDate(document);

      form.setFieldsValue({
        title: `公文提醒: ${document.subject || document.doc_number || '未命名'}`,
        description: buildDescription(document),
        start_date: eventDate,
        end_date: eventDate,
        all_day: true,
        event_type: eventType,
        priority: determinePriority(document),
        location: ''
      });

      setAllDay(true);
      setReminderEnabled(true);

      // 根據事件類型設定預設提醒
      const defaultMinutes = eventType === 'deadline' ? 1440 :
                            eventType === 'meeting' ? 60 :
                            eventType === 'review' ? 480 : 1440;
      setReminders([{ minutes_before: defaultMinutes, notification_type: 'system' }]);

    } else if (visible && !document) {
      // 無公文時的預設值
      form.resetFields();
      form.setFieldsValue({
        event_type: 'reminder',
        priority: 3,
        all_day: true,
        start_date: dayjs()
      });
      setAllDay(true);
      setReminders([{ minutes_before: 60, notification_type: 'system' }]);
    }
  }, [visible, document, form, determineEventType, determineEventDate, determinePriority, buildDescription]);

  // ============================================================================
  // 提醒管理
  // ============================================================================

  const handleAddReminder = () => {
    // 檢查是否已存在相同設定
    const exists = reminders.some(
      r => r.minutes_before === newReminderMinutes && r.notification_type === newReminderType
    );
    if (exists) {
      notification.warning({ message: '此提醒設定已存在' });
      return;
    }

    setReminders([...reminders, {
      minutes_before: newReminderMinutes,
      notification_type: newReminderType
    }]);
  };

  const handleRemoveReminder = (index: number) => {
    setReminders(reminders.filter((_, i) => i !== index));
  };

  const getReminderLabel = (minutes: number): string => {
    const option = REMINDER_TIME_OPTIONS.find(o => o.value === minutes);
    return option?.label || `${minutes} 分鐘前`;
  };

  // ============================================================================
  // 提交表單
  // ============================================================================

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 準備提交資料
      const submitData = {
        title: values.title,
        description: values.description || null,
        start_date: values.start_date.toISOString(),
        end_date: values.end_date?.toISOString() || values.start_date.toISOString(),
        all_day: values.all_day || false,
        event_type: values.event_type,
        priority: values.priority,
        location: values.location || null,
        document_id: document?.id || null,
        reminder_enabled: reminderEnabled,
        // 新增: 提醒設定列表
        reminders: reminderEnabled ? reminders : [],
        // 新增: Google 同步選項
        sync_to_google: syncToGoogle
      };

      // 呼叫後端 API
      const response = await apiClient.post<{
        success: boolean;
        message: string;
        event_id?: number;
        google_event_id?: string;
      }>('/calendar/events/create-with-reminders', submitData);

      if (response.success) {
        notification.success({
          message: '事件建立成功',
          description: response.google_event_id
            ? '已同步至 Google Calendar'
            : '事件已建立，提醒已設定'
        });
        onSuccess?.(response.event_id!);
        onClose();
      } else {
        throw new Error(response.message || '建立失敗');
      }

    } catch (error: any) {
      console.error('建立事件失敗:', error);
      notification.error({
        message: '建立事件失敗',
        description: error.message || '請稍後再試'
      });
    } finally {
      setLoading(false);
    }
  };

  // ============================================================================
  // 渲染
  // ============================================================================

  return (
    <Modal
      title={
        <Space>
          <CalendarOutlined />
          <span>新增行事曆事件</span>
          {document && <Tag color="blue">{document.doc_number}</Tag>}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={isMobile ? '95%' : 800}
      style={{ maxWidth: '95vw', top: 20 }}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={loading}
          onClick={handleSubmit}
        >
          建立事件
        </Button>
      ]}
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical">
          {/* ============ 基本資訊 ============ */}
          <Card
            size="small"
            title={<><CalendarOutlined /> 事件資訊</>}
            style={{ marginBottom: 16 }}
          >
            <Form.Item
              name="title"
              label="事件標題"
              rules={[{ required: true, message: '請輸入事件標題' }]}
            >
              <Input placeholder="輸入事件標題" maxLength={200} showCount />
            </Form.Item>

            <Form.Item name="description" label="事件描述">
              <TextArea rows={3} placeholder="輸入事件描述（選填）" maxLength={1000} />
            </Form.Item>

            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="event_type"
                  label="事件類型"
                  rules={[{ required: true, message: '請選擇事件類型' }]}
                >
                  <Select placeholder="選擇事件類型">
                    {EVENT_TYPE_OPTIONS.map(opt => (
                      <Select.Option key={opt.value} value={opt.value}>
                        <Space>{opt.icon}{opt.label}</Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="priority"
                  label="優先級"
                  rules={[{ required: true, message: '請選擇優先級' }]}
                >
                  <Select placeholder="選擇優先級">
                    {PRIORITY_OPTIONS.map(opt => (
                      <Select.Option key={opt.value} value={opt.value}>
                        <span style={{ color: opt.color }}>{opt.label}</span>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item name="all_day" label="全天事件" valuePropName="checked">
                  <Switch onChange={setAllDay} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={18}>
                <Form.Item name="location" label={<><EnvironmentOutlined /> 地點</>}>
                  <Input placeholder="輸入地點（選填）" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="start_date"
                  label="開始時間"
                  rules={[{ required: true, message: '請選擇開始時間' }]}
                >
                  <DatePicker
                    showTime={!allDay}
                    format={allDay ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm'}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="end_date" label="結束時間">
                  <DatePicker
                    showTime={!allDay}
                    format={allDay ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm'}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* ============ 提醒設定 ============ */}
          <Card
            size="small"
            title={
              <Space>
                <BellOutlined />
                <span>提醒設定</span>
                <Switch
                  size="small"
                  checked={reminderEnabled}
                  onChange={setReminderEnabled}
                />
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            {reminderEnabled ? (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {/* 新增提醒 */}
                <div>
                  <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                    新增提醒：
                  </Text>
                  <Row gutter={8}>
                    <Col xs={10} sm={8}>
                      <Select
                        value={newReminderMinutes}
                        onChange={setNewReminderMinutes}
                        style={{ width: '100%' }}
                        options={REMINDER_TIME_OPTIONS}
                      />
                    </Col>
                    <Col xs={8} sm={8}>
                      <Select
                        value={newReminderType}
                        onChange={setNewReminderType}
                        style={{ width: '100%' }}
                      >
                        {REMINDER_TYPE_OPTIONS.map(type => (
                          <Select.Option key={type.value} value={type.value}>
                            <Space size="small">{type.icon}{!isMobile && type.label}</Space>
                          </Select.Option>
                        ))}
                      </Select>
                    </Col>
                    <Col xs={6} sm={8}>
                      <Button
                        type="dashed"
                        icon={<PlusOutlined />}
                        onClick={handleAddReminder}
                        style={{ width: '100%' }}
                      >
                        {!isMobile && '新增'}
                      </Button>
                    </Col>
                  </Row>
                </div>

                {/* 已設定的提醒列表 */}
                {reminders.length > 0 && (
                  <div>
                    <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                      已設定的提醒：
                    </Text>
                    <List
                      size="small"
                      dataSource={reminders}
                      renderItem={(reminder, index) => (
                        <List.Item
                          actions={[
                            <Tooltip title="移除">
                              <Button
                                type="text"
                                danger
                                size="small"
                                icon={<DeleteOutlined />}
                                onClick={() => handleRemoveReminder(index)}
                              />
                            </Tooltip>
                          ]}
                        >
                          <Space>
                            {reminder.notification_type === 'email' ? (
                              <MailOutlined style={{ color: '#1890ff' }} />
                            ) : (
                              <NotificationOutlined style={{ color: '#52c41a' }} />
                            )}
                            <Tag color={reminder.notification_type === 'email' ? 'blue' : 'green'}>
                              {getReminderLabel(reminder.minutes_before)}
                            </Tag>
                            <Text type="secondary">
                              {reminder.notification_type === 'email' ? '郵件' : '系統'}通知
                            </Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </div>
                )}

                {reminders.length === 0 && (
                  <Text type="secondary">尚未設定提醒，請點擊「新增」按鈕添加</Text>
                )}
              </Space>
            ) : (
              <Text type="secondary">提醒功能已關閉</Text>
            )}
          </Card>

          {/* ============ Google 同步 ============ */}
          <Card
            size="small"
            title={
              <Space>
                <GoogleOutlined style={{ color: '#4285f4' }} />
                <span>Google Calendar 同步</span>
              </Space>
            }
          >
            <Space>
              <Switch checked={syncToGoogle} onChange={setSyncToGoogle} />
              <Text>
                {syncToGoogle
                  ? '建立事件後將自動同步至 Google Calendar'
                  : '僅儲存在本地系統'}
              </Text>
            </Space>
          </Card>
        </Form>
      </Spin>
    </Modal>
  );
};

export default IntegratedEventModal;
