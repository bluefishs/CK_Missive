/**
 * 日曆事件表單模態框
 * 用於新增和編輯日曆事件 (符合 POST 資安機制)
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal, Form, Input, Select, DatePicker, Switch,
  Row, Col, Space, Button, Spin, Divider, Grid, App
} from 'antd';

const { useBreakpoint } = Grid;
import {
  BellOutlined, CalendarOutlined, AlertOutlined,
  EyeOutlined, UnorderedListOutlined, FileTextOutlined
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { apiClient } from '../../api/client';
import debounce from 'lodash/debounce';

const { TextArea } = Input;

interface EventFormData {
  title: string;
  description?: string;
  start_date: Dayjs;
  end_date?: Dayjs;
  all_day: boolean;
  event_type: string;
  priority: number;
  location?: string;
  document_id?: number;
  assigned_user_id?: number;
  reminder_enabled?: boolean;
  reminder_minutes?: number;
}

interface CalendarEvent {
  id: number;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  all_day: boolean;
  event_type: string;
  priority: string | number;
  location?: string;
  document_id?: number;
  doc_number?: string;
  assigned_user_id?: number;
}

// 公文選項介面
interface DocumentOption {
  id: number;
  doc_number: string;
  subject: string;
}

interface EventFormModalProps {
  visible: boolean;
  mode: 'create' | 'edit';
  event?: CalendarEvent | null;
  onClose: () => void;
  onSuccess: () => void;
}

const EVENT_TYPE_OPTIONS = [
  { value: 'deadline', label: '截止提醒', icon: <AlertOutlined style={{ color: '#f5222d' }} /> },
  { value: 'meeting', label: '會議安排', icon: <CalendarOutlined style={{ color: '#722ed1' }} /> },
  { value: 'review', label: '審核提醒', icon: <EyeOutlined style={{ color: '#1890ff' }} /> },
  { value: 'reminder', label: '一般提醒', icon: <BellOutlined style={{ color: '#fa8c16' }} /> },
  { value: 'reference', label: '參考事件', icon: <UnorderedListOutlined style={{ color: '#666' }} /> }
];

const PRIORITY_OPTIONS = [
  { value: 1, label: '緊急', color: '#f5222d' },
  { value: 2, label: '重要', color: '#fa8c16' },
  { value: 3, label: '普通', color: '#1890ff' },
  { value: 4, label: '低', color: '#52c41a' },
  { value: 5, label: '最低', color: '#d9d9d9' }
];

export const EventFormModal: React.FC<EventFormModalProps> = ({
  visible,
  mode,
  event,
  onClose,
  onSuccess
}) => {
  const [form] = Form.useForm();
  const { notification, modal } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [allDay, setAllDay] = useState(false);
  const [documentOptions, setDocumentOptions] = useState<DocumentOption[]>([]);
  const [documentSearchError, setDocumentSearchError] = useState<string | null>(null);
  const [existingEventsWarning, setExistingEventsWarning] = useState<string | null>(null);

  // 響應式斷點
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [documentSearching, setDocumentSearching] = useState(false);

  // 檢查公文是否已有行事曆事件
  const checkDocumentEvents = async (documentId: number) => {
    try {
      const response = await apiClient.post<{
        has_events: boolean;
        event_count: number;
        events: Array<{ id: number; title: string; start_date: string }>;
        message: string;
      }>('/calendar/events/check-document', { document_id: documentId });

      if (response.has_events && response.event_count > 0) {
        setExistingEventsWarning(
          `此公文已有 ${response.event_count} 筆行事曆事件。建立新事件可能造成重複。`
        );
        notification.warning({
          message: '公文已有事件',
          description: `此公文已有 ${response.event_count} 筆行事曆事件，建議先確認是否需要新增。`,
          duration: 5,
        });
      } else {
        setExistingEventsWarning(null);
      }
    } catch (error) {
      console.error('檢查公文事件失敗:', error);
      // 靜默失敗，不影響使用者操作
    }
  };

  // 處理關聯公文選擇變更
  const handleDocumentChange = (value: number | undefined) => {
    setExistingEventsWarning(null);
    if (value && mode === 'create') {
      checkDocumentEvents(value);
    }
  };

  // 搜尋公文（防抖動）
  const searchDocuments = useCallback(
    debounce(async (keyword: string) => {
      setDocumentSearchError(null);

      if (!keyword || keyword.length < 2) {
        setDocumentOptions([]);
        return;
      }

      setDocumentSearching(true);
      try {
        const response = await apiClient.post<{
          success: boolean;
          items: Array<{
            id: number;
            doc_number: string;
            subject?: string;
          }>;
        }>('/documents-enhanced/list', {
          keyword,
          limit: 20,
          page: 1
        });

        if (response.success && response.items) {
          setDocumentOptions(response.items.map(doc => ({
            id: doc.id,
            doc_number: doc.doc_number,
            subject: doc.subject || ''
          })));
          if (response.items.length === 0) {
            setDocumentSearchError('找不到符合的公文');
          }
        } else {
          setDocumentSearchError('搜尋失敗，請稍後再試');
        }
      } catch (error) {
        console.error('搜尋公文失敗:', error);
        setDocumentSearchError('搜尋時發生錯誤');
        notification.error({
          message: '搜尋公文失敗',
          description: '請檢查網路連線或稍後再試',
          duration: 3,
        });
      } finally {
        setDocumentSearching(false);
      }
    }, 300),
    [notification]
  );

  // 初始化表單數據
  useEffect(() => {
    if (visible && mode === 'edit' && event) {
      form.setFieldsValue({
        title: event.title,
        description: event.description,
        start_date: dayjs(event.start_date),
        end_date: event.end_date ? dayjs(event.end_date) : undefined,
        all_day: event.all_day,
        event_type: event.event_type,
        priority: typeof event.priority === 'string' ? parseInt(event.priority) : event.priority,
        location: event.location,
        document_id: event.document_id,
        assigned_user_id: event.assigned_user_id
      });
      setAllDay(event.all_day);
      // 如果有關聯公文，預載公文選項
      if (event.document_id && event.doc_number) {
        setDocumentOptions([{
          id: event.document_id,
          doc_number: event.doc_number,
          subject: ''
        }]);
      }
    } else if (visible && mode === 'create') {
      form.resetFields();
      form.setFieldsValue({
        event_type: 'reminder',
        priority: 3,
        all_day: false,
        start_date: dayjs()
      });
      setAllDay(false);
      setDocumentOptions([]);
      setExistingEventsWarning(null);
    }
  }, [visible, mode, event, form]);

  // 提交表單
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const submitData = {
        title: values.title,
        description: values.description || null,
        start_date: values.start_date.toISOString(),
        end_date: values.end_date?.toISOString() || null,
        all_day: values.all_day || false,
        event_type: values.event_type,
        priority: values.priority,
        location: values.location || null,
        document_id: values.document_id || null,
        assigned_user_id: values.assigned_user_id || null
      };

      if (mode === 'create') {
        // 新增事件 (POST /api/calendar/events)
        const response = await apiClient.post<{ success: boolean; message: string }>(
          '/calendar/events',
          submitData
        );
        if (response.success) {
          notification.success({ message: '事件建立成功' });
          onSuccess();
          onClose();
        } else {
          throw new Error(response.message || '建立失敗');
        }
      } else if (mode === 'edit' && event) {
        // 更新事件 (POST /api/calendar/events/update)
        const response = await apiClient.post<{ success: boolean; message: string }>(
          '/calendar/events/update',
          {
            event_id: event.id,
            ...submitData
          }
        );
        if (response.success) {
          notification.success({ message: '事件更新成功' });
          onSuccess();
          onClose();
        } else {
          throw new Error(response.message || '更新失敗');
        }
      }
    } catch (error: any) {
      console.error('Error submitting event:', error);
      notification.error({
        message: mode === 'create' ? '建立事件失敗' : '更新事件失敗',
        description: error.message || '請稍後再試'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={mode === 'create' ? '新增日曆事件' : '編輯日曆事件'}
      open={visible}
      onCancel={onClose}
      width={isMobile ? '95%' : 700}
      style={{ maxWidth: '95vw' }}
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
          {mode === 'create' ? '建立' : '儲存'}
        </Button>
      ]}
    >
      <Spin spinning={loading}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            event_type: 'reminder',
            priority: 3,
            all_day: false
          }}
        >
          <Form.Item
            name="title"
            label="事件標題"
            rules={[{ required: true, message: '請輸入事件標題' }]}
          >
            <Input placeholder="輸入事件標題" maxLength={200} showCount />
          </Form.Item>

          <Form.Item
            name="description"
            label="事件描述"
          >
            <TextArea rows={3} placeholder="輸入事件描述（選填）" maxLength={1000} showCount />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
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
            <Col span={12}>
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
            <Col span={8}>
              <Form.Item
                name="all_day"
                label="全天事件"
                valuePropName="checked"
              >
                <Switch onChange={setAllDay} />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item
                name="location"
                label="地點"
              >
                <Input placeholder="輸入地點（選填）" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
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
            <Col span={12}>
              <Form.Item
                name="end_date"
                label="結束時間"
              >
                <DatePicker
                  showTime={!allDay}
                  format={allDay ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm'}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" plain>
            <Space><FileTextOutlined />關聯公文</Space>
          </Divider>

          <Form.Item
            name="document_id"
            label="關聯公文"
            tooltip="輸入公文字號或主旨關鍵字搜尋（至少2個字元）"
            help={
              existingEventsWarning ? (
                <span style={{ color: '#fa8c16' }}>{existingEventsWarning}</span>
              ) : documentSearchError && !documentSearching ? (
                <span style={{ color: '#faad14' }}>{documentSearchError}</span>
              ) : undefined
            }
          >
            <Select
              showSearch
              allowClear
              placeholder="輸入公文字號或主旨搜尋..."
              filterOption={false}
              onSearch={searchDocuments}
              onChange={handleDocumentChange}
              loading={documentSearching}
              notFoundContent={
                documentSearching ? (
                  <div style={{ textAlign: 'center', padding: 8 }}>
                    <Spin size="small" />
                    <div style={{ marginTop: 4, color: '#888' }}>搜尋中...</div>
                  </div>
                ) : documentSearchError ? (
                  <div style={{ textAlign: 'center', padding: 8, color: '#faad14' }}>
                    {documentSearchError}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 8, color: '#888' }}>
                    輸入至少2個字元搜尋
                  </div>
                )
              }
              optionLabelProp="label"
              status={documentSearchError ? 'warning' : undefined}
            >
              {documentOptions.map(doc => (
                <Select.Option
                  key={doc.id}
                  value={doc.id}
                  label={doc.doc_number}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>{doc.doc_number}</div>
                    {doc.subject && (
                      <div style={{ fontSize: 12, color: '#888', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 250 }}>
                        {doc.subject}
                      </div>
                    )}
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  );
};

export default EventFormModal;
