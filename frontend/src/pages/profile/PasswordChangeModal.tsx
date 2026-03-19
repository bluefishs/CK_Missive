/**
 * PasswordChangeModal - Modal dialog for changing user password
 *
 * Includes current password verification, new password with min-length
 * validation, and confirmation matching.
 *
 * @version 1.0.0
 */

import {
  Modal,
  Form,
  Input,
  Button,
  Space,
} from 'antd';
import { LockOutlined } from '@ant-design/icons';
import type { PasswordChangeModalProps, PasswordChangeFormValues } from './types';

export const PasswordChangeModal = ({
  open,
  isMobile,
  onCancel,
  onSubmit,
}: PasswordChangeModalProps) => {
  const [passwordForm] = Form.useForm<PasswordChangeFormValues>();

  const handleCancel = () => {
    passwordForm.resetFields();
    onCancel();
  };

  const handleFinish = async (values: PasswordChangeFormValues) => {
    await onSubmit(values);
    passwordForm.resetFields();
  };

  return (
    <Modal
      title="修改密碼"
      open={open}
      onCancel={handleCancel}
      footer={null}
      destroyOnHidden
      width={isMobile ? '95%' : 520}
    >
      <Form
        form={passwordForm}
        layout="vertical"
        onFinish={handleFinish}
      >
        <Form.Item
          label="目前密碼"
          name="current_password"
          rules={[{ required: true, message: '請輸入目前密碼' }]}
        >
          <Input.Password prefix={<LockOutlined />} />
        </Form.Item>

        <Form.Item
          label="新密碼"
          name="new_password"
          rules={[
            { required: true, message: '請輸入新密碼' },
            { min: 6, message: '密碼長度至少需要 6 個字符' }
          ]}
        >
          <Input.Password prefix={<LockOutlined />} />
        </Form.Item>

        <Form.Item
          label="確認新密碼"
          name="confirm_password"
          dependencies={['new_password']}
          rules={[
            { required: true, message: '請確認新密碼' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error('兩次輸入的密碼不一致'));
              },
            }),
          ]}
        >
          <Input.Password prefix={<LockOutlined />} />
        </Form.Item>

        <Form.Item>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={handleCancel}>
              取消
            </Button>
            <Button type="primary" htmlType="submit">
              確認修改
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};
