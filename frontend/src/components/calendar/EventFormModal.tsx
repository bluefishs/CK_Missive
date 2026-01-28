/**
 * 日曆事件表單模態框
 * 用於新增和編輯日曆事件 (符合 POST 資安機制)
 *
 * @version 2.0.0 - 模組化重構：Hook 提取
 * @date 2026-01-28
 */
import React from 'react';
import {
  Modal, Form, Input, Select, DatePicker, Switch,
  Row, Col, Space, Button, Spin, Divider,
} from 'antd';
import {
  BellOutlined, CalendarOutlined, AlertOutlined,
  EyeOutlined, UnorderedListOutlined, FileTextOutlined,
} from '@ant-design/icons';

import { useEventForm } from './form/useEventForm';
import type { EventFormModalProps } from './form/types';
import { EVENT_TYPE_OPTIONS, PRIORITY_OPTIONS } from './form/types';

const { TextArea } = Input;

const EVENT_TYPE_ICONS: Record<string, React.ReactNode> = {
  deadline: <AlertOutlined style={{ color: '#f5222d' }} />,
  meeting: <CalendarOutlined style={{ color: '#722ed1' }} />,
  review: <EyeOutlined style={{ color: '#1890ff' }} />,
  reminder: <BellOutlined style={{ color: '#fa8c16' }} />,
  reference: <UnorderedListOutlined style={{ color: '#666' }} />,
};

export const EventFormModal: React.FC<EventFormModalProps> = ({
  visible,
  mode,
  event,
  onClose,
  onSuccess,
}) => {
  const {
    form,
    isMobile,
    loading,
    allDay,
    setAllDay,
    documentOptions,
    documentSearchError,
    existingEventsWarning,
    documentSearching,
    searchDocuments,
    handleDocumentChange,
    handleSubmit,
  } = useEventForm(visible, mode, event, onClose, onSuccess);

  return (
    <Modal
      title={mode === 'create' ? '新增日曆事件' : '編輯日曆事件'}
      open={visible}
      onCancel={onClose}
      width={isMobile ? '95%' : 700}
      style={{ maxWidth: '95vw' }}
      forceRender
      footer={[
        <Button key="cancel" onClick={onClose}>取消</Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          {mode === 'create' ? '建立' : '儲存'}
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
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
            <Input placeholder="輸入事件標題" maxLength={200} showCount />
          </Form.Item>

          <Form.Item name="description" label="事件描述">
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
                      <Space>{EVENT_TYPE_ICONS[opt.value]}{opt.label}</Space>
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
              <Form.Item name="all_day" label="全天事件" valuePropName="checked">
                <Switch onChange={setAllDay} />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item name="location" label="地點">
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
              <Form.Item name="end_date" label="結束時間">
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
            rules={[{ required: mode === 'create', message: '請選擇關聯公文' }]}
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
                <Select.Option key={doc.id} value={doc.id} label={doc.doc_number}>
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
