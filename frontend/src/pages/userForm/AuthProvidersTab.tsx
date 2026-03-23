/**
 * 使用者認證方式 Tab
 *
 * 顯示認證方式 + LINE 綁定/解除綁定
 */
import React, { useState } from 'react';
import { Descriptions, Tag, Space, Divider, Form, Input, Row, Col, Button, Popconfirm } from 'antd';
import { LinkOutlined, DisconnectOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { adminUsersApi } from '../../api/adminUsersApi';
import { App } from 'antd';

interface UserInfo {
  auth_provider?: string;
  auth_providers?: string[];
  google_id?: string;
  line_user_id?: string;
  line_display_name?: string;
}

interface Props {
  userId: number;
  user?: UserInfo;
}

const AuthProvidersTab: React.FC<Props> = ({ userId, user }) => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [lineIdInput, setLineIdInput] = useState('');
  const [lineNameInput, setLineNameInput] = useState('');

  const bindLineMutation = useMutation({
    mutationFn: () => adminUsersApi.bindLine(userId, lineIdInput, lineNameInput || undefined),
    onSuccess: () => {
      message.success('LINE 綁定成功');
      setLineIdInput('');
      setLineNameInput('');
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
    onError: (error: Error) => message.error(error.message || 'LINE 綁定失敗'),
  });

  const unbindLineMutation = useMutation({
    mutationFn: () => adminUsersApi.unbindLine(userId),
    onSuccess: () => {
      message.success('LINE 綁定已解除');
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
    onError: (error: Error) => message.error(error.message || '解除綁定失敗'),
  });

  const AUTH_PROVIDER_CONFIG: Record<string, { label: string; color: string }> = {
    email: { label: '電子郵件', color: 'green' },
    google: { label: 'Google', color: 'blue' },
    line: { label: 'LINE', color: 'lime' },
    internal: { label: '內網', color: 'orange' },
  };

  return (
    <div>
      <Descriptions column={1} bordered size="small" style={{ marginBottom: 24 }}>
        <Descriptions.Item label="主要認證方式">
          <Tag color={user?.auth_provider === 'google' ? 'blue' : user?.auth_provider === 'line' ? 'lime' : 'green'}>
            {user?.auth_provider === 'google' ? 'Google' : user?.auth_provider === 'line' ? 'LINE' : '電子郵件'}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="可用認證方式">
          <Space>
            {(user?.auth_providers || []).map((p) => {
              const c = AUTH_PROVIDER_CONFIG[p] || { label: p, color: 'default' };
              return <Tag key={p} color={c.color}>{c.label}</Tag>;
            })}
            {(!user?.auth_providers || user.auth_providers.length === 0) && <Tag>無</Tag>}
          </Space>
        </Descriptions.Item>
        {user?.google_id && (
          <Descriptions.Item label="Google ID">{user.google_id}</Descriptions.Item>
        )}
      </Descriptions>

      <Divider>LINE 帳號綁定</Divider>

      {user?.line_user_id ? (
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="LINE User ID"><code>{user.line_user_id}</code></Descriptions.Item>
          <Descriptions.Item label="LINE 顯示名稱">{user.line_display_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="操作">
            <Popconfirm title="確定解除此使用者的 LINE 綁定？" onConfirm={() => unbindLineMutation.mutate()} okText="確定" cancelText="取消">
              <Button danger icon={<DisconnectOutlined />} loading={unbindLineMutation.isPending} size="small">
                解除綁定
              </Button>
            </Popconfirm>
          </Descriptions.Item>
        </Descriptions>
      ) : (
        <Form layout="vertical">
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item label="LINE User ID" required>
                <Input placeholder="U773510136cb50aa415ed6852bb3ba336" value={lineIdInput} onChange={(e) => setLineIdInput(e.target.value)} maxLength={64} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="LINE 顯示名稱">
                <Input placeholder="選填，預設使用帳號姓名" value={lineNameInput} onChange={(e) => setLineNameInput(e.target.value)} maxLength={100} />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary" icon={<LinkOutlined />} onClick={() => bindLineMutation.mutate()} loading={bindLineMutation.isPending} disabled={!lineIdInput || lineIdInput.length < 10}>
            綁定 LINE
          </Button>
        </Form>
      )}
    </div>
  );
};

export default AuthProvidersTab;
