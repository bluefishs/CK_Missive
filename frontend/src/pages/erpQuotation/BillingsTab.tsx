/**
 * ERP 請款管理 Tab
 *
 * 報價單詳情頁的請款子表，支援 CRUD 操作。
 * 狀態/查詢/handlers 已提取至 useBillingHandlers hook。
 *
 * ACCEPTED EXCEPTION: Modal 僅保留 2 個快速動作（invoice / payment），各 3 欄位。
 * 2026-08-02 修訂：原本連「新增/編輯請款」(5 欄位) 也走 Modal，已改為獨立路由頁
 * `ERPBillingFormPage`（沿用公文的填報模式）。04-06 的豁免理由（欄位少＋緊耦合）
 * 對 5 欄位的主要填報不再成立 —— 那是**桌面**成立、行動情境未被納入考慮：
 * 獨立頁換到的是手機完整縱向空間、可分享網址、返回鍵正確、重整不丟資料。
 *
 * 仍為 Modal 的兩個動作是刻意保留：欄位少、緊接某一列的動作而來，
 * 導頁反而讓人失去所在位置。
 *
 * @version 1.2.0
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
import { useNavigate } from 'react-router-dom';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import dayjs from 'dayjs';

import type { ERPBilling, ERPBillingStatus } from '../../types/erp';
import { ERP_BILLING_STATUS_LABELS } from '../../types/erp';
import { ROUTES } from '../../router/types';
import { useResponsive } from '../../hooks';

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
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  const {
    invoiceForm,
    paymentForm,
    invoiceModalOpen,
    paymentModalOpen,
    billings,
    billingsWithDetails,
    isLoading,
    updatePending,
    createInvoicePending,
    handleDelete,
    handleOpenInvoiceModal,
    handleCancelInvoiceModal,
    handleConfirmPayment,
    handleCancelPaymentModal,
    handlePaymentSubmit,
    handleCreateInvoice,
  } = useBillingHandlers(erpQuotationId);

  const goCreate = () =>
    navigate(ROUTES.ERP_BILLING_CREATE.replace(':quotationId', String(erpQuotationId)));
  const goEdit = (billingId: number) =>
    navigate(
      ROUTES.ERP_BILLING_EDIT
        .replace(':quotationId', String(erpQuotationId))
        .replace(':billingId', String(billingId)),
    );

  // Columns
  const allColumns: ColumnsType<ERPBilling> = [
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
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => handleOpenInvoiceModal(record.id)}
          >
            開立發票
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => goEdit(record.id)}
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

  // 手機收斂欄位：只留「期別／金額／狀態／操作」，其餘仍可由展開列查看。
  // 量測依據（2026-08-02 mobile_probe）：報價頁表格在 390px 下橫向外溢 708px，
  // 桌面 1440px 為 0 —— 是窄螢幕獨有的問題，不是表格本身欄位太多。
  const HIDE_ON_MOBILE = ['billing_date', 'payment_date', 'payment_amount'];
  const columns = isMobile
    ? allColumns.filter((c) => !HIDE_ON_MOBILE.includes(String(c.key)))
    : allColumns;

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={goCreate} block={isMobile}>
          新增請款
        </Button>
      </div>

      <EnhancedTable<ERPBilling>
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

      {/* 新增/編輯請款已改為獨立頁 ERPBillingFormPage（見檔首說明） */}

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
