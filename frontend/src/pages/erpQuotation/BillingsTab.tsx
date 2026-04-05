/**
 * ERP 請款管理 Tab
 *
 * 報價單詳情頁的請款子表，支援 CRUD 操作。
 * 狀態/查詢/handlers 已提取至 useBillingHandlers hook。
 *
 * ACCEPTED EXCEPTION: Modal CRUD pattern retained (3 modals: billing/invoice/payment).
 * Reason: Tab-inline editing within ERP Quotation detail page.
 * - Billing modal (5 fields): core CRUD for billing periods
 * - Invoice modal (3 fields): quick invoice creation from billing
 * - Payment modal (3 fields): payment confirmation workflow
 * All tightly coupled to erpQuotationId context with expandable row detail.
 * Quality: Handlers extracted to useBillingHandlers, form validation, loading states,
 * Popconfirm delete, destroyOnHidden for form cleanup.
 *
 * @version 1.1.1
 */

import React from 'react';
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
  Typography,
  Empty,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FileTextOutlined, DollarOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import type { ERPBilling, ERPBillingStatus } from '../../types/erp';
import { ERP_BILLING_STATUS_LABELS } from '../../types/erp';

import { useBillingHandlers } from './useBillingHandlers';

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
  const {
    form,
    invoiceForm,
    paymentForm,
    modalOpen,
    editingRecord,
    invoiceModalOpen,
    paymentModalOpen,
    billings,
    billingsWithDetails,
    isLoading,
    createPending,
    updatePending,
    createInvoicePending,
    handleAdd,
    handleEdit,
    handleDelete,
    handleSubmit,
    handleCancel,
    handleOpenInvoiceModal,
    handleCancelInvoiceModal,
    handleConfirmPayment,
    handleCancelPaymentModal,
    handlePaymentSubmit,
    handleCreateInvoice,
  } = useBillingHandlers(erpQuotationId);

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
      width: 240,
      render: (_: unknown, record: ERPBilling) => (
        <Space size="small">
          {record.payment_status !== 'paid' && (
            <Button
              type="link"
              size="small"
              icon={<DollarOutlined />}
              style={{ color: '#52c41a' }}
              onClick={() => handleConfirmPayment(record.id, Number(record.billing_amount))}
            >
              收款
            </Button>
          )}
          {!record.invoice_id && (
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => handleOpenInvoiceModal(record.id)}
            >
              開立發票
            </Button>
          )}
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
        confirmLoading={createPending || updatePending}
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

      <Modal
        title="開立發票"
        open={invoiceModalOpen}
        onOk={handleCreateInvoice}
        onCancel={handleCancelInvoiceModal}
        confirmLoading={createInvoicePending}
        destroyOnHidden
        width={480}
      >
        <Form form={invoiceForm} layout="vertical" preserve={false}>
          <Form.Item
            name="invoice_number"
            label="發票號碼"
            rules={[{ required: true, message: '請輸入發票號碼' }]}
          >
            <Input placeholder="例：AB-12345678" maxLength={50} />
          </Form.Item>
          <Form.Item name="invoice_date" label="開立日期">
            <DatePicker style={{ width: '100%' }} placeholder="預設為今天" />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="確認收款" open={paymentModalOpen} onOk={handlePaymentSubmit}
        onCancel={handleCancelPaymentModal}
        confirmLoading={updatePending} destroyOnHidden width={400}>
        <Form form={paymentForm} layout="vertical" size="small" preserve={false}>
          <Form.Item name="payment_amount" label="收款金額" rules={[{ required: true, message: '請輸入收款金額' }]}>
            <InputNumber style={{ width: '100%' }} min={0} precision={0}
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number((value ?? '').replace(/,/g, '')) as 0} />
          </Form.Item>
          <Form.Item name="payment_date" label="收款日期" rules={[{ required: true, message: '請選擇收款日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="payment_status" label="狀態">
            <Select options={[{ value: 'paid', label: '已收款' }, { value: 'partial', label: '部分收款' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default BillingsTab;
