/**
 * PM 案件人員管理頁籤
 *
 * 提供案件人員的 CRUD 功能（子表格模式）
 */
import { useState, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, Select, Switch, DatePicker, Tag, Badge, Popconfirm, Space, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { PMCaseStaff, PMStaffRole } from '../../types/pm';
import { PM_STAFF_ROLE_LABELS } from '../../types/pm';
import {
  usePMCaseStaff,
  useCreatePMCaseStaff,
  useUpdatePMCaseStaff,
  useDeletePMCaseStaff,
} from '../../hooks/business/usePMCases';

interface StaffTabProps {
  pmCaseId: number;
}

const ROLE_TAG_COLOR: Record<PMStaffRole, string> = {
  project_manager: 'blue',
  engineer: 'green',
  surveyor: 'orange',
  assistant: 'cyan',
  other: 'default',
};

interface FormValues {
  staff_name: string;
  role: PMStaffRole;
  is_primary?: boolean;
  start_date?: dayjs.Dayjs;
  end_date?: dayjs.Dayjs;
  notes?: string;
}

export default function StaffTab({ pmCaseId }: StaffTabProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<PMCaseStaff | null>(null);
  const [form] = Form.useForm<FormValues>();

  const { data: staffList, isLoading } = usePMCaseStaff(pmCaseId);
  const createMutation = useCreatePMCaseStaff();
  const updateMutation = useUpdatePMCaseStaff();
  const deleteMutation = useDeletePMCaseStaff();

  const handleAdd = useCallback(() => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  }, [form]);

  const handleEdit = useCallback(
    (record: PMCaseStaff) => {
      setEditingRecord(record);
      form.setFieldsValue({
        staff_name: record.staff_name,
        role: record.role as PMStaffRole,
        is_primary: record.is_primary,
        start_date: record.start_date ? dayjs(record.start_date) : undefined,
        end_date: record.end_date ? dayjs(record.end_date) : undefined,
        notes: record.notes ?? undefined,
      });
      setModalOpen(true);
    },
    [form],
  );

  const handleDelete = useCallback(
    (id: number) => {
      deleteMutation.mutate(
        { id, pmCaseId },
        { onSuccess: () => message.success('人員已移除') },
      );
    },
    [deleteMutation, pmCaseId],
  );

  const handleSubmit = useCallback(async () => {
    const values = await form.validateFields();
    const payload = {
      staff_name: values.staff_name,
      role: values.role,
      is_primary: values.is_primary,
      start_date: values.start_date?.format('YYYY-MM-DD'),
      end_date: values.end_date?.format('YYYY-MM-DD'),
      notes: values.notes,
    };

    if (editingRecord) {
      updateMutation.mutate(
        { id: editingRecord.id, pmCaseId, data: payload },
        {
          onSuccess: () => {
            message.success('人員資料已更新');
            setModalOpen(false);
          },
        },
      );
    } else {
      createMutation.mutate(
        { ...payload, pm_case_id: pmCaseId, staff_name: payload.staff_name, role: payload.role },
        {
          onSuccess: () => {
            message.success('人員已新增');
            setModalOpen(false);
          },
        },
      );
    }
  }, [form, editingRecord, pmCaseId, createMutation, updateMutation]);

  const roleOptions = Object.entries(PM_STAFF_ROLE_LABELS).map(([value, label]) => ({
    value,
    label,
  }));

  const columns: ColumnsType<PMCaseStaff> = [
    {
      title: '姓名',
      dataIndex: 'staff_name',
      key: 'staff_name',
      ellipsis: true,
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 120,
      render: (val: PMStaffRole) => (
        <Tag color={ROLE_TAG_COLOR[val]}>{PM_STAFF_ROLE_LABELS[val]}</Tag>
      ),
    },
    {
      title: '主要負責人',
      dataIndex: 'is_primary',
      key: 'is_primary',
      width: 110,
      align: 'center',
      render: (val: boolean) =>
        val ? <Badge status="success" text="是" /> : <Badge status="default" text="否" />,
    },
    {
      title: '起始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '結束日期',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: PMCaseStaff) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            編輯
          </Button>
          <Popconfirm
            title="確定移除此人員？"
            onConfirm={() => handleDelete(record.id)}
            okText="確定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              刪除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增人員
        </Button>
      </div>

      <Table<PMCaseStaff>
        rowKey="id"
        columns={columns}
        dataSource={staffList ?? []}
        loading={isLoading}
        pagination={false}
        size="small"
      />

      <Modal
        title={editingRecord ? '編輯人員' : '新增人員'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={{ is_primary: false }}>
          <Form.Item
            name="staff_name"
            label="姓名"
            rules={[{ required: true, message: '請輸入姓名' }]}
          >
            <Input placeholder="請輸入姓名" />
          </Form.Item>

          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '請選擇角色' }]}
          >
            <Select placeholder="請選擇角色" options={roleOptions} />
          </Form.Item>

          <Form.Item name="is_primary" label="主要負責人" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="start_date" label="起始日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="end_date" label="結束日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={3} placeholder="備註" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
