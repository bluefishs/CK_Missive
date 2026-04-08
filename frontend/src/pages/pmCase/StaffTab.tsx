/**
 * 承辦同仁 Tab（統一版）
 *
 * 使用統一人員表 project_user_assignments，透過 case_code 查詢。
 * 角色選項與 Contract Cases 一致（計畫主持/計畫協同/專案PM/職安主管）。
 * 使用者下拉選擇使用 useUsersDropdown（與 Contract Cases 一致）。
 *
 * @version 4.0.0 — 統一版型，移除外部人員，使用 useUsersDropdown
 */
import { useState } from 'react';
import { Button, Modal, Form, Select, Tag, Popconfirm, App } from 'antd';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import { PlusOutlined, DeleteOutlined, UserOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { useUsersDropdown } from '../../hooks';
import { STAFF_ROLE_OPTIONS } from '../contractCase/tabs/constants';

interface StaffRecord {
  id: number;
  user_id?: number;
  staff_name?: string;
  user_name: string;
  role?: string;
  is_primary?: boolean;
  status?: string;
}

interface StaffListResponse {
  staff: StaffRecord[];
  total: number;
}

interface StaffTabProps {
  caseCode: string;
}

export default function StaffTab({ caseCode }: StaffTabProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);

  const { users } = useUsersDropdown();
  const queryKey = ['project-staff-by-case', caseCode];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => apiClient.post<StaffListResponse>(
      API_ENDPOINTS.PROJECT_STAFF.CASE_LIST(caseCode)
    ),
    enabled: !!caseCode,
  });

  const createMutation = useMutation({
    mutationFn: (values: { user_id: number; role: string }) =>
      apiClient.post(API_ENDPOINTS.PROJECT_STAFF.CREATE, {
        case_code: caseCode,
        user_id: values.user_id,
        role: values.role,
      }),
    onSuccess: () => {
      message.success('人員新增成功');
      queryClient.invalidateQueries({ queryKey });
      setModalVisible(false);
      form.resetFields();
    },
    onError: () => message.error('新增失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: (staffId: number) =>
      apiClient.post(API_ENDPOINTS.PROJECT_STAFF.ASSIGNMENT_DELETE(staffId)),
    onSuccess: () => {
      message.success('已移除人員');
      queryClient.invalidateQueries({ queryKey });
    },
    onError: () => message.error('移除失敗'),
  });

  const staff = data?.staff ?? [];

  const getRoleColor = (role?: string) => {
    const opt = STAFF_ROLE_OPTIONS.find(o => o.value === role);
    return opt?.color || 'default';
  };

  const columns: ColumnsType<StaffRecord> = [
    {
      title: '姓名',
      key: 'name',
      render: (_, r) => (
        <span>
          <UserOutlined style={{ marginRight: 6, color: '#999' }} />
          {r.user_name || r.staff_name || '-'}
        </span>
      ),
    },
    {
      title: '角色/職責',
      dataIndex: 'role',
      key: 'role',
      width: 110,
      render: (role: string) => (
        <Tag color={getRoleColor(role)}>
          {STAFF_ROLE_OPTIONS.find(o => o.value === role)?.label || role || '-'}
        </Tag>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (s: string) => (
        <Tag color={s === 'active' ? 'green' : s === 'completed' ? 'blue' : 'default'}>
          {s === 'active' ? '在職' : s === 'completed' ? '已結束' : s || '-'}
        </Tag>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_, r) => (
        <Popconfirm title="確定移除此人員？" onConfirm={() => deleteMutation.mutate(r.id)}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  // 使用者下拉選項（排除已加入的人員）
  const existingUserIds = new Set(staff.map(s => s.user_id).filter(Boolean));
  const userOptions = users
    .filter(u => !existingUserIds.has(u.id))
    .map(u => ({
      value: u.id,
      label: `${u.full_name || u.username}${u.email ? ` (${u.email})` : ''}`,
    }));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontWeight: 600 }}>承辦同仁 ({staff.length})</span>
        <Button size="small" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          新增人員
        </Button>
      </div>

      <EnhancedTable<StaffRecord>
        dataSource={staff}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={false}
      />

      <Modal
        title="新增承辦同仁"
        open={modalVisible}
        onCancel={() => { setModalVisible(false); form.resetFields(); }}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(v) => createMutation.mutate(v)}>
          <Form.Item name="user_id" label="選擇同仁"
            rules={[{ required: true, message: '請選擇同仁' }]}
          >
            <Select
              showSearch
              placeholder="搜尋同仁..."
              optionFilterProp="label"
              options={userOptions}
            />
          </Form.Item>
          <Form.Item name="role" label="角色/職責" initialValue="專案PM"
            rules={[{ required: true, message: '請選擇角色' }]}
          >
            <Select options={STAFF_ROLE_OPTIONS.map(o => ({ value: o.value, label: o.label }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
