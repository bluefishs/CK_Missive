/**
 * Synonym Form Modal
 *
 * Extracted from SynonymManagementPanel.tsx.
 * Handles the create/edit modal for synonym groups.
 */

import React from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
} from 'antd';
import type { FormInstance } from 'antd';

const { TextArea } = Input;

interface CategoryOption {
  value: string;
  label: string;
}

interface SynonymFormModalProps {
  open: boolean;
  editing: boolean;
  form: FormInstance;
  categoryOptions: CategoryOption[];
  onSave: () => void;
  onCancel: () => void;
}

const SynonymFormModal: React.FC<SynonymFormModalProps> = ({
  open,
  editing,
  form,
  categoryOptions,
  onSave,
  onCancel,
}) => (
  <Modal
    title={editing ? '編輯同義詞群組' : '新增同義詞群組'}
    open={open}
    onOk={onSave}
    onCancel={onCancel}
    okText="儲存"
    cancelText="取消"
    destroyOnHidden
    forceRender
  >
    <Form
      form={form}
      layout="vertical"
      initialValues={{ is_active: true }}
    >
      <Form.Item
        name="category"
        label="分類"
        rules={[{ required: true, message: '請選擇或輸入分類' }]}
      >
        <Select
          showSearch
          placeholder="選擇或輸入分類"
          options={categoryOptions}
          allowClear
        />
      </Form.Item>

      <Form.Item
        name="words"
        label="同義詞列表"
        rules={[{ required: true, message: '請輸入同義詞' }]}
        extra="以逗號分隔多個同義詞，例如：桃園市政府, 桃市府, 市政府"
      >
        <TextArea
          rows={3}
          placeholder="桃園市政府, 桃市府, 市政府, 市府"
        />
      </Form.Item>

      <Form.Item
        name="is_active"
        label="啟用狀態"
        valuePropName="checked"
      >
        <Switch checkedChildren="啟用" unCheckedChildren="停用" />
      </Form.Item>
    </Form>
  </Modal>
);

export default SynonymFormModal;
