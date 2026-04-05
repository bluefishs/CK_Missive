/**
 * 作業性質代碼管理頁面
 *
 * CRUD 管理作業性質代碼 (取代硬編碼常數)
 *
 * ACCEPTED EXCEPTION: Modal CRUD pattern retained.
 * Reason: Configuration/lookup table management (4 fields: code, label, description, sort_order).
 * Modal is the standard UX for simple code-management pages where navigating away would be disruptive.
 * Quality: Form validation (required rules), loading states (confirmLoading), error handling (onError).
 *
 * @version 1.0.1
 * @date 2026-04-05
 */
import React, { useState } from 'react';
import {
  Card, Table, Button, Space, Input, InputNumber, Switch, Form, Modal, App, Tag, Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, ReloadOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

interface CaseNatureCode {
  id: number;
  code: string;
  label: string;
  description?: string;
  sort_order: number;
  is_active: boolean;
}

const CaseNatureManagementPage: React.FC = () => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<CaseNatureCode | null>(null);
  const [form] = Form.useForm();

  // 列表查詢
  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ['case-nature-list'],
    queryFn: () => apiClient.post<CaseNatureCode[]>(API_ENDPOINTS.PM.CASE_NATURE_LIST, {}),
  });

  // 新增
  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiClient.post(API_ENDPOINTS.PM.CASE_NATURE_CREATE, data),
    onSuccess: () => {
      message.success('新增成功');
      invalidateAll();
      setModalOpen(false);
      form.resetFields();
    },
    onError: () => message.error('新增失敗，代碼可能已存在'),
  });

  // 更新
  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiClient.post(API_ENDPOINTS.PM.CASE_NATURE_UPDATE, data),
    onSuccess: () => {
      message.success('更新成功');
      invalidateAll();
      setModalOpen(false);
      setEditingItem(null);
      form.resetFields();
    },
    onError: () => message.error('更新失敗'),
  });

  // 停用/啟用
  const toggleMutation = useMutation({
    mutationFn: (data: { id: number; is_active: boolean }) =>
      apiClient.post(API_ENDPOINTS.PM.CASE_NATURE_UPDATE, data),
    onSuccess: () => {
      message.success('狀態已更新');
      invalidateAll();
    },
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['case-nature-list'] });
    queryClient.invalidateQueries({ queryKey: ['case-nature-options'] });
  };

  const handleAdd = () => {
    setEditingItem(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (item: CaseNatureCode) => {
    setEditingItem(item);
    form.setFieldsValue(item);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editingItem) {
      updateMutation.mutate({ id: editingItem.id, ...values });
    } else {
      createMutation.mutate(values);
    }
  };

  const columns: ColumnsType<CaseNatureCode> = [
    { title: '代碼', dataIndex: 'code', key: 'code', width: 80, align: 'center',
      render: (v: string) => <Tag color="blue" style={{ fontFamily: 'monospace' }}>{v}</Tag> },
    { title: '標籤', dataIndex: 'label', key: 'label', width: 140 },
    { title: '說明', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 70, align: 'center' },
    { title: '狀態', dataIndex: 'is_active', key: 'is_active', width: 80, align: 'center',
      render: (active: boolean, record) => (
        <Switch size="small" checked={active}
          onChange={(v) => toggleMutation.mutate({ id: record.id, is_active: v })} />
      ),
    },
    { title: '操作', key: 'action', width: 80, align: 'center',
      render: (_, record) => (
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
          編輯
        </Button>
      ),
    },
  ];

  return (
    <ResponsiveContent>
      <Card
        title={<Title level={4} style={{ margin: 0 }}>作業性質代碼管理</Title>}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增代碼</Button>
          </Space>
        }
      >
        <Table<CaseNatureCode>
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={false}
        />
      </Card>

      <Modal
        title={editingItem ? '編輯作業性質' : '新增作業性質'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); setEditingItem(null); form.resetFields(); }}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" size="small">
          <Form.Item name="code" label="代碼" rules={[{ required: true }]}
            extra="兩位數字，如 01, 12">
            <Input maxLength={10} disabled={!!editingItem} placeholder="如 12" />
          </Form.Item>
          <Form.Item name="label" label="標籤" rules={[{ required: true }]}>
            <Input maxLength={100} placeholder="如 地面測量" />
          </Form.Item>
          <Form.Item name="description" label="說明">
            <Input.TextArea maxLength={500} rows={2} placeholder="代碼用途說明" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </ResponsiveContent>
  );
};

export default CaseNatureManagementPage;
