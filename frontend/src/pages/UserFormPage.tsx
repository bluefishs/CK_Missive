/**
 * 使用者表單頁
 *
 * 共享新增/編輯表單，根據路由參數自動切換模式
 * 導航模式：編輯模式支援刪除功能
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Select, Row, Col, App, Modal, Switch, Tabs, Divider } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FormPageLayout } from '../components/common/FormPage';
import { adminUsersApi } from '../api/adminUsersApi';
import { ROUTES } from '../router/types';
import { USER_ROLES, USER_STATUSES } from '../constants/permissions';
import PermissionManager from '../components/admin/PermissionManager';
import type { User, UserPermissions } from '../types/api';

const { Option } = Select;

export const UserFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [permissionForm] = Form.useForm();
  const queryClient = useQueryClient();

  const isEdit = Boolean(id);
  const title = isEdit ? '編輯使用者' : '新增使用者';
  const userId = id ? parseInt(id, 10) : undefined;

  // 編輯模式：載入使用者資料
  const { data: user, isLoading } = useQuery({
    queryKey: ['user', userId],
    queryFn: async () => {
      const response = await adminUsersApi.getUsers({ page: 1, per_page: 100 });
      return response.items?.find((u: User) => u.id === userId);
    },
    enabled: isEdit && !!userId,
  });

  // 載入使用者權限
  const { data: userPermissions } = useQuery({
    queryKey: ['userPermissions', userId],
    queryFn: async () => {
      return await adminUsersApi.getUserPermissions(userId!);
    },
    enabled: isEdit && !!userId,
  });

  // 載入角色列表
  const { data: rolesData } = useQuery({
    queryKey: ['availablePermissions'],
    queryFn: async () => {
      return await adminUsersApi.getAvailablePermissions();
    },
  });

  const roles = rolesData?.roles || [];

  // 填入表單資料
  useEffect(() => {
    if (user) {
      form.setFieldsValue({
        email: user.email,
        username: user.username,
        full_name: user.full_name,
        is_active: user.is_active,
        is_admin: user.is_admin,
        role: user.role,
        status: user.status || (user.is_active ? 'active' : 'inactive'),
        department: user.department,
        position: user.position,
      });
    }
  }, [user, form]);

  // 填入權限資料
  useEffect(() => {
    if (userPermissions) {
      permissionForm.setFieldsValue({
        role: userPermissions.role,
        permissions: userPermissions.permissions,
      });
    }
  }, [userPermissions, permissionForm]);

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => adminUsersApi.createUser(data),
    onSuccess: () => {
      message.success('使用者建立成功');
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      navigate(ROUTES.USER_MANAGEMENT);
    },
    onError: (error: Error) => {
      message.error((error as any)?.response?.data?.detail || error?.message || '建立失敗');
    },
  });

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: any) => adminUsersApi.updateUser(userId!, data),
    onSuccess: () => {
      message.success('使用者更新成功');
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      navigate(ROUTES.USER_MANAGEMENT);
    },
    onError: (error: Error) => {
      message.error((error as any)?.response?.data?.detail || error?.message || '更新失敗');
    },
  });

  // 更新權限 mutation
  const updatePermissionsMutation = useMutation({
    mutationFn: (data: UserPermissions) => adminUsersApi.updateUserPermissions(userId!, data),
    onSuccess: () => {
      message.success('權限更新成功');
      queryClient.invalidateQueries({ queryKey: ['userPermissions', userId] });
    },
    onError: (error: Error) => {
      message.error((error as any)?.response?.data?.detail || error?.message || '權限更新失敗');
    },
  });

  // 刪除 mutation
  const deleteMutation = useMutation({
    mutationFn: () => adminUsersApi.deleteUser(userId!),
    onSuccess: () => {
      message.success('使用者刪除成功');
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      navigate(ROUTES.USER_MANAGEMENT);
    },
    onError: (error: Error) => {
      message.error((error as any)?.response?.data?.detail || error?.message || '刪除失敗');
    },
  });

  // 刪除確認
  const handleDelete = () => {
    Modal.confirm({
      title: '確定要刪除此使用者？',
      icon: <ExclamationCircleOutlined />,
      content: '刪除後將無法復原，該使用者將無法登入系統。',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(),
    });
  };

  // 保存處理
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      const userData = {
        ...values,
        is_active: values.status === 'active',
      };
      delete userData.status;

      if (isEdit) {
        updateMutation.mutate(userData);
      } else {
        createMutation.mutate(userData);
      }
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  // 保存權限
  const handleSavePermissions = async () => {
    try {
      const values = await permissionForm.validateFields();
      updatePermissionsMutation.mutate({
        user_id: userId!,
        role: values.role,
        permissions: values.permissions || [],
      });
    } catch {
      message.error('請檢查權限設定');
    }
  };

  // 角色變更時更新預設權限
  const handleRoleChange = (role: string) => {
    const selectedRole = roles.find((r: any) => r.name === role);
    if (selectedRole) {
      permissionForm.setFieldsValue({
        permissions: selectedRole.default_permissions,
      });
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const tabItems = [
    {
      key: 'basic',
      label: '基本資料',
      children: (
        <Form form={form} layout="vertical" size="large">
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item
                name="email"
                label="電子郵件"
                rules={[
                  { required: true, message: '請輸入電子郵件' },
                  { type: 'email', message: '請輸入有效的電子郵件' },
                ]}
              >
                <Input placeholder="請輸入電子郵件" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                name="username"
                label="使用者名稱"
                rules={[{ required: true, message: '請輸入使用者名稱' }]}
              >
                <Input placeholder="請輸入使用者名稱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="full_name" label="完整姓名">
                <Input placeholder="請輸入完整姓名" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="department" label="部門">
                <Input placeholder="請輸入部門" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="position" label="職位">
                <Input placeholder="請輸入職位" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              {!isEdit && (
                <Form.Item
                  name="password"
                  label="密碼"
                  rules={[
                    { required: true, message: '請輸入密碼' },
                    { min: 6, message: '密碼至少需要6個字元' },
                  ]}
                >
                  <Input.Password placeholder="輸入新使用者密碼" />
                </Form.Item>
              )}
            </Col>
          </Row>

          <Divider>帳號設定</Divider>

          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Form.Item
                name="role"
                label="角色"
                rules={[{ required: true, message: '請選擇角色' }]}
              >
                <Select placeholder="請選擇角色">
                  {Object.entries(USER_ROLES).map(([key, role]) => (
                    <Option key={key} value={key}>
                      {role.name_zh}
                      {!role.can_login && ' (無法登入)'}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item
                name="status"
                label="狀態"
                rules={[{ required: true, message: '請選擇狀態' }]}
              >
                <Select placeholder="請選擇狀態">
                  {Object.entries(USER_STATUSES).map(([key, status]) => (
                    <Option key={key} value={key}>
                      {status.name_zh}
                      {!status.can_login && ' (無法登入)'}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item name="is_admin" label="管理員" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="suspended_reason"
            label="暫停原因"
            tooltip="當狀態為暫停時，可填寫暫停原因"
          >
            <Input.TextArea rows={2} placeholder="請輸入暫停或停用的原因..." maxLength={200} />
          </Form.Item>
        </Form>
      ),
    },
  ];

  // 編輯模式才顯示權限 Tab
  if (isEdit) {
    tabItems.push({
      key: 'permissions',
      label: '權限設定',
      children: (
        <Form form={permissionForm} layout="vertical" size="large">
          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '請選擇角色' }]}
          >
            <Select placeholder="請選擇角色" onChange={handleRoleChange}>
              {roles.map((role: any) => (
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
              permissionForm.setFieldsValue({ permissions });
            }}
            readOnly={false}
          />

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <button
              type="button"
              className="ant-btn ant-btn-primary"
              onClick={handleSavePermissions}
              disabled={updatePermissionsMutation.isPending}
            >
              {updatePermissionsMutation.isPending ? '儲存中...' : '儲存權限'}
            </button>
          </div>
        </Form>
      ),
    });
  }

  return (
    <FormPageLayout
      title={title}
      backPath={ROUTES.USER_MANAGEMENT}
      onSave={handleSave}
      onDelete={isEdit ? handleDelete : undefined}
      loading={isEdit && isLoading}
      saving={isSaving}
      deleting={deleteMutation.isPending}
    >
      <Tabs items={tabItems} defaultActiveKey="basic" />
    </FormPageLayout>
  );
};

export default UserFormPage;
