/**
 * ProfileInfoCard - Basic user information form with avatar
 *
 * Displays user avatar and editable form fields for username, full name,
 * email, department, and position.
 *
 * @version 1.0.0
 */

import { useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Row,
  Col,
  Space,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  EditOutlined,
  BankOutlined,
  IdcardOutlined,
} from '@ant-design/icons';
import type { ProfileInfoCardProps, ProfileFormFields } from './types';

export const ProfileInfoCard = ({
  profile,
  isMobile,
  editing,
  saving,
  onToggleEdit,
  onSave,
  onCancelEdit,
}: ProfileInfoCardProps) => {
  const [form] = Form.useForm<ProfileFormFields>();

  useEffect(() => {
    form.setFieldsValue({
      username: profile.username,
      full_name: profile.full_name,
      email: profile.email,
      department: profile.department,
      position: profile.position,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps -- only sync form when profile changes
  }, [profile]);

  const handleCancel = () => {
    form.setFieldsValue({
      username: profile.username,
      full_name: profile.full_name,
      email: profile.email,
      department: profile.department,
      position: profile.position,
    });
    onCancelEdit();
  };

  return (
    <Card
      title="基本資訊"
      size={isMobile ? 'small' : 'medium'}
      extra={
        <Button
          type="primary"
          icon={<EditOutlined />}
          size={isMobile ? 'small' : 'middle'}
          onClick={onToggleEdit}
        >
          {isMobile ? (editing ? '取消' : '編輯') : (editing ? '取消編輯' : '編輯資料')}
        </Button>
      }
    >
      <Row gutter={[isMobile ? 12 : 24, isMobile ? 12 : 16]} align="middle">
        <Col xs={24} sm={6} style={{ textAlign: 'center', marginBottom: isMobile ? 12 : 0 }}>
          <Avatar
            size={isMobile ? 64 : 80}
            src={profile.avatar_url}
            icon={<UserOutlined />}
          />
        </Col>
        <Col xs={24} sm={18}>
          <Form
            form={form}
            layout="vertical"
            onFinish={onSave}
            initialValues={{
              username: profile.username,
              full_name: profile.full_name,
              email: profile.email,
              department: profile.department,
              position: profile.position,
            }}
          >
            <Form.Item
              label="使用者名稱"
              name="username"
              rules={[
                { required: true, message: '請輸入使用者名稱' },
                { min: 3, message: '使用者名稱至少需要 3 個字符' }
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                disabled={!editing}
              />
            </Form.Item>

            <Form.Item
              label="姓名"
              name="full_name"
              rules={[
                { required: true, message: '請輸入姓名' }
              ]}
            >
              <Input
                disabled={!editing}
              />
            </Form.Item>

            <Form.Item label="電子郵件" name="email">
              <Input
                prefix={<MailOutlined />}
                disabled
              />
            </Form.Item>

            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item label="部門" name="department">
                  <Input
                    prefix={<BankOutlined />}
                    placeholder="例：工程部"
                    disabled={!editing}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item label="職位" name="position">
                  <Input
                    prefix={<IdcardOutlined />}
                    placeholder="例：專案經理"
                    disabled={!editing}
                  />
                </Form.Item>
              </Col>
            </Row>

            {editing && (
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={saving}>
                    儲存變更
                  </Button>
                  <Button onClick={handleCancel}>
                    取消
                  </Button>
                </Space>
              </Form.Item>
            )}
          </Form>
        </Col>
      </Row>
    </Card>
  );
};
