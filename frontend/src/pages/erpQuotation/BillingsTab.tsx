/**
 * ERP 請款管理 Tab
 *
 * 報價單詳情頁的請款子表，支援 CRUD 操作。
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
  Typography,
  Empty,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FileTextOutlined, DollarOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import type {
  ERPBilling,
  ERPBillingCreate,
  ERPBillingUpdate,
  ERPBillingStatus,
} from '../../types/erp';
import { ERP_BILLING_STATUS_LABELS } from '../../types/erp';
import { useQuery } from '@tanstack/react-query';

// 期別整合型別
interface BillingWithDetails {
  id: number;
  billing_period?: string;
  billing_date?: string;
  billing_amount: number;
  payment_status: string;
  invoices: Array<{ id: number; invoice_number: string; invoice_date?: string; amount: number; status: string }>;
  vendor_payables: Array<{ id: number; vendor_name: string; payable_amount: number; payment_status: string; description?: string }>;
}

import {
  useERPBillings,
  useCreateERPBilling,
  useUpdateERPBilling,
  useDeleteERPBilling,
} from '../../hooks/business/useERPQuotations';

// =============================================================================
// 常數
// =============================================================================

const BILLING_STATUS_COLORS: Record<ERPBillingStatus, string> = {
  pending: 'default',
  partial: 'orange',
  paid: 'green',
  overdue: 'red',
};

// =============================================================================
// Props
// =============================================================================

export interface BillingsTabProps {
  erpQuotationId: number;
}

// =============================================================================
// 元件
// =============================================================================

const BillingsTab: React.FC<BillingsTabProps> = ({ erpQuotationId }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ERPBilling | null>(null);

  // Data
  const { data: billings, isLoading } = useERPBillings(erpQuotationId);

  // 期別整合視圖 — 含關聯發票+廠商應付
  const { data: billingsWithDetails } = useQuery({
    queryKey: ['erp-billings-details', erpQuotationId],
    queryFn: async () => {
      const { apiClient } = await import('../../api/client');
      const resp = await apiClient.post<{ success: boolean; data: BillingWithDetails[] }>(
        '/erp/billings/list-with-details',
        { erp_quotation_id: erpQuotationId },
      );
      return resp.data;
    },
    staleTime: 60_000,
  });
  const createMutation = useCreateERPBilling();
  const updateMutation = useUpdateERPBilling(erpQuotationId);
  const deleteMutation = useDeleteERPBilling(erpQuotationId);

  // Handlers
  const handleAdd = useCallback(() => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  }, [form]);

  const handleEdit = useCallback((record: ERPBilling) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      billing_date: record.billing_date ? dayjs(record.billing_date) : null,
      billing_amount: record.billing_amount ? Number(record.billing_amount) : null,
    });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('請款紀錄已刪除');
    } catch {
      message.error('刪除失敗');
    }
  }, [deleteMutation, message]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        billing_date: values.billing_date?.format('YYYY-MM-DD'),
        billing_amount: String(values.billing_amount),
      };

      if (editingRecord) {
        const updateData: ERPBillingUpdate = { ...payload };
        await updateMutation.mutateAsync({ id: editingRecord.id, data: updateData });
        message.success('請款紀錄已更新');
      } else {
        const createData: ERPBillingCreate = {
          ...payload,
          erp_quotation_id: erpQuotationId,
        };
        await createMutation.mutateAsync(createData);
        message.success('請款紀錄已新增');
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
  const columns: ColumnsType<ERPBilling> = [
    {
      title: '請款期別',
      dataIndex: 'billing_period',
      key: 'billing_period',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '請款日期',
      dataIndex: 'billing_date',
      key: 'billing_date',
      width: 120,
      render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
    },
    {
      title: '請款金額',
      dataIndex: 'billing_amount',
      key: 'billing_amount',
      width: 130,
      align: 'right',
      render: (val: string) =>
        val != null ? Number(val).toLocaleString('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }) : '-',
    },
    {
      title: '收款狀態',
      dataIndex: 'payment_status',
      key: 'payment_status',
      width: 100,
      render: (val: ERPBillingStatus) => (
        <Tag color={BILLING_STATUS_COLORS[val]}>
          {ERP_BILLING_STATUS_LABELS[val] ?? val}
        </Tag>
      ),
    },
    {
      title: '收款日期',
      dataIndex: 'payment_date',
      key: 'payment_date',
      width: 120,
      render: (val: string | null) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
    },
    {
      title: '收款金額',
      dataIndex: 'payment_amount',
      key: 'payment_amount',
      width: 130,
      align: 'right',
      render: (val: string | null) =>
        val != null ? Number(val).toLocaleString('zh-TW') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: ERPBilling) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="確定要刪除此請款紀錄？"
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

  const dataSource = Array.isArray(billings) ? billings : [];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增請款
        </Button>
      </div>

      <Table<ERPBilling>
        columns={columns}
        dataSource={dataSource}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (total) => `共 ${total} 筆` }}
        expandable={{
          expandedRowRender: (record) => {
            const detail = billingsWithDetails?.find(d => d.id === record.id);
            if (!detail) return <Typography.Text type="secondary">載入中...</Typography.Text>;
            const hasInvoices = detail.invoices.length > 0;
            const hasPayables = detail.vendor_payables.length > 0;
            if (!hasInvoices && !hasPayables) {
              return <Empty description="本期尚無關聯發票或廠商應付" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
            }
            return (
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                {hasInvoices && (
                  <div style={{ flex: 1, minWidth: 300 }}>
                    <Typography.Text strong><FileTextOutlined /> 關聯發票 ({detail.invoices.length})</Typography.Text>
                    <Table size="small" dataSource={detail.invoices} rowKey="id" pagination={false} style={{ marginTop: 8 }}
                      columns={[
                        { title: '發票號碼', dataIndex: 'invoice_number', width: 120 },
                        { title: '日期', dataIndex: 'invoice_date', width: 100 },
                        { title: '金額', dataIndex: 'amount', width: 100, render: (v: number) => v?.toLocaleString() },
                        { title: '狀態', dataIndex: 'status', width: 80, render: (s: string) => <Tag color={s === 'issued' ? 'green' : 'red'}>{s === 'issued' ? '已開立' : s}</Tag> },
                      ]}
                    />
                  </div>
                )}
                {hasPayables && (
                  <div style={{ flex: 1, minWidth: 300 }}>
                    <Typography.Text strong><DollarOutlined /> 廠商應付 ({detail.vendor_payables.length})</Typography.Text>
                    <Table size="small" dataSource={detail.vendor_payables} rowKey="id" pagination={false} style={{ marginTop: 8 }}
                      columns={[
                        { title: '廠商', dataIndex: 'vendor_name', width: 140 },
                        { title: '應付金額', dataIndex: 'payable_amount', width: 100, render: (v: number) => v?.toLocaleString() },
                        { title: '狀態', dataIndex: 'payment_status', width: 80, render: (s: string) => <Tag color={s === 'paid' ? 'green' : s === 'partial' ? 'orange' : 'default'}>{s === 'paid' ? '已付' : s === 'partial' ? '部分' : '未付'}</Tag> },
                        { title: '說明', dataIndex: 'description', ellipsis: true },
                      ]}
                    />
                  </div>
                )}
              </div>
            );
          },
          rowExpandable: () => true,
        }}
      />

      <Modal
        title={editingRecord ? '編輯請款' : '新增請款'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCancel}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnHidden
        width={560}
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item name="billing_period" label="請款期別">
            <Input placeholder="例：第 1 期" />
          </Form.Item>

          <Form.Item
            name="billing_date"
            label="請款日期"
            rules={[{ required: true, message: '請選擇請款日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="billing_amount"
            label="請款金額"
            rules={[{ required: true, message: '請輸入請款金額' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number((value ?? '').replace(/,/g, '')) as 0}
            />
          </Form.Item>

          <Form.Item name="payment_status" label="收款狀態" initialValue="pending">
            <Select>
              {(Object.entries(ERP_BILLING_STATUS_LABELS) as [ERPBillingStatus, string][]).map(
                ([key, label]) => (
                  <Select.Option key={key} value={key}>
                    {label}
                  </Select.Option>
                ),
              )}
            </Select>
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default BillingsTab;
