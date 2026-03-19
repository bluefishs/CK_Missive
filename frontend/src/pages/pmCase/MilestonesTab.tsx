/**
 * PM 案件里程碑管理頁籤
 *
 * 提供里程碑的 CRUD 功能（子表格模式）
 */
import { useState, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, Select, DatePicker, Tag, Popconfirm, Space, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { PMMilestone, PMMilestoneType, PMMilestoneStatus } from '../../types/pm';
import { PM_MILESTONE_TYPE_LABELS } from '../../types/pm';
import {
  usePMMilestones,
  useCreatePMMilestone,
  useUpdatePMMilestone,
  useDeletePMMilestone,
} from '../../hooks/business/usePMCases';

interface MilestonesTabProps {
  pmCaseId: number;
}

const MILESTONE_STATUS_COLOR: Record<PMMilestoneStatus, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  overdue: 'error',
  skipped: 'warning',
};

const MILESTONE_STATUS_LABELS: Record<PMMilestoneStatus, string> = {
  pending: '待辦',
  in_progress: '進行中',
  completed: '已完成',
  overdue: '逾期',
  skipped: '略過',
};

interface FormValues {
  milestone_name: string;
  milestone_type?: PMMilestoneType;
  planned_date?: dayjs.Dayjs;
  actual_date?: dayjs.Dayjs;
  status?: PMMilestoneStatus;
  sort_order?: number;
  notes?: string;
}

export default function MilestonesTab({ pmCaseId }: MilestonesTabProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<PMMilestone | null>(null);
  const [form] = Form.useForm<FormValues>();

  const { data: milestones, isLoading } = usePMMilestones(pmCaseId);
  const createMutation = useCreatePMMilestone();
  const updateMutation = useUpdatePMMilestone();
  const deleteMutation = useDeletePMMilestone();

  const handleAdd = useCallback(() => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  }, [form]);

  const handleEdit = useCallback(
    (record: PMMilestone) => {
      setEditingRecord(record);
      form.setFieldsValue({
        milestone_name: record.milestone_name,
        milestone_type: (record.milestone_type ?? undefined) as PMMilestoneType | undefined,
        planned_date: record.planned_date ? dayjs(record.planned_date) : undefined,
        actual_date: record.actual_date ? dayjs(record.actual_date) : undefined,
        status: record.status as PMMilestoneStatus,
        sort_order: record.sort_order,
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
        { onSuccess: () => message.success('里程碑已刪除') },
      );
    },
    [deleteMutation, pmCaseId],
  );

  const handleSubmit = useCallback(async () => {
    const values = await form.validateFields();
    const payload = {
      milestone_name: values.milestone_name,
      milestone_type: values.milestone_type,
      planned_date: values.planned_date?.format('YYYY-MM-DD'),
      actual_date: values.actual_date?.format('YYYY-MM-DD'),
      status: values.status,
      sort_order: values.sort_order,
      notes: values.notes,
    };

    if (editingRecord) {
      updateMutation.mutate(
        { id: editingRecord.id, pmCaseId, data: payload },
        {
          onSuccess: () => {
            message.success('里程碑已更新');
            setModalOpen(false);
          },
        },
      );
    } else {
      createMutation.mutate(
        { ...payload, pm_case_id: pmCaseId, milestone_name: payload.milestone_name },
        {
          onSuccess: () => {
            message.success('里程碑已建立');
            setModalOpen(false);
          },
        },
      );
    }
  }, [form, editingRecord, pmCaseId, createMutation, updateMutation]);

  const columns: ColumnsType<PMMilestone> = [
    {
      title: '里程碑名稱',
      dataIndex: 'milestone_name',
      key: 'milestone_name',
      ellipsis: true,
    },
    {
      title: '類型',
      dataIndex: 'milestone_type',
      key: 'milestone_type',
      width: 100,
      render: (val: PMMilestoneType | null) => (val ? <Tag>{PM_MILESTONE_TYPE_LABELS[val]}</Tag> : '-'),
    },
    {
      title: '預計日期',
      dataIndex: 'planned_date',
      key: 'planned_date',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '實際日期',
      dataIndex: 'actual_date',
      key: 'actual_date',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val: PMMilestoneStatus) => (
        <Tag color={MILESTONE_STATUS_COLOR[val]}>{MILESTONE_STATUS_LABELS[val]}</Tag>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 70,
      align: 'center',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: PMMilestone) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            編輯
          </Button>
          <Popconfirm
            title="確定刪除此里程碑？"
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

  const milestoneTypeOptions = Object.entries(PM_MILESTONE_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  }));

  const statusOptions = Object.entries(MILESTONE_STATUS_LABELS).map(([value, label]) => ({
    value,
    label,
  }));

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增里程碑
        </Button>
      </div>

      <Table<PMMilestone>
        rowKey="id"
        columns={columns}
        dataSource={milestones ?? []}
        loading={isLoading}
        pagination={false}
        size="small"
      />

      <Modal
        title={editingRecord ? '編輯里程碑' : '新增里程碑'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="milestone_name"
            label="里程碑名稱"
            rules={[{ required: true, message: '請輸入里程碑名稱' }]}
          >
            <Input placeholder="請輸入名稱" />
          </Form.Item>

          <Form.Item name="milestone_type" label="類型">
            <Select placeholder="請選擇類型" allowClear options={milestoneTypeOptions} />
          </Form.Item>

          <Form.Item name="planned_date" label="預計日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="actual_date" label="實際日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="status" label="狀態">
            <Select placeholder="請選擇狀態" allowClear options={statusOptions} />
          </Form.Item>

          <Form.Item name="sort_order" label="排序">
            <Input type="number" placeholder="排序值" />
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={3} placeholder="備註" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
