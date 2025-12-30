/**
 * 使用者管理表格欄位配置
 * @description 從 UserManagementPage.tsx 提取
 */
import React from 'react';
import { Space, Tag, Avatar, Button, Tooltip, Popconfirm, Typography } from 'antd';
import {
  UserOutlined,
  EditOutlined,
  DeleteOutlined,
  KeyOutlined,
  GoogleOutlined,
  MailOutlined,
  SafetyOutlined,
  StopOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  USER_ROLES,
  USER_STATUSES,
  getRoleDisplayName,
  getStatusDisplayName
} from '../constants/permissions';
import type { User } from '../types/user';

const { Text } = Typography;

interface UserTableColumnsConfig {
  onEdit: (user: User) => void;
  onEditPermissions: (user: User) => void;
  onDelete: (userId: number) => void;
}

export const createUserTableColumns = ({
  onEdit,
  onEditPermissions,
  onDelete,
}: UserTableColumnsConfig): ColumnsType<User> => [
  {
    title: '使用者',
    key: 'user',
    dataIndex: 'full_name',
    sorter: true,
    render: (_, record) => (
      <Space>
        <Avatar
          src={record.avatar_url}
          icon={<UserOutlined />}
          style={{
            backgroundColor: record.auth_provider === 'google' ? '#4285f4' : '#1976d2'
          }}
        />
        <div>
          <div style={{ fontWeight: 500 }}>{record.full_name || record.username}</div>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.email}
          </Text>
        </div>
      </Space>
    ),
  },
  {
    title: '認證方式',
    dataIndex: 'auth_provider',
    key: 'auth_provider',
    sorter: true,
    filters: [
      { text: 'Google', value: 'google' },
      { text: '電子郵件', value: 'email' },
    ],
    render: (provider: string) => (
      <Tag
        icon={provider === 'google' ? <GoogleOutlined /> : <MailOutlined />}
        color={provider === 'google' ? 'blue' : 'green'}
      >
        {provider === 'google' ? 'Google' : '電子郵件'}
      </Tag>
    ),
  },
  {
    title: '角色',
    dataIndex: 'role',
    key: 'role',
    sorter: true,
    filters: [
      { text: '超級管理員', value: 'superuser' },
      { text: '管理員', value: 'admin' },
      { text: '一般使用者', value: 'user' },
      { text: '未驗證', value: 'unverified' },
    ],
    render: (role: string, record) => {
      const roleConfig = USER_ROLES[role as keyof typeof USER_ROLES];
      const color = role === 'superuser' ? 'red' :
                   role === 'admin' ? 'orange' :
                   role === 'unverified' ? 'default' : 'blue';

      return (
        <Space>
          <Tag color={color}>
            {getRoleDisplayName(role)}
          </Tag>
          {record.is_admin && <SafetyOutlined style={{ color: '#f5222d' }} />}
          {!roleConfig?.can_login && (
            <Tooltip title="此角色無法登入系統">
              <StopOutlined style={{ color: '#faad14' }} />
            </Tooltip>
          )}
        </Space>
      );
    },
  },
  {
    title: '狀態',
    dataIndex: 'status',
    key: 'status',
    sorter: true,
    filters: [
      { text: '啟用', value: 'active' },
      { text: '待審核', value: 'pending' },
      { text: '暫停', value: 'suspended' },
      { text: '停用', value: 'inactive' },
    ],
    render: (status: string, record) => {
      const statusConfig = USER_STATUSES[status as keyof typeof USER_STATUSES];
      const roleConfig = USER_ROLES[record.role as keyof typeof USER_ROLES];
      const color = status === 'active' ? 'green' :
                   status === 'pending' ? 'orange' :
                   status === 'suspended' ? 'volcano' : 'red';

      const canLogin = record.is_active &&
                      (statusConfig?.can_login ?? true) &&
                      (roleConfig?.can_login ?? true);

      return (
        <Space direction="vertical" size={0}>
          <Tag color={color}>
            {getStatusDisplayName(status)}
          </Tag>
          {record.suspended_reason && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              {record.suspended_reason}
            </Text>
          )}
          {!canLogin && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              🚫 無法登入
            </Text>
          )}
        </Space>
      );
    },
  },
  {
    title: '註冊時間',
    dataIndex: 'created_at',
    key: 'created_at',
    sorter: true,
    render: (date: string) => new Date(date).toLocaleDateString('zh-TW'),
  },
  {
    title: '最後登入',
    dataIndex: 'last_login',
    key: 'last_login',
    sorter: true,
    render: (date: string) => date ? new Date(date).toLocaleDateString('zh-TW') : '從未登入',
  },
  {
    title: '權限維護',
    key: 'actions',
    render: (_, record) => (
      <Space>
        <Tooltip title="編輯使用者">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => onEdit(record)}
          />
        </Tooltip>
        <Tooltip title="管理權限">
          <Button
            type="text"
            icon={<KeyOutlined />}
            onClick={() => onEditPermissions(record)}
          />
        </Tooltip>
        <Popconfirm
          title="確定要刪除此使用者嗎？"
          onConfirm={() => onDelete(record.id)}
          okText="確定"
          cancelText="取消"
        >
          <Tooltip title="刪除使用者">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
            />
          </Tooltip>
        </Popconfirm>
      </Space>
    ),
  },
];
