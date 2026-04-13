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

const FEATURE_LABELS: Record<string, string> = {
  summary: '摘要生成',
  classify: '分類建議',
  keywords: '關鍵字提取',
  search_intent: '搜尋意圖解析',
  match_agency: '機關匹配',
};

interface PromptCreateModalProps {
  open: boolean;
  form: FormInstance;
  allFeatures: string[];
  loading: boolean;
  onOk: () => void;
  onCancel: () => void;
}

export const PromptCreateModal: React.FC<PromptCreateModalProps> = ({
  open,
  form,
  allFeatures,
  loading,
  onOk,
  onCancel,
}) => {
  return (
    <Modal
      title="新增 Prompt 版本"
      open={open}
      onOk={onOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={720}
      okText="新增"
      cancelText="取消"
      forceRender
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="feature"
          label="功能名稱"
          rules={[{ required: true, message: '請選擇功能名稱' }]}
        >
          <Select
            placeholder="選擇功能"
            options={allFeatures.map((f) => ({
              value: f,
              label: `${FEATURE_LABELS[f] || f}（${f}）`,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="system_prompt"
          label="系統提示詞"
          rules={[{ required: true, message: '請輸入系統提示詞' }]}
        >
          <TextArea
            rows={10}
            placeholder="輸入系統提示詞（支援 {variable} 佔位符）"
            style={{ fontFamily: 'monospace', fontSize: 13 }}
          />
        </Form.Item>

        <Form.Item name="user_template" label="使用者提示詞模板（選填）">
          <TextArea
            rows={4}
            placeholder="輸入使用者提示詞模板（選填）"
            style={{ fontFamily: 'monospace', fontSize: 13 }}
          />
        </Form.Item>

        <Form.Item name="description" label="版本說明（選填）">
          <Input placeholder="簡述這個版本的修改內容" maxLength={500} />
        </Form.Item>

        <Form.Item name="activate" valuePropName="checked" initialValue={false}>
          <Switch checkedChildren="立即啟用" unCheckedChildren="暫不啟用" />
        </Form.Item>
      </Form>
    </Modal>
  );
};
