/**
 * 日曆事件表單頁面（導航模式）
 *
 * 支援新建與編輯模式：
 * - 新建: /calendar/event/new (可帶 ?documentId=xxx query param)
 * - 編輯: /calendar/event/:id/edit
 *
 * @version 2.1.0 - 邏輯拆分至 useCalendarEventForm
 */

import React from 'react';
import { ResponsiveContent } from '@ck-shared/ui-components';
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
import { EVENT_TYPE_OPTIONS, PRIORITY_OPTIONS } from '../components/calendar/form/types';
import { useCalendarEventForm } from './useCalendarEventForm';

const { TextArea } = Input;
const { Title } = Typography;

const EVENT_TYPE_ICONS: Record<string, React.ReactNode> = {
  deadline: <AlertOutlined style={{ color: '#f5222d' }} />,
  meeting: <CalendarOutlined style={{ color: '#722ed1' }} />,
  review: <EyeOutlined style={{ color: '#1890ff' }} />,
  reminder: <BellOutlined style={{ color: '#fa8c16' }} />,
  reference: <UnorderedListOutlined style={{ color: '#666' }} />,
};

const CalendarEventFormPage: React.FC = () => {
  const {
    form,
    isNew,
    isLoading,
    allDay,
    setAllDay,
    documentOptions,
    documentSearching,
    documentSearchError,
    searchDocuments,
    saveMutation,
    handleBack,
    handleSave,
  } = useCalendarEventForm();

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
        <div style={{ marginBottom: 24 }}>
          <Space align="center" style={{ marginBottom: 16 }}>
            <Button type="text" icon={<ArrowLeftOutlined />} onClick={handleBack}>
              返回行事曆
            </Button>
          </Space>
          <Title level={4} style={{ margin: 0 }}>
            {isNew ? <PlusOutlined style={{ marginRight: 8 }} /> : <CalendarOutlined style={{ marginRight: 8 }} />}
            {isNew ? '新增日曆事件' : '編輯日曆事件'}
          </Title>
        </div>

        <Form
          form={form}
          layout="vertical"
          initialValues={{ event_type: 'reminder', priority: 3, all_day: false }}
        >
          <Form.Item name="title" label="事件標題" rules={[{ required: true, message: '請輸入事件標題' }]}>
            <TextArea placeholder="輸入事件標題" maxLength={200} showCount autoSize={{ minRows: 1, maxRows: 3 }} />
          </Form.Item>

          <Form.Item name="description" label="事件描述">
            <TextArea rows={3} placeholder="輸入事件描述（選填）" maxLength={1000} showCount />
          </Form.Item>

          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="event_type" label="事件類型" rules={[{ required: true, message: '請選擇事件類型' }]}>
                <Select
                  placeholder="選擇事件類型"
                  options={EVENT_TYPE_OPTIONS.map(opt => ({
                    value: opt.value,
                    label: <Space>{EVENT_TYPE_ICONS[opt.value]}{opt.label}</Space>,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="priority" label="優先級" rules={[{ required: true, message: '請選擇優先級' }]}>
                <Select
                  placeholder="選擇優先級"
                  options={PRIORITY_OPTIONS.map(opt => ({
                    value: opt.value,
                    label: <span style={{ color: opt.color }}>{opt.label}</span>,
                  }))}
                />
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
              <Form.Item name="start_date" label="開始時間" rules={[{ required: true, message: '請選擇開始時間' }]}>
                <DatePicker
                  showTime={!allDay}
                  format={allDay ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm'}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                name="end_date" label="結束時間"
                rules={[{
                  validator: (_, value) => {
                    if (!value) return Promise.resolve();
                    const startDate = form.getFieldValue('start_date');
                    if (startDate && value.isBefore(startDate)) return Promise.reject('結束時間不能早於開始時間');
                    return Promise.resolve();
                  },
                }]}
              >
                <DatePicker
                  showTime={!allDay}
                  format={allDay ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm'}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider titlePlacement="left" plain>
            <Space><FileTextOutlined />關聯公文</Space>
          </Divider>

          <Form.Item name="document_id" label="關聯公文" tooltip="輸入公文字號或主旨關鍵字搜尋（至少2個字元）">
            <Select
              showSearch allowClear
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
                  <div style={{ textAlign: 'center', padding: 8, color: '#faad14' }}>{documentSearchError}</div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 8, color: '#888' }}>輸入至少2個字元搜尋</div>
                )
              }
              optionLabelProp="label"
              options={documentOptions.map(doc => ({ value: doc.id, label: doc.doc_number }))}
              optionRender={(option) => {
                const doc = documentOptions.find(d => d.id === option.value);
                return (
                  <div>
                    <div style={{ fontWeight: 500 }}>{doc?.doc_number}</div>
                    {doc?.subject && (
                      <div style={{ fontSize: 12, color: '#888', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 300 }}>
                        {doc.subject}
                      </div>
                    )}
                  </div>
                );
              }}
            />
          </Form.Item>

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
