/**
 * Vendor Association Form Modal
 *
 * Extracted from ProjectVendorManagement.tsx.
 * Handles the create/edit modal form for project-vendor associations.
 */

import React from 'react';
import {
  Modal,
  Form,
  Select,
  DatePicker,
  InputNumber,
  Button,
  Space,
  Tag,
} from 'antd';
import type { FormInstance } from 'antd';
import type { Vendor } from '../../types/api';
import { parseCurrencyInput } from '../../utils/format';

const { Option } = Select;

interface VendorAssociationFormProps {
  open: boolean;
  editing: boolean;
  form: FormInstance;
  availableVendors: Vendor[];
  onSubmit: (values: {
    vendor_id: number;
    role?: string;
    contract_amount?: number;
    start_date?: string;
    end_date?: string;
    status?: string;
  }) => void;
  onCancel: () => void;
}

const VendorAssociationForm: React.FC<VendorAssociationFormProps> = ({
  open,
  editing,
  form,
  availableVendors,
  onSubmit,
  onCancel,
}) => (
  <Modal
    title={editing ? '編輯廠商關聯' : '新增廠商關聯'}
    open={open}
    onCancel={onCancel}
    footer={null}
    width={600}
    forceRender
  >
    <Form
      form={form}
      layout="vertical"
      onFinish={onSubmit}
    >
      <Form.Item
        name="vendor_id"
        label="選擇廠商"
        rules={[{ required: true, message: '請選擇廠商' }]}
      >
        <Select
          placeholder="請選擇廠商"
          disabled={editing}
          showSearch
          optionFilterProp="children"
        >
          {availableVendors.map(vendor => (
            <Option key={vendor.id} value={vendor.id}>
              <Space>
                <strong>{vendor.vendor_name}</strong>
                {vendor.vendor_code && (
                  <small style={{ color: '#666' }}>({vendor.vendor_code})</small>
                )}
                {vendor.business_type && (
                  <Tag style={{ fontSize: '10px' }}>{vendor.business_type}</Tag>
                )}
              </Space>
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item name="role" label="廠商角色">
        <Select placeholder="請選擇角色">
          <Option value="主承包商">主承包商</Option>
          <Option value="分包商">分包商</Option>
          <Option value="供應商">供應商</Option>
          <Option value="顧問">顧問</Option>
          <Option value="監造">監造</Option>
          <Option value="其他">其他</Option>
        </Select>
      </Form.Item>

      <Form.Item name="contract_amount" label="合約金額">
        <InputNumber
          placeholder="請輸入合約金額"
          min={0}
          style={{ width: '100%' }}
          formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          parser={parseCurrencyInput}
        />
      </Form.Item>

      <div style={{ display: 'flex', gap: 16 }}>
        <Form.Item name="start_date" label="合作開始日期" style={{ flex: 1 }}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="end_date" label="合作結束日期" style={{ flex: 1 }}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </div>

      <Form.Item name="status" label="合作狀態">
        <Select placeholder="請選擇狀態" defaultValue="active">
          <Option value="active">合作中</Option>
          <Option value="completed">已完成</Option>
          <Option value="inactive">暫停</Option>
          <Option value="cancelled">已取消</Option>
        </Select>
      </Form.Item>

      <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
        <Space>
          <Button onClick={onCancel}>取消</Button>
          <Button type="primary" htmlType="submit">
            {editing ? '更新' : '建立'}
          </Button>
        </Space>
      </Form.Item>
    </Form>
  </Modal>
);

export default VendorAssociationForm;
