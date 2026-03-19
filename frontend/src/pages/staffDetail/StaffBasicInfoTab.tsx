/**
 * StaffBasicInfoTab
 * @description Basic info tab with view mode (Descriptions) and edit mode (Form)
 */
import React from 'react';
import {
  Button,
  Space,
  Typography,
  Form,
  Input,
  AutoComplete,
  Switch,
  Row,
  Col,
  Tag,
  Descriptions,
} from 'antd';
import type { FormInstance } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
  IdcardOutlined,
  SaveOutlined,
  CloseOutlined,
  KeyOutlined,
  BankOutlined,
} from '@ant-design/icons';
import type { User } from '../../types/api';

const { Text } = Typography;

interface StaffBasicInfoTabProps {
  staff: User;
  form: FormInstance;
  isEditing: boolean;
  isMobile: boolean;
  saving: boolean;
  showPasswordChange: boolean;
  departmentOptions: string[];
  onShowPasswordChange: (checked: boolean) => void;
  onSave: () => void;
  onCancel: () => void;
}

export const StaffBasicInfoTab: React.FC<StaffBasicInfoTabProps> = ({
  staff,
  form,
  isEditing,
  isMobile,
  saving,
  showPasswordChange,
  departmentOptions,
  onShowPasswordChange,
  onSave,
  onCancel,
}) => {
  if (!isEditing) {
    return (
      <Descriptions column={{ xs: 1, sm: 2 }} bordered items={[
        { key: '姓名', label: '姓名', children: staff.full_name || '-' },
        { key: '帳號', label: '帳號', children: staff.username },
        { key: 'Email', label: 'Email', children: (
          <a href={`mailto:${staff.email}`}>{staff.email}</a>
        ) },
        { key: '部門', label: '部門', children: staff.department ? (
          <Tag icon={<BankOutlined />} color="blue">{staff.department}</Tag>
        ) : '-' },
        { key: '職稱', label: '職稱', children: staff.position || '-' },
        { key: '狀態', label: '狀態', children: (
          <Tag color={staff.is_active ? 'success' : 'default'}>
            {staff.is_active ? '啟用中' : '已停用'}
          </Tag>
        ) },
        { key: '最後登入', label: '最後登入', span: 2, children: staff.last_login ? new Date(staff.last_login).toLocaleString('zh-TW') : '尚未登入' },
      ]} />
    );
  }

  return (
    <Form form={form} layout="vertical">
      <Row gutter={16}>
        <Col xs={24} sm={12}>
          <Form.Item
            name="full_name"
            label="姓名"
            rules={[{ required: true, message: '請輸入姓名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="請輸入姓名" />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12}>
          <Form.Item name="username" label="帳號">
            <Input disabled />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        name="email"
        label="Email"
        rules={[
          { required: true, message: '請輸入 Email' },
          { type: 'email', message: '請輸入有效的 Email' },
        ]}
      >
        <Input prefix={<MailOutlined />} placeholder="請輸入 Email" />
      </Form.Item>

      <Row gutter={16}>
        <Col xs={24} sm={12}>
          <Form.Item name="department" label="部門">
            <AutoComplete
              placeholder="請選擇或輸入部門"
              allowClear
              options={departmentOptions.map(d => ({ label: d, value: d }))}
              filterOption={(input, option) =>
                (option?.value as string)?.includes(input) ?? false
              }
            />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12}>
          <Form.Item name="position" label="職稱">
            <Input prefix={<IdcardOutlined />} placeholder="請輸入職稱" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="密碼管理">
        <Space>
          <Switch
            checked={showPasswordChange}
            onChange={onShowPasswordChange}
            checkedChildren="修改密碼"
            unCheckedChildren="保持不變"
          />
          {!showPasswordChange && (
            <Text type="secondary">
              <KeyOutlined /> 如需修改密碼請開啟此選項
            </Text>
          )}
        </Space>
      </Form.Item>

      {showPasswordChange && (
        <Form.Item
          name="password"
          label="新密碼"
          rules={[
            { required: true, message: '請輸入新密碼' },
            { min: 6, message: '密碼至少 6 個字元' },
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="請輸入新密碼" />
        </Form.Item>
      )}

      <Form.Item name="is_active" label="狀態" valuePropName="checked">
        <Switch checkedChildren="啟用" unCheckedChildren="停用" />
      </Form.Item>

      <div style={{ textAlign: isMobile ? 'center' : 'right' }}>
        <Space size={isMobile ? 'small' : 'middle'}>
          <Button
            icon={<CloseOutlined />}
            size={isMobile ? 'small' : 'middle'}
            onClick={onCancel}
          >
            取消
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            size={isMobile ? 'small' : 'middle'}
            onClick={onSave}
            loading={saving}
          >
            儲存
          </Button>
        </Space>
      </div>
    </Form>
  );
};
