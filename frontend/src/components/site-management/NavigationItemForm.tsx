/**
 * 導覽項目編輯表單
 * @description 從 NavigationManagement.tsx 拆分
 */
import React, { useEffect } from 'react';
import {
  Modal, Form, Input, Select, Switch, Row, Col, Space, Button
} from 'antd';
import type { NavigationItem, NavigationFormData, ParentOption } from '../../types/navigation';
import { ICON_OPTIONS, PERMISSION_GROUPS } from '../../config/navigationConfig';

const { Option } = Select;
const { TextArea } = Input;

interface NavigationItemFormProps {
  visible: boolean;
  editingItem: NavigationItem | null;
  parentOptions: ParentOption[];
  defaultSortOrder: number;
  onSubmit: (values: NavigationFormData) => Promise<void>;
  onCancel: () => void;
}

const NavigationItemForm: React.FC<NavigationItemFormProps> = ({
  visible,
  editingItem,
  parentOptions,
  defaultSortOrder,
  onSubmit,
  onCancel,
}) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible) {
      if (editingItem) {
        form.setFieldsValue({
          ...editingItem,
          parent_id: editingItem.parent_id || undefined
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          is_visible: true,
          is_enabled: true,
          target: '_self',
          level: 1,
          sort_order: defaultSortOrder
        });
      }
    }
  }, [visible, editingItem, defaultSortOrder, form]);

  const handleFinish = async (values: NavigationFormData) => {
    await onSubmit(values);
    form.resetFields();
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title={editingItem ? '編輯導覽項目' : '新增導覽項目'}
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="title"
              label="標題"
              rules={[{ required: true, message: '請輸入標題' }]}
            >
              <Input placeholder="請輸入標題" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="key"
              label="唯一鍵值"
              rules={[{ required: true, message: '請輸入唯一鍵值' }]}
            >
              <Input placeholder="請輸入唯一鍵值" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="path" label="路由路徑">
              <Input placeholder="請輸入路由路徑" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="icon" label="圖示">
              <Select placeholder="選擇圖示" allowClear>
                {ICON_OPTIONS.map(icon => (
                  <Option key={icon} value={icon}>{icon}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="parent_id" label="父級項目">
              <Select placeholder="選擇父級項目" allowClear>
                {parentOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="level"
              label="層級"
              rules={[{ required: true, message: '請輸入層級' }]}
            >
              <Input type="number" placeholder="請輸入層級 (1-5)" min={1} max={5} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="sort_order"
              label="排序順序"
              rules={[{ required: true, message: '請輸入排序順序' }]}
            >
              <Input type="number" placeholder="請輸入排序順序" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="description" label="描述">
          <TextArea rows={3} placeholder="請輸入描述" />
        </Form.Item>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="target"
              label="開啟方式"
              rules={[{ required: true }]}
            >
              <Select>
                <Option value="_self">當前頁面</Option>
                <Option value="_blank">新頁面</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="is_visible"
              label="是否可見"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="is_enabled"
              label="是否啟用"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="permission_required"
          label="所需權限"
          extra="選擇此導覽項目所需的最低權限等級，留空表示所有使用者皆可存取"
        >
          <Select
            placeholder="選擇所需權限或留空表示無限制"
            allowClear
            showSearch
            optionFilterProp="children"
          >
            {PERMISSION_GROUPS.map(group => (
              <Select.OptGroup key={group.label} label={group.label}>
                {group.options.map(opt => (
                  <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                ))}
              </Select.OptGroup>
            ))}
          </Select>
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              {editingItem ? '更新' : '新增'}
            </Button>
            <Button onClick={handleCancel}>
              取消
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default NavigationItemForm;
