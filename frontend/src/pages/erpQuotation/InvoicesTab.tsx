/**
 * ERP 發票管理 Tab
 *
 * 報價單詳情頁的發票子表，支援 CRUD 操作。
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
  ERPInvoice,
  ERPInvoiceCreate,
  ERPInvoiceUpdate,
  ERPInvoiceType,
  ERPInvoiceStatus,
} from '../../types/erp';
import {
  ERP_INVOICE_TYPE_LABELS,
} from '../../types/erp';
import {
  useERPInvoices,
  useCreateERPInvoice,
  useUpdateERPInvoice,
  useDeleteERPInvoice,
} from '../../hooks/business/useERPQuotations';

// =============================================================================
// 常數
// =============================================================================

const INVOICE_STATUS_LABELS: Record<ERPInvoiceStatus, string> = {
  issued: '已開立',
  voided: '已作廢',
  cancelled: '已取消',
};

const INVOICE_STATUS_COLORS: Record<ERPInvoiceStatus, string> = {
  issued: 'green',
  voided: 'red',
  cancelled: 'default',
};

const INVOICE_TYPE_COLORS: Record<ERPInvoiceType, string> = {
  sales: 'blue',
  purchase: 'orange',
};

// =============================================================================
// Props
// =============================================================================

export interface InvoicesTabProps {
  erpQuotationId: number;
}

// =============================================================================
// 元件
// =============================================================================

const InvoicesTab: React.FC<InvoicesTabProps> = ({ erpQuotationId }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ERPInvoice | null>(null);

  // Data
  const { data: invoices, isLoading } = useERPInvoices(erpQuotationId);
  const createMutation = useCreateERPInvoice();
  const updateMutation = useUpdateERPInvoice(erpQuotationId);
  const deleteMutation = useDeleteERPInvoice(erpQuotationId);

  // Handlers
  const handleAdd = useCallback(() => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  }, [form]);

  const handleEdit = useCallback((record: ERPInvoice) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      invoice_date: record.invoice_date ? dayjs(record.invoice_date) : null,
      amount: record.amount ? Number(record.amount) : null,
      tax_amount: record.tax_amount ? Number(record.tax_amount) : null,
    });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('發票已刪除');
    } catch {
      message.error('刪除失敗');
    }
  }, [deleteMutation, message]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        invoice_date: values.invoice_date?.format('YYYY-MM-DD'),
        amount: String(values.amount),
        tax_amount: values.tax_amount != null ? String(values.tax_amount) : undefined,
      };

      if (editingRecord) {
        const updateData: ERPInvoiceUpdate = { ...payload };
        await updateMutation.mutateAsync({ id: editingRecord.id, data: updateData });
        message.success('發票已更新');
      } else {
        const createData: ERPInvoiceCreate = {
          ...payload,
          erp_quotation_id: erpQuotationId,
        };
        await createMutation.mutateAsync(createData);
        message.success('發票已新增');
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
  const columns: ColumnsType<ERPInvoice> = [
    {
      title: '發票號碼',
      dataIndex: 'invoice_number',
      key: 'invoice_number',
      width: 140,
    },
    {
      title: '發票日期',
      dataIndex: 'invoice_date',
      key: 'invoice_date',
      width: 120,
      render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right',
      render: (val: string) =>
        val != null ? Number(val).toLocaleString('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }) : '-',
    },
    {
      title: '稅額',
      dataIndex: 'tax_amount',
      key: 'tax_amount',
      width: 100,
      align: 'right',
      render: (val: string) =>
        val != null && val !== '0' ? Number(val).toLocaleString('zh-TW') : '-',
    },
    {
      title: '類型',
      dataIndex: 'invoice_type',
      key: 'invoice_type',
      width: 80,
      render: (val: ERPInvoiceType) => (
        <Tag color={INVOICE_TYPE_COLORS[val]}>
          {ERP_INVOICE_TYPE_LABELS[val] ?? val}
        </Tag>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (val: ERPInvoiceStatus) => (
        <Tag color={INVOICE_STATUS_COLORS[val]}>
          {INVOICE_STATUS_LABELS[val] ?? val}
        </Tag>
      ),
    },
    {
      title: '說明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: ERPInvoice) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="確定要刪除此發票？"
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

  const dataSource = Array.isArray(invoices) ? invoices : [];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增發票
        </Button>
      </div>

      <Table<ERPInvoice>
        columns={columns}
        dataSource={dataSource}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (total) => `共 ${total} 筆` }}
      />

      <Modal
        title={editingRecord ? '編輯發票' : '新增發票'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCancel}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnClose
        width={600}
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="invoice_number"
            label="發票號碼"
            rules={[{ required: true, message: '請輸入發票號碼' }]}
          >
            <Input placeholder="例：AB-12345678" />
          </Form.Item>

          <Form.Item
            name="invoice_date"
            label="發票日期"
            rules={[{ required: true, message: '請選擇發票日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="amount"
            label="金額"
            rules={[{ required: true, message: '請輸入金額' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number((value ?? '').replace(/,/g, '')) as 0}
            />
          </Form.Item>

          <Form.Item name="tax_amount" label="稅額">
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number((value ?? '').replace(/,/g, '')) as 0}
            />
          </Form.Item>

          <Form.Item name="invoice_type" label="發票類型" initialValue="sales">
            <Select>
              {(Object.entries(ERP_INVOICE_TYPE_LABELS) as [ERPInvoiceType, string][]).map(
                ([key, label]) => (
                  <Select.Option key={key} value={key}>
                    {label}
                  </Select.Option>
                ),
              )}
            </Select>
          </Form.Item>

          <Form.Item name="description" label="說明">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default InvoicesTab;
