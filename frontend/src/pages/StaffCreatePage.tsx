/**
 * 新增承辦同仁頁面
 * @version 1.0.0
 * @date 2026-01-22
 */
import React, { useState } from 'react';
import { Form, Input, Select, Switch, Row, Col, App } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  LockOutlined,
  IdcardOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { FormPageLayout } from '../components/common/FormPage';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import { DEPARTMENT_OPTIONS } from '../constants';

const { Option } = Select;

export const StaffCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // 提交表單
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      await apiClient.post(API_ENDPOINTS.USERS.CREATE, values);
      message.success('承辦同仁建立成功');
      navigate(ROUTES.STAFF);
    } catch (error: unknown) {
      const err = error as { errorFields?: unknown; response?: { data?: { detail?: string } } };
      if (err?.errorFields) {
        message.error('請檢查表單欄位');
      } else {
        const detail = err?.response?.data?.detail;
        const errMsg = typeof detail === 'string' ? detail : '建立失敗';
        message.error(errMsg);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <FormPageLayout
      title="新增承辦同仁"
      backPath={ROUTES.STAFF}
      onSave={handleSave}
      saving={saving}
    >
      <Form
        form={form}
        layout="vertical"
        size="large"
        initialValues={{ is_active: true }}
      >
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
            <Form.Item
              name="username"
              label="帳號"
              rules={[
                { required: true, message: '請輸入帳號' },
                { min: 3, message: '帳號至少 3 個字元' },
              ]}
            >
              <Input placeholder="請輸入帳號" />
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

        <Form.Item
          name="password"
          label="密碼"
          rules={[
            { required: true, message: '請輸入密碼' },
            { min: 6, message: '密碼至少 6 個字元' },
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="請輸入密碼" />
        </Form.Item>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item name="department" label="部門">
              <Select placeholder="請選擇部門" allowClear>
                {DEPARTMENT_OPTIONS.map(dept => (
                  <Option key={dept} value={dept}>{dept}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="position" label="職稱">
              <Input prefix={<IdcardOutlined />} placeholder="請輸入職稱" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="is_active" label="狀態" valuePropName="checked">
          <Switch checkedChildren="啟用" unCheckedChildren="停用" />
        </Form.Item>
      </Form>
    </FormPageLayout>
  );
};

export default StaffCreatePage;
