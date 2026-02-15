/**
 * 日曆事件表單頁面（導航模式）
 *
 * 支援新建與編輯模式：
 * - 新建: /calendar/event/new (可帶 ?documentId=xxx query param)
 * - 編輯: /calendar/event/:id/edit
 *
 * @version 2.0.0
 * @date 2026-02-11
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { ResponsiveContent } from '../components/common';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Switch,
  Row,
  Col,
  Button,
  Space,
  Spin,
  Divider,
  App,
  Typography,
} from 'antd';
import {
  CalendarOutlined,
  BellOutlined,
  AlertOutlined,
  EyeOutlined,
  UnorderedListOutlined,
  FileTextOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { logger } from '../services/logger';

import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type { CalendarEvent } from '../api/calendarApi';
import { EVENT_TYPE_OPTIONS, PRIORITY_OPTIONS } from '../components/calendar/form/types';

const { TextArea } = Input;
const { Title } = Typography;

interface DocumentOption {
  id: number;
  doc_number: string;
  subject: string;
}

const EVENT_TYPE_ICONS: Record<string, React.ReactNode> = {
  deadline: <AlertOutlined style={{ color: '#f5222d' }} />,
  meeting: <CalendarOutlined style={{ color: '#722ed1' }} />,
  review: <EyeOutlined style={{ color: '#1890ff' }} />,
  reminder: <BellOutlined style={{ color: '#fa8c16' }} />,
  reference: <UnorderedListOutlined style={{ color: '#666' }} />,
};

const CalendarEventFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const { message, notification } = App.useApp();
  const queryClient = useQueryClient();

  // 判斷模式：無 id 或路徑含 /new = 新建模式
  const isNew = !id;

  // 從 location.state 或 query param 取得關聯公文 ID
  const returnTo = (location.state as { returnTo?: string })?.returnTo;
  const presetDocumentId = searchParams.get('documentId');

  // 本地狀態
  const [allDay, setAllDay] = useState(false);
  const [documentOptions, setDocumentOptions] = useState<DocumentOption[]>([]);
  const [documentSearching, setDocumentSearching] = useState(false);
  const [documentSearchError, setDocumentSearchError] = useState<string | null>(null);

  // 查詢事件資料（僅編輯模式）
  const { data: event, isLoading } = useQuery({
    queryKey: ['calendar-event', id],
    queryFn: async () => {
      const response = await apiClient.post<{
        success: boolean;
        event: Record<string, unknown>;
      }>(API_ENDPOINTS.CALENDAR.EVENTS_DETAIL, { event_id: parseInt(id || '0', 10) });
      const raw = response.event;
      return {
        ...raw,
        start_datetime: raw.start_date as string,
        end_datetime: raw.end_date as string,
      } as CalendarEvent;
    },
    enabled: !isNew && !!id,
  });

  // 建立事件 mutation
  const createMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const response = await apiClient.post<{ success: boolean; message: string; event_id?: number }>(
        API_ENDPOINTS.CALENDAR.EVENTS_CREATE,
        data
      );
      if (!response.success) {
        throw new Error(response.message || '建立失敗');
      }
      return response;
    },
    onSuccess: () => {
      message.success('事件建立成功');
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardCalendar'] });
      handleBack();
    },
    onError: (error: Error) => {
      notification.error({
        message: '建立事件失敗',
        description: error.message || '請稍後再試',
      });
    },
  });

  // 更新事件 mutation
  const updateMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const response = await apiClient.post<{ success: boolean; message: string }>(
        API_ENDPOINTS.CALENDAR.EVENTS_UPDATE,
        { event_id: parseInt(id || '0', 10), ...data }
      );
      if (!response.success) {
        throw new Error(response.message || '更新失敗');
      }
      return response;
    },
    onSuccess: () => {
      message.success('事件更新成功');
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardCalendar'] });
      handleBack();
    },
    onError: (error: Error) => {
      notification.error({
        message: '更新事件失敗',
        description: error.message || '請稍後再試',
      });
    },
  });

  const saveMutation = isNew ? createMutation : updateMutation;

  // 初始化表單（編輯模式）
  useEffect(() => {
    if (event && !isNew) {
      form.setFieldsValue({
        title: event.title,
        description: event.description,
        start_date: dayjs(event.start_datetime),
        end_date: event.end_datetime ? dayjs(event.end_datetime) : undefined,
        all_day: event.all_day ?? false,
        event_type: event.event_type || 'reminder',
        priority: typeof event.priority === 'string'
          ? parseInt(event.priority, 10)
          : (event.priority ?? 3),
        location: event.location,
        document_id: event.document_id,
      });
      setAllDay(event.all_day ?? false);
      if (event.document_id) {
        setDocumentOptions([{
          id: event.document_id,
          doc_number: event.doc_number || `公文 #${event.document_id}`,
          subject: '',
        }]);
      }
    }
  }, [event, form, isNew]);

  // 新建模式：預設關聯公文（從 query param）
  useEffect(() => {
    if (isNew && presetDocumentId) {
      const docId = parseInt(presetDocumentId, 10);
      if (!isNaN(docId)) {
        form.setFieldsValue({ document_id: docId });
        // 查詢公文資訊顯示在選項中
        apiClient.post<{
          success: boolean;
          items: Array<{ id: number; doc_number: string; subject?: string }>;
        }>(API_ENDPOINTS.DOCUMENTS.LIST, { keyword: '', limit: 1, page: 1, id: docId })
          .then(response => {
            const firstItem = response.items?.[0];
            if (response.success && firstItem) {
              setDocumentOptions([{
                id: firstItem.id,
                doc_number: firstItem.doc_number,
                subject: firstItem.subject || '',
              }]);
            } else {
              setDocumentOptions([{ id: docId, doc_number: `公文 #${docId}`, subject: '' }]);
            }
          })
          .catch(() => {
            setDocumentOptions([{ id: docId, doc_number: `公文 #${docId}`, subject: '' }]);
          });
      }
    }
  }, [isNew, presetDocumentId, form]);

  // 公文搜尋
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
        }>(API_ENDPOINTS.DOCUMENTS.LIST, {
          keyword,
          limit: 20,
          page: 1,
        });

        if (response.success && response.items) {
          setDocumentOptions(response.items.map(doc => ({
            id: doc.id,
            doc_number: doc.doc_number,
            subject: doc.subject || '',
          })));
          if (response.items.length === 0) {
            setDocumentSearchError('找不到符合的公文');
          }
        } else {
          setDocumentSearchError('搜尋失敗，請稍後再試');
        }
      } catch (error) {
        logger.error('搜尋公文失敗:', error);
        setDocumentSearchError('搜尋時發生錯誤');
      } finally {
        setDocumentSearching(false);
      }
    }, 300),
    []
  );

  // 返回處理
  const handleBack = () => {
    navigate(returnTo || '/calendar');
  };

  // 儲存處理
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

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
      };

      saveMutation.mutate(submitData);
    } catch {
      // form validation error - 不需額外處理
    }
  };

  if (!isNew && isLoading) {
    return (
      <ResponsiveContent maxWidth="full" padding="medium" style={{ textAlign: 'center' }}>
        <Spin size="large" />
      </ResponsiveContent>
    );
  }

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card>
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <Space align="center" style={{ marginBottom: 16 }}>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleBack}
            >
              返回行事曆
            </Button>
          </Space>
          <Title level={4} style={{ margin: 0 }}>
            {isNew ? <PlusOutlined style={{ marginRight: 8 }} /> : <CalendarOutlined style={{ marginRight: 8 }} />}
            {isNew ? '新增日曆事件' : '編輯日曆事件'}
          </Title>
        </div>

        {/* Form */}
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            event_type: 'reminder',
            priority: 3,
            all_day: false,
          }}
        >
          <Form.Item
            name="title"
            label="事件標題"
            rules={[{ required: true, message: '請輸入事件標題' }]}
          >
            <TextArea
              placeholder="輸入事件標題"
              maxLength={200}
              showCount
              autoSize={{ minRows: 1, maxRows: 3 }}
            />
          </Form.Item>

          <Form.Item name="description" label="事件描述">
            <TextArea rows={3} placeholder="輸入事件描述（選填）" maxLength={1000} showCount />
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
                      <Space>{EVENT_TYPE_ICONS[opt.value]}{opt.label}</Space>
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
            <Col xs={12} sm={8}>
              <Form.Item name="all_day" label="全天事件" valuePropName="checked">
                <Switch onChange={setAllDay} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={16}>
              <Form.Item name="location" label="地點">
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
              <Form.Item
                name="end_date"
                label="結束時間"
                rules={[
                  {
                    validator: (_, value) => {
                      if (!value) return Promise.resolve();
                      const startDate = form.getFieldValue('start_date');
                      if (startDate && value.isBefore(startDate)) {
                        return Promise.reject('結束時間不能早於開始時間');
                      }
                      return Promise.resolve();
                    },
                  },
                ]}
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
          >
            <Select
              showSearch
              allowClear
              placeholder="輸入公文字號或主旨搜尋..."
              filterOption={false}
              onSearch={searchDocuments}
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
            >
              {documentOptions.map(doc => (
                <Select.Option key={doc.id} value={doc.id} label={doc.doc_number}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{doc.doc_number}</div>
                    {doc.subject && (
                      <div style={{
                        fontSize: 12,
                        color: '#888',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: 300,
                      }}>
                        {doc.subject}
                      </div>
                    )}
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {/* Actions */}
          <Divider />
          <Row justify="end">
            <Space>
              <Button onClick={handleBack}>取消</Button>
              <Button
                type="primary"
                icon={isNew ? <PlusOutlined /> : <SaveOutlined />}
                loading={saveMutation.isPending}
                disabled={saveMutation.isPending}
                onClick={handleSave}
              >
                {isNew ? '建立' : '儲存'}
              </Button>
            </Space>
          </Row>
        </Form>
      </Card>
    </ResponsiveContent>
  );
};

export default CalendarEventFormPage;
