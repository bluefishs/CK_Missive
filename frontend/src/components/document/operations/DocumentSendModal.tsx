/**
 * DocumentSendModal 元件
 *
 * 公文發送對話框
 *
 * @version 1.0.0
 * @date 2026-01-26
 */
import React, { useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  App,
  Card,
  Space,
  Row,
  Col,
} from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { Document } from '../../../types';
import { logger } from '../../../utils/logger';

const { TextArea } = Input;
const { Option } = Select;

// ============================================================================
// 型別定義
// ============================================================================

export interface DocumentSendModalProps {
  document: Document | null;
  visible: boolean;
  onClose: () => void;
  onSend: (sendData: unknown) => Promise<void>;
}

// ============================================================================
// 元件
// ============================================================================

export const DocumentSendModal: React.FC<DocumentSendModalProps> = ({
  document,
  visible,
  onClose,
  onSend,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      await onSend(values);
      message.success('公文發送成功！');
      onClose();
    } catch (error) {
      logger.error('Send document failed:', error);
      message.error('公文發送失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <SendOutlined />
          發送公文
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={loading} onClick={handleSend}>
            發送
          </Button>
        </Space>
      }
    >
      {document && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <strong>公文字號:</strong> {document.doc_number}
            </Col>
            <Col span={12}>
              <strong>主旨:</strong> {document.subject}
            </Col>
          </Row>
        </Card>
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          label="收件人"
          name="recipients"
          rules={[{ required: true, message: '請選擇收件人' }]}
        >
          <Select
            mode="multiple"
            placeholder="請選擇收件人"
            options={[
              { label: '張三', value: 'zhang.san@example.com' },
              { label: '李四', value: 'li.si@example.com' },
              { label: '王五', value: 'wang.wu@example.com' },
            ]}
          />
        </Form.Item>

        <Form.Item label="發送方式" name="sendMethod" initialValue="email">
          <Select>
            <Option value="email">電子郵件</Option>
            <Option value="internal">內部系統</Option>
            <Option value="both">兩者皆是</Option>
          </Select>
        </Form.Item>

        <Form.Item label="發送備註" name="sendNotes">
          <TextArea rows={3} placeholder="請輸入發送備註" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default DocumentSendModal;
