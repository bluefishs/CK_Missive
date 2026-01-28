/**
 * 整合式事件建立模態框
 * 在公文頁面一站式完成：事件建立 + 提醒設定 + Google 同步
 *
 * @version 2.0.0 - 模組化重構：Hook + 子元件提取
 * @date 2026-01-28
 */
import React from 'react';
import {
  Modal, Form, Input, Select, DatePicker, Switch,
  Row, Col, Space, Button, Spin, Card,
  List, Tag, Tooltip, Typography,
} from 'antd';
import {
  BellOutlined, CalendarOutlined, AlertOutlined, PlusOutlined,
  DeleteOutlined, MailOutlined, NotificationOutlined, GoogleOutlined,
  ClockCircleOutlined, EnvironmentOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { useIntegratedEvent } from './integrated/useIntegratedEvent';
import type { IntegratedEventModalProps } from './integrated/types';
import {
  EVENT_TYPE_OPTIONS,
  PRIORITY_OPTIONS,
  REMINDER_TIME_OPTIONS,
  REMINDER_TYPE_OPTIONS,
} from './integrated/types';

const { TextArea } = Input;
const { Text } = Typography;

export const IntegratedEventModal: React.FC<IntegratedEventModalProps> = ({
  visible,
  document,
  onClose,
  onSuccess,
}) => {
  const {
    form,
    isMobile,
    loading,
    allDay,
    setAllDay,
    reminderEnabled,
    setReminderEnabled,
    syncToGoogle,
    setSyncToGoogle,
    reminders,
    newReminderMinutes,
    setNewReminderMinutes,
    newReminderType,
    setNewReminderType,
    existingEvents,
    handleAddReminder,
    handleRemoveReminder,
    getReminderLabel,
    handleSubmit,
  } = useIntegratedEvent(visible, document, onClose, onSuccess);

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
      forceRender
      footer={[
        <Button key="cancel" onClick={onClose}>取消</Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          建立事件
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical">
          {/* 已存在事件警告 */}
          {existingEvents.length > 0 && (
            <Card
              size="small"
              style={{ marginBottom: 16, borderColor: '#faad14', background: '#fffbe6' }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong style={{ color: '#d48806' }}>
                  <AlertOutlined /> 此公文已有 {existingEvents.length} 筆行事曆事件
                </Text>
                <div style={{ maxHeight: 100, overflowY: 'auto' }}>
                  {existingEvents.map(e => (
                    <div key={e.id} style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      • {dayjs(e.start_date).format('YYYY-MM-DD HH:mm')} - {e.title.slice(0, 30)}...
                    </div>
                  ))}
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  如果只是要修改日期，建議直接編輯現有事件。
                </Text>
              </Space>
            </Card>
          )}

          {/* 基本資訊 */}
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
                        {opt.label}
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

          {/* 提醒設定 */}
          <Card
            size="small"
            title={
              <Space>
                <BellOutlined />
                <span>提醒設定</span>
                <Switch size="small" checked={reminderEnabled} onChange={setReminderEnabled} />
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            {reminderEnabled ? (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
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
                        options={REMINDER_TIME_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
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
                            <Space size="small">
                              {type.value === 'system' ? <NotificationOutlined /> : <MailOutlined />}
                              {!isMobile && type.label}
                            </Space>
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
                            <Tooltip title="移除" key="remove">
                              <Button
                                type="text"
                                danger
                                size="small"
                                icon={<DeleteOutlined />}
                                onClick={() => handleRemoveReminder(index)}
                              />
                            </Tooltip>,
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

          {/* Google 同步 */}
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
