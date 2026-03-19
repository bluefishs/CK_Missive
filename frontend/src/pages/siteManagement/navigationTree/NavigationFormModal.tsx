import { useEffect } from 'react';
import type { FC } from 'react';
import { Modal, Form, Input, Select, Switch, Space, TreeSelect } from 'antd';
import type { NavigationFormModalProps, FormValues } from './types';
import { ICON_OPTIONS } from './constants';

const { Option } = Select;
const { TextArea } = Input;

const INITIAL_VALUES: Partial<FormValues> = {
  is_visible: true,
  is_enabled: true,
  target: '_self',
  level: 1,
};

export const NavigationFormModal: FC<NavigationFormModalProps> = ({
  open,
  editingItem,
  defaultParentId,
  parentOptions,
  validPaths,
  confirmLoading,
  onSubmit,
  onCancel,
}) => {
  const [form] = Form.useForm<FormValues>();

  // Sync form values when modal opens
  useEffect(() => {
    if (!open) return;
    if (editingItem) {
      // Editing existing item
      form.setFieldsValue({
        ...editingItem,
        parent_id: editingItem.parent_id === null ? 0 : editingItem.parent_id,
      } as unknown as FormValues);
    } else {
      // Creating new item -- apply defaults
      form.resetFields();
      form.setFieldsValue({
        parent_id: defaultParentId ?? 0,
        is_visible: true,
        is_enabled: true,
        target: '_self',
      } as FormValues);
    }
  }, [open, editingItem, defaultParentId, form]);

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  const handleFinish = async (values: FormValues) => {
    await onSubmit(values);
    form.resetFields();
  };

  return (
    <Modal
      title={editingItem ? '編輯導覽項目' : '新增導覽項目'}
      open={open}
      onCancel={handleCancel}
      onOk={() => form.submit()}
      confirmLoading={confirmLoading}
      width={700}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={INITIAL_VALUES}
      >
        <Form.Item label="標題" name="title" rules={[{ required: true, message: '請輸入標題' }]}>
          <Input placeholder="例如：公文管理" />
        </Form.Item>

        <Form.Item
          label="識別碼 (Key)"
          name="key"
          rules={[{ required: true, message: '請輸入識別碼' }]}
          tooltip="程式使用的唯一識別碼"
        >
          <Input placeholder="例如：documents" />
        </Form.Item>

        <Form.Item label="路徑" name="path" tooltip="URL 路徑，群組項目可選擇「無」">
          <Select
            placeholder="選擇路徑"
            allowClear
            showSearch
            optionFilterProp="children"
            filterOption={(input, option) =>
              (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
            }
          >
            {validPaths.map((item) => (
              <Option key={item.path ?? 'null'} value={item.path ?? ''}>
                {item.path ? `${item.description} (${item.path})` : item.description}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item label="圖示" name="icon" rules={[{ required: true, message: '請選擇圖示' }]}>
          <Select placeholder="選擇圖示" showSearch>
            {ICON_OPTIONS.map(icon => (
              <Option key={icon} value={icon}>{icon}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item label="說明" name="description">
          <TextArea rows={2} placeholder="此功能的簡短說明" />
        </Form.Item>

        <Form.Item label="父層項目" name="parent_id" tooltip="選擇父層項目或頂層">
          <TreeSelect
            treeData={parentOptions}
            placeholder="選擇父層項目"
            allowClear
            treeDefaultExpandAll
            showSearch
            treeNodeFilterProp="title"
            fieldNames={{ label: 'title', value: 'value', children: 'children' }}
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item label="排序順序" name="sort_order" tooltip="數字越小越前面">
          <Input type="number" min={0} placeholder="0 = 自動排至最後" />
        </Form.Item>

        <Form.Item label="所需權限" name="permission_required" tooltip="留空表示不需權限">
          <Input placeholder="例如：documents:read" />
        </Form.Item>

        <Space>
          <Form.Item label="顯示" name="is_visible" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="啟用" name="is_enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Space>
      </Form>
    </Modal>
  );
};
