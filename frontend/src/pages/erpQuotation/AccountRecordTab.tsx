/**
 * 統一帳款紀錄 Tab — 應收/應付共用
 *
 * 統一欄位: 期別、對象、請款日期、請款金額、發票號碼、
 *          發票金額、收付款狀態、收付款日期、收付款金額
 *
 * @version 1.0.0
 * @date 2026-03-30
 */
import React, { useState, useCallback } from 'react';
import {
  Table, Button, Space, Tag, Modal, Form, Input, InputNumber,
  DatePicker, Select, Popconfirm, App, Card, Statistic, Row, Col,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';

/** 帳款方向 */
type AccountDirection = 'receivable' | 'payable';

interface AccountRecord {
  id: number;
  period?: string;
  counterparty?: string;       // 對象 (委託單位 or 廠商)
  request_date?: string;       // 請款日期
  request_amount?: number;     // 請款金額
  invoice_number?: string;     // 發票號碼
  invoice_date?: string;       // 發票日期
  invoice_amount?: number;     // 發票金額
  payment_status: string;      // 收付款狀態
  payment_date?: string;       // 收付款日期
  payment_amount?: number;     // 收付款金額
  notes?: string;
}

interface AccountRecordTabProps {
  erpQuotationId: number;
  direction: AccountDirection;
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', unpaid: 'default',
  partial: 'orange',
  paid: 'green',
  overdue: 'red',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '待收款', unpaid: '未付款',
  partial: '部分收付',
  paid: '已收付',
  overdue: '逾期',
};

// 資料轉換: billing → 統一格式
const billingToRecord = (b: Record<string, unknown>): AccountRecord => ({
  id: b.id as number,
  period: b.billing_period as string,
  counterparty: '委託單位',
  request_date: b.billing_date as string,
  request_amount: Number(b.billing_amount || 0),
  invoice_number: undefined,
  payment_status: (b.payment_status as string) || 'pending',
  payment_date: b.payment_date as string,
  payment_amount: b.payment_amount ? Number(b.payment_amount) : undefined,
  notes: b.notes as string,
});

// 資料轉換: vendor_payable → 統一格式
const payableToRecord = (p: Record<string, unknown>): AccountRecord => ({
  id: p.id as number,
  period: undefined,
  counterparty: p.vendor_name as string,
  request_date: p.due_date as string,
  request_amount: Number(p.payable_amount || 0),
  invoice_number: p.invoice_number as string,
  payment_status: (p.payment_status as string) || 'unpaid',
  payment_date: p.paid_date as string,
  payment_amount: p.paid_amount ? Number(p.paid_amount) : undefined,
  notes: p.notes as string,
});

export const AccountRecordTab: React.FC<AccountRecordTabProps> = ({
  erpQuotationId,
  direction,
}) => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const isReceivable = direction === 'receivable';
  const dirLabel = isReceivable ? '應收' : '應付';
  const counterpartyLabel = isReceivable ? '委託單位' : '協力廠商';
  const paymentLabel = isReceivable ? '收款' : '付款';
  const listEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_LIST : ERP_ENDPOINTS.VENDOR_PAYABLES_LIST;
  const createEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_CREATE : ERP_ENDPOINTS.VENDOR_PAYABLES_CREATE;
  const updateEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_UPDATE : ERP_ENDPOINTS.VENDOR_PAYABLES_UPDATE;
  const deleteEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_DELETE : ERP_ENDPOINTS.VENDOR_PAYABLES_DELETE;
  const queryKey = isReceivable ? ['erp-billings', erpQuotationId] : ['erp-vendor-payables', erpQuotationId];

  // 查詢
  const { data: rawData, isLoading } = useQuery({
    queryKey,
    queryFn: () => apiClient.post<{ data: Record<string, unknown>[] }>(listEndpoint, { erp_quotation_id: erpQuotationId }),
  });

  const records: AccountRecord[] = (rawData?.data ?? (rawData as unknown as Record<string, unknown>[]) ?? []).map(
    isReceivable ? billingToRecord : payableToRecord
  );

  // 統計
  const totalRequest = records.reduce((s, r) => s + (r.request_amount || 0), 0);
  const totalPaid = records.reduce((s, r) => s + (r.payment_amount || 0), 0);
  const outstanding = totalRequest - totalPaid;

  // CRUD
  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiClient.post(createEndpoint, data),
    onSuccess: () => { message.success('新增成功'); invalidate(); close(); },
    onError: () => message.error('新增失敗'),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiClient.post(updateEndpoint, data),
    onSuccess: () => { message.success('更新成功'); invalidate(); close(); },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.post(deleteEndpoint, { id }),
    onSuccess: () => { message.success('已刪除'); invalidate(); },
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: ['erp-quotations'] });
    // Also invalidate the specific quotation detail (cost structure depends on billing/payable data)
    queryClient.invalidateQueries({ queryKey: ['erp-quotations', 'detail'] });
  };

  const close = () => { setModalOpen(false); setEditingId(null); form.resetFields(); };

  const handleAdd = () => { setEditingId(null); form.resetFields(); setModalOpen(true); };

  const handleEdit = (record: AccountRecord) => {
    setEditingId(record.id);
    if (isReceivable) {
      form.setFieldsValue({
        billing_period: record.period,
        billing_date: record.request_date ? dayjs(record.request_date) : null,
        billing_amount: record.request_amount,
        payment_status: record.payment_status,
        payment_date: record.payment_date ? dayjs(record.payment_date) : null,
        payment_amount: record.payment_amount,
        notes: record.notes,
      });
    } else {
      form.setFieldsValue({
        vendor_name: record.counterparty,
        payable_amount: record.request_amount,
        invoice_number: record.invoice_number,
        due_date: record.request_date ? dayjs(record.request_date) : null,
        payment_status: record.payment_status,
        paid_date: record.payment_date ? dayjs(record.payment_date) : null,
        paid_amount: record.payment_amount,
        notes: record.notes,
      });
    }
    setModalOpen(true);
  };

  const handleSubmit = useCallback(async () => {
    const values = await form.validateFields();

    if (isReceivable) {
      const payload = {
        erp_quotation_id: erpQuotationId,
        billing_period: values.billing_period,
        billing_date: values.billing_date?.format('YYYY-MM-DD'),
        billing_amount: values.billing_amount,
        payment_status: values.payment_status || 'pending',
        payment_date: values.payment_date?.format('YYYY-MM-DD'),
        payment_amount: values.payment_amount,
        notes: values.notes,
      };
      if (editingId) updateMutation.mutate({ id: editingId, data: payload });
      else createMutation.mutate(payload);
    } else {
      const payload = {
        erp_quotation_id: erpQuotationId,
        vendor_name: values.vendor_name,
        payable_amount: values.payable_amount,
        invoice_number: values.invoice_number,
        due_date: values.due_date?.format('YYYY-MM-DD'),
        payment_status: values.payment_status || 'unpaid',
        paid_date: values.paid_date?.format('YYYY-MM-DD'),
        paid_amount: values.paid_amount,
        notes: values.notes,
      };
      if (editingId) updateMutation.mutate({ id: editingId, data: payload });
      else createMutation.mutate(payload);
    }
  }, [form, editingId, erpQuotationId, isReceivable, createMutation, updateMutation]);

  // 統一欄位
  const columns: ColumnsType<AccountRecord> = [
    { title: '期別', dataIndex: 'period', width: 80, render: (v) => v || '-' },
    { title: counterpartyLabel, dataIndex: 'counterparty', width: 140, ellipsis: true },
    { title: '請款日期', dataIndex: 'request_date', width: 110 },
    { title: '請款金額', dataIndex: 'request_amount', width: 110, align: 'right', render: (v: number) => v?.toLocaleString() },
    { title: '發票號碼', dataIndex: 'invoice_number', width: 120, render: (v) => v || '-' },
    { title: `${paymentLabel}狀態`, dataIndex: 'payment_status', width: 90, align: 'center',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{STATUS_LABELS[s] || s}</Tag> },
    { title: `${paymentLabel}日期`, dataIndex: 'payment_date', width: 110 },
    { title: `${paymentLabel}金額`, dataIndex: 'payment_amount', width: 110, align: 'right', render: (v) => v?.toLocaleString() || '-' },
    {
      title: '操作', width: 100, align: 'center',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="確認刪除？" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 統計摘要 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}><Card size="small"><Statistic title={`${dirLabel}總額`} value={totalRequest} precision={0} /></Card></Col>
        <Col span={8}><Card size="small"><Statistic title={`已${paymentLabel}`} value={totalPaid} precision={0} styles={{ content: { color: '#52c41a' } }} /></Card></Col>
        <Col span={8}><Card size="small"><Statistic title="未結餘額" value={outstanding} precision={0} styles={{ content: { color: outstanding > 0 ? '#ff4d4f' : '#52c41a' } }} /></Card></Col>
      </Row>

      <div style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增{dirLabel}</Button>
      </div>

      <Table<AccountRecord>
        columns={columns}
        dataSource={records}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
      />

      {/* 統一表單 */}
      <Modal title={editingId ? `編輯${dirLabel}` : `新增${dirLabel}`} open={modalOpen}
        onOk={handleSubmit} onCancel={close} width={560}
        confirmLoading={createMutation.isPending || updateMutation.isPending}>
        <Form form={form} layout="vertical" size="small">
          {isReceivable ? (
            <>
              <Form.Item name="billing_period" label="期別"><Input placeholder="如 第1期" /></Form.Item>
              <Form.Item name="billing_date" label="請款日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
              <Form.Item name="billing_amount" label="請款金額" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item name="vendor_name" label="協力廠商" rules={[{ required: true }]}><Input placeholder="廠商名稱" /></Form.Item>
              <Form.Item name="payable_amount" label="應付金額" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
              </Form.Item>
              <Form.Item name="invoice_number" label="廠商發票號碼"><Input placeholder="選填" /></Form.Item>
              <Form.Item name="due_date" label="應付日期"><DatePicker style={{ width: '100%' }} /></Form.Item>
            </>
          )}
          <Form.Item name="payment_status" label={`${paymentLabel}狀態`} initialValue={isReceivable ? 'pending' : 'unpaid'}>
            <Select options={isReceivable
              ? [{ value: 'pending', label: '待收款' }, { value: 'partial', label: '部分收款' }, { value: 'paid', label: '已收款' }, { value: 'overdue', label: '逾期' }]
              : [{ value: 'unpaid', label: '未付款' }, { value: 'partial', label: '部分付款' }, { value: 'paid', label: '已付款' }]
            } />
          </Form.Item>
          <Form.Item name={isReceivable ? 'payment_date' : 'paid_date'} label={`${paymentLabel}日期`}><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name={isReceivable ? 'payment_amount' : 'paid_amount'} label={`${paymentLabel}金額`}>
            <InputNumber style={{ width: '100%' }} min={0} formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
          <Form.Item name="notes" label="備註"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AccountRecordTab;
