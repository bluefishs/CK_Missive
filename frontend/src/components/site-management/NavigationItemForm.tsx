/**
 * 導覽項目編輯表單 - 整合共用模組版本
 * @description 支援客製化標籤、欄位控制、擴展欄位
 * @version 2.0.0 - 2026-01-09
 */
import React, { useEffect } from 'react';
import {
  Modal, Form, Input, Select, Switch, Row, Col, Space, Button
} from 'antd';
import type {
  NavigationItem,
  NavigationFormData,
  ParentOption,
  IconOption,
  PermissionGroup,
  FormLabels,
} from '../../types/navigation';
import { defaultFormLabels } from '../../types/navigation';

const { Option } = Select;
const { TextArea } = Input;

export interface NavigationItemFormProps {
  visible: boolean;
  editingItem: NavigationItem | null;
  parentOptions: ParentOption[];
  defaultSortOrder: number;
  iconOptions?: IconOption[];
  permissionGroups?: PermissionGroup[];
  onSubmit: (values: NavigationFormData) => Promise<void>;
  onCancel: () => void;

  // 客製化
  labels?: Partial<FormLabels>;
  showPermissionField?: boolean;
  showDescriptionField?: boolean;
  showTargetField?: boolean;
  renderExtraFields?: () => React.ReactNode;
}

const NavigationItemForm: React.FC<NavigationItemFormProps> = ({
  visible,
  editingItem,
  parentOptions,
  defaultSortOrder,
  iconOptions = [],
  permissionGroups = [],
  onSubmit,
  onCancel,
  labels: userLabels,
  showPermissionField = true,
  showDescriptionField = true,
  showTargetField = true,
  renderExtraFields,
}) => {
  const labels = { ...defaultFormLabels, ...userLabels };
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
      title={editingItem ? labels.editTitle : labels.addTitle}
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={600}
      forceRender
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
              label={labels.title}
              rules={[{ required: true, message: `請輸入${labels.title}` }]}
            >
              <Input placeholder={`請輸入${labels.title}`} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="key"
              label={labels.key}
              rules={[{ required: true, message: `請輸入${labels.key}` }]}
            >
              <Input placeholder={`請輸入${labels.key}`} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="path" label={labels.path}>
              <Input placeholder={`請輸入${labels.path}`} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="icon" label={labels.icon}>
              <Select placeholder={`選擇${labels.icon}`} allowClear>
                {iconOptions.map(icon => (
                  <Option key={icon.value} value={icon.value}>
                    {icon.icon} {icon.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="parent_id" label={labels.parent}>
              <Select placeholder={`選擇${labels.parent}`} allowClear>
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
              label={labels.level}
              rules={[{ required: true, message: `請輸入${labels.level}` }]}
            >
              <Input type="number" placeholder="1-5" min={1} max={5} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="sort_order"
              label={labels.sortOrder}
              rules={[{ required: true, message: `請輸入${labels.sortOrder}` }]}
            >
              <Input type="number" placeholder={`請輸入${labels.sortOrder}`} />
            </Form.Item>
          </Col>
        </Row>

        {showDescriptionField && (
          <Form.Item name="description" label={labels.description}>
            <TextArea rows={3} placeholder={`請輸入${labels.description}`} />
          </Form.Item>
        )}

        <Row gutter={16}>
          {showTargetField && (
            <Col span={8}>
              <Form.Item name="target" label={labels.target} rules={[{ required: true }]}>
                <Select>
                  <Option value="_self">當前頁面</Option>
                  <Option value="_blank">新頁面</Option>
                </Select>
              </Form.Item>
            </Col>
          )}
          <Col span={8}>
            <Form.Item name="is_visible" label={labels.isVisible} valuePropName="checked">
              <Switch />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="is_enabled" label={labels.isEnabled} valuePropName="checked">
              <Switch />
            </Form.Item>
          </Col>
        </Row>

        {showPermissionField && permissionGroups.length > 0 && (
          <Form.Item name="permission_required" label={labels.permission}>
            <Select placeholder="選擇所需權限或留空" allowClear showSearch optionFilterProp="children">
              {permissionGroups.map(group => (
                <Select.OptGroup key={group.label} label={group.label}>
                  {group.options.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select.OptGroup>
              ))}
            </Select>
          </Form.Item>
        )}

        {renderExtraFields?.()}

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              {editingItem ? labels.update : labels.submit}
            </Button>
            <Button onClick={handleCancel}>
              {labels.cancel}
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default NavigationItemForm;
