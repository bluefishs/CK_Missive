/**
 * 使用者權限管理 Modal
 * @description 從 UserManagementPage.tsx 拆分
 */
import React, { useEffect } from 'react';
import {
  Modal, Form, Select, Divider, Space, Button
} from 'antd';
import PermissionManager from './PermissionManager';
import type { User, Permission, UserPermissions } from '../../types/api';
import type { UserInfo } from '../../services/authService';

const { Option } = Select;

interface UserPermissionModalProps {
  visible: boolean;
  user: User | null;
  userPermissions: UserPermissions | null;
  roles: Permission[];
  currentLoggedInUser: UserInfo | null;
  onSubmit: (values: any) => Promise<void>;
  onCancel: () => void;
  onRoleChange: (role: string) => void;
}

const UserPermissionModal: React.FC<UserPermissionModalProps> = ({
  visible,
  user,
  userPermissions,
  roles,
  currentLoggedInUser,
  onSubmit,
  onCancel,
  onRoleChange,
}) => {
  const [form] = Form.useForm();
  const canEditPermissions = currentLoggedInUser?.role === 'admin' || currentLoggedInUser?.role === 'superuser';

  useEffect(() => {
    if (visible && userPermissions) {
      form.setFieldsValue({
        role: userPermissions.role,
        permissions: userPermissions.permissions,
      });
    }
  }, [visible, userPermissions, form]);

  const handleFinish = async (values: any) => {
    await onSubmit(values);
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  const handleRoleChange = (role: string) => {
    onRoleChange(role);
    // 更新表單中的權限
    const selectedRole = roles.find(r => r.name === role);
    if (selectedRole) {
      form.setFieldsValue({
        permissions: selectedRole.default_permissions,
      });
    }
  };

  return (
    <Modal
      title={`管理權限 - ${user?.full_name || user?.username}`}
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={800}
      forceRender
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
      >
        <Form.Item
          name="role"
          label="角色"
          rules={[{ required: true, message: '請選擇角色' }]}
        >
          <Select
            onChange={handleRoleChange}
            disabled={!canEditPermissions}
          >
            {roles.map(role => (
              <Option key={role.name} value={role.name}>
                {role.display_name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Divider>詳細權限設定</Divider>

        <PermissionManager
          userPermissions={userPermissions?.permissions || []}
          onPermissionChange={(permissions) => {
            form.setFieldsValue({ permissions });
          }}
          readOnly={!canEditPermissions}
        />

        <Form.Item style={{ marginTop: '24px' }}>
          <Space>
            <Button type="primary" htmlType="submit">
              更新權限
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

export default UserPermissionModal;
