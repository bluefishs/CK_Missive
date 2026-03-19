import React, { useState, useCallback } from 'react';
import { Modal, Form, Input, Select, Space, Alert } from 'antd';
import { BankOutlined } from '@ant-design/icons';
import debounce from 'lodash/debounce';

const { Option } = Select;

interface AgencyOption {
  agency_name: string;
  agency_short_name?: string;
}

interface AddAgencyModalProps {
  visible: boolean;
  onCancel: () => void;
  onSubmit: (values: { agency_name: string; agency_short_name?: string; agency_type?: string }) => Promise<void>;
  submitting: boolean;
  agencyOptions: AgencyOption[];
  isMobile: boolean;
}

export const AddAgencyModal: React.FC<AddAgencyModalProps> = ({
  visible,
  onCancel,
  onSubmit,
  submitting,
  agencyOptions,
  isMobile,
}) => {
  const [form] = Form.useForm();
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce wrapper; agencyOptions is stable enough
  const checkAgencyDuplicate = useCallback(
    debounce(async (name: string) => {
      if (!name || name.length < 2) {
        setDuplicateWarning(null);
        return;
      }

      const lowerName = name.toLowerCase();
      const similar = agencyOptions.filter(
        (a) =>
          a.agency_name.toLowerCase().includes(lowerName) ||
          lowerName.includes(a.agency_name.toLowerCase()) ||
          (a.agency_short_name && a.agency_short_name.toLowerCase().includes(lowerName))
      );

      if (similar.length > 0) {
        const names = similar.slice(0, 3).map((a) => a.agency_name).join('、');
        setDuplicateWarning(`已有相似機關：${names}`);
      } else {
        setDuplicateWarning(null);
      }
    }, 300),
    [agencyOptions]
  );

  const handleAgencyNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    checkAgencyDuplicate(e.target.value);
  };

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      await onSubmit(values);
      form.resetFields();
      setDuplicateWarning(null);
    } catch {
      // validation failed, form will show errors
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setDuplicateWarning(null);
    onCancel();
  };

  return (
    <Modal
      title={
        <Space>
          <BankOutlined />
          <span>新增機關單位</span>
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      onOk={handleOk}
      confirmLoading={submitting}
      okText="建立"
      cancelText="取消"
      width={isMobile ? '95%' : 500}
      forceRender
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 16 }}
      >
        <Form.Item
          label="機關名稱"
          name="agency_name"
          rules={[
            { required: true, message: '請輸入機關名稱' },
            { min: 2, message: '機關名稱至少 2 個字' },
          ]}
          help={duplicateWarning && (
            <span style={{ color: '#faad14' }}>{duplicateWarning}</span>
          )}
          validateStatus={duplicateWarning ? 'warning' : undefined}
        >
          <Input
            placeholder="請輸入完整機關名稱"
            onChange={handleAgencyNameChange}
            maxLength={100}
            showCount
          />
        </Form.Item>

        <Form.Item
          label="機關簡稱"
          name="agency_short_name"
          tooltip="例如：國土署、地政局"
        >
          <Input
            placeholder="請輸入機關簡稱（選填）"
            maxLength={50}
          />
        </Form.Item>

        <Form.Item
          label="機關類型"
          name="agency_type"
          initialValue="政府機關"
        >
          <Select>
            <Option value="政府機關">政府機關</Option>
            <Option value="國營事業">國營事業</Option>
            <Option value="學術機構">學術機構</Option>
            <Option value="其他">其他</Option>
          </Select>
        </Form.Item>

        {duplicateWarning && (
          <Alert
            title="提示"
            description="系統偵測到可能重複的機關，請確認是否需要新增。如果是同一機關，建議直接從下拉選單中選擇。"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
      </Form>
    </Modal>
  );
};
