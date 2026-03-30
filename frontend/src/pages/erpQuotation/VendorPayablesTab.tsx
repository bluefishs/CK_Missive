/**
 * ERP 廠商應付管理 Tab
 *
 * 報價單詳情頁的廠商應付子表，支援 CRUD 操作。
 *
 * @version 1.0.0
 */

import React, { useState, useCallback } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Popconfirm,
  App,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import type {
  ERPVendorPayableDetail as ERPVendorPayable,
  ERPVendorPayableCreate,
  ERPVendorPayableUpdate,
  ERPPayableStatus,
} from '../../types/erp';
import { ERP_PAYABLE_STATUS_LABELS } from '../../types/erp';
import {
  useERPVendorPayables,
  useERPBillings,
  useCreateERPVendorPayable,
  useUpdateERPVendorPayable,
  useDeleteERPVendorPayable,
} from '../../hooks/business/useERPQuotations';

// =============================================================================
// 常數
// =============================================================================

const PAYABLE_STATUS_COLORS: Record<ERPPayableStatus, string> = {
  unpaid: 'default',
  partial: 'orange',
  paid: 'green',
};

// =============================================================================
// Props
// =============================================================================

export interface VendorPayablesTabProps {
  erpQuotationId: number;
}

// =============================================================================
// 元件
// =============================================================================

const VendorPayablesTab: React.FC<VendorPayablesTabProps> = ({ erpQuotationId }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ERPVendorPayable | null>(null);

  // Data
  const { data: payables, isLoading } = useERPVendorPayables(erpQuotationId);

  // 取得期別選項
  const { data: billings } = useERPBillings(erpQuotationId);
  const billingOptions = (billings ?? []).map(b => ({
    value: b.id,
    label: `${b.billing_period || '未命名'} — ${b.billing_date || ''} (${Number(b.billing_amount || 0).toLocaleString()})`,
  }));
  const createMutation = useCreateERPVendorPayable();
  const updateMutation = useUpdateERPVendorPayable(erpQuotationId);
  const deleteMutation = useDeleteERPVendorPayable(erpQuotationId);

  // Handlers
  const handleAdd = useCallback(() => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  }, [form]);

  const handleEdit = useCallback((record: ERPVendorPayable) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      due_date: record.due_date ? dayjs(record.due_date) : null,
      payable_amount: record.payable_amount ? Number(record.payable_amount) : null,
    });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('應付紀錄已刪除');
    } catch {
      message.error('刪除失敗');
    }
  }, [deleteMutation, message]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        due_date: values.due_date?.format('YYYY-MM-DD') ?? undefined,
        payable_amount: String(values.payable_amount),
      };

      if (editingRecord) {
        const updateData: ERPVendorPayableUpdate = { ...payload };
        await updateMutation.mutateAsync({ id: editingRecord.id, data: updateData });
        message.success('應付紀錄已更新');
      } else {
        const createData: ERPVendorPayableCreate = {
          ...payload,
          erp_quotation_id: erpQuotationId,
        };
        await createMutation.mutateAsync(createData);
        message.success('應付紀錄已新增');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingRecord(null);
    } catch {
      // form validation failed or API error
    }
  }, [form, editingRecord, erpQuotationId, createMutation, updateMutation, message]);

  const handleCancel = useCallback(() => {
    setModalOpen(false);
    form.resetFields();
    setEditingRecord(null);
  }, [form]);

  // Columns
  const columns: ColumnsType<ERPVendorPayable> = [
    {
      title: '廠商名稱',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      width: 150,
    },
    {
      title: '應付金額',
      dataIndex: 'payable_amount',
      key: 'payable_amount',
      width: 130,
      align: 'right',
      render: (val: string) =>
        val != null ? Number(val).toLocaleString('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }) : '-',
    },
    {
      title: '說明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '到期日',
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
    },
    {
      title: '付款狀態',
      dataIndex: 'payment_status',
      key: 'payment_status',
      width: 100,
      render: (val: ERPPayableStatus) => (
        <Tag color={PAYABLE_STATUS_COLORS[val]}>
          {ERP_PAYABLE_STATUS_LABELS[val] ?? val}
        </Tag>
      ),
    },
    {
      title: '付款日期',
      dataIndex: 'paid_date',
      key: 'paid_date',
      width: 120,
      render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
    },
    {
      title: '已付金額',
      dataIndex: 'paid_amount',
      key: 'paid_amount',
      width: 120,
      align: 'right',
      render: (val: string | null) =>
        val != null ? Number(val).toLocaleString('zh-TW') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: ERPVendorPayable) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="確定要刪除此應付紀錄？"
            onConfirm={() => handleDelete(record.id)}
            okText="確定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const dataSource = Array.isArray(payables) ? payables : [];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增應付
        </Button>
      </div>

      <Table<ERPVendorPayable>
        columns={columns}
        dataSource={dataSource}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (total) => `共 ${total} 筆` }}
      />

      <Modal
        title={editingRecord ? '編輯廠商應付' : '新增廠商應付'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCancel}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnHidden
        width={600}
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="vendor_name"
            label="廠商名稱"
            rules={[{ required: true, message: '請輸入廠商名稱' }]}
          >
            <Input placeholder="請輸入廠商名稱" />
          </Form.Item>

          <Form.Item
            name="payable_amount"
            label="應付金額"
            rules={[{ required: true, message: '請輸入應付金額' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number((value ?? '').replace(/,/g, '')) as 0}
            />
          </Form.Item>

          <Form.Item name="description" label="說明">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="due_date" label="到期日">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="invoice_number" label="發票號碼">
            <Input placeholder="對應發票號碼（選填）" />
          </Form.Item>

          <Form.Item name="billing_id" label="關聯請款期別">
            <Select allowClear placeholder="選擇期別 (選填)"
              options={billingOptions}
            />
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default VendorPayablesTab;
