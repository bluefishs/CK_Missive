/**
 * 使用者編輯表單 Modal
 * @description 從 UserManagementPage.tsx 拆分
 */
import React, { useEffect } from 'react';
import {
  Modal, Form, Input, Select, Switch, Row, Col, Space, Button
} from 'antd';
import { USER_ROLES, USER_STATUSES } from '../../constants/permissions';
import type { User } from '../../types/user';

const { Option } = Select;

interface UserEditModalProps {
  visible: boolean;
  user: User | null;
  currentLoggedInUser: User | null;
  onSubmit: (values: any) => Promise<void>;
  onCancel: () => void;
}

const UserEditModal: React.FC<UserEditModalProps> = ({
  visible,
  user,
  currentLoggedInUser,
  onSubmit,
  onCancel,
}) => {
  const [form] = Form.useForm();
  const isEditing = !!user;
  const canEditStatus = currentLoggedInUser?.role === 'admin' || currentLoggedInUser?.role === 'superuser';

  useEffect(() => {
    if (visible) {
      if (user) {
        form.setFieldsValue({
          email: user.email,
          username: user.username,
          full_name: user.full_name,
          is_active: user.is_active,
          is_admin: user.is_admin,
          role: user.role,
          status: user.status || (user.is_active ? 'active' : 'inactive'),
        });
      } else {
        form.resetFields();
      }
    }
  }, [visible, user, form]);

  const handleFinish = async (values: any) => {
    await onSubmit(values);
    form.resetFields();
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title={isEditing ? "編輯使用者" : "新增使用者"}
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
              name="email"
              label="電子郵件"
              rules={[{ required: true, type: 'email', message: '請輸入有效的電子郵件' }]}
            >
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="username"
              label="使用者名稱"
              rules={[{ required: true, message: '請輸入使用者名稱' }]}
            >
              <Input />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="full_name"
          label="完整姓名"
        >
          <Input />
        </Form.Item>

        {!isEditing && (
          <Form.Item
            name="password"
            label="密碼"
            rules={[
              { required: true, message: '請輸入密碼' },
              { min: 6, message: '密碼至少需要6個字元' }
            ]}
          >
            <Input.Password placeholder="輸入新使用者密碼" />
          </Form.Item>
        )}

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="role"
              label="角色"
              rules={[{ required: true, message: '請選擇角色' }]}
            >
              <Select>
                {Object.entries(USER_ROLES).map(([key, role]) => (
                  <Option key={key} value={key}>
                    {role.name_zh}
                    {!role.can_login && ' (無法登入)'}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="status"
              label="狀態"
              rules={[{ required: true, message: '請選擇狀態' }]}
            >
              <Select disabled={!canEditStatus}>
                {Object.entries(USER_STATUSES).map(([key, status]) => (
                  <Option key={key} value={key}>
                    {status.name_zh}
                    {!status.can_login && ' (無法登入)'}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="is_admin" valuePropName="checked">
              <Switch checkedChildren="管理員" unCheckedChildren="一般使用者" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="suspended_reason"
          label="暫停原因"
          tooltip="當狀態為暫停時，可填寫暫停原因"
        >
          <Input.TextArea
            rows={2}
            placeholder="請輸入暫停或停用的原因..."
            maxLength={200}
          />
        </Form.Item>

        <Form.Item style={{ marginTop: '24px' }}>
          <Space>
            <Button type="primary" htmlType="submit">
              {isEditing ? '更新' : '新增'}
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

export default UserEditModal;
