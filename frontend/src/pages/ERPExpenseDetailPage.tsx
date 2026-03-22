/**
 * ERP 費用報銷詳情頁面 (含編輯功能)
 */
import React, { useState } from 'react';
import {
  Card, Descriptions, Tag, Button, Space, Table, Popconfirm, message, Typography, Spin,
  Modal, Form, Input, Select, Upload, Image,
} from 'antd';
import {
  ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, EditOutlined,
  UploadOutlined, FileImageOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useParams, useNavigate } from 'react-router-dom';
import { useExpenseDetail, useApproveExpense, useRejectExpense, useUpdateExpense, useUploadExpenseReceipt, useAuthGuard } from '../hooks';
import type { ExpenseInvoiceItem, ExpenseInvoiceUpdate } from '../types/erp';
import { EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS, EXPENSE_SOURCE_LABELS, EXPENSE_CATEGORY_OPTIONS, CURRENCY_SYMBOLS, APPROVAL_THRESHOLD } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const ERPExpenseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const canApprove = hasPermission('projects:write');
  const { data, isLoading } = useExpenseDetail(id ? Number(id) : null);
  const approveMutation = useApproveExpense();
  const rejectMutation = useRejectExpense();
  const updateMutation = useUpdateExpense();
  const uploadReceiptMutation = useUploadExpenseReceipt();

  const [editOpen, setEditOpen] = useState(false);
  const [editForm] = Form.useForm<ExpenseInvoiceUpdate>();

  const handleUploadReceipt = (file: File) => {
    if (!invoice) return;
    uploadReceiptMutation.mutate(
      { invoiceId: invoice.id, file },
      {
        onSuccess: () => message.success('收據上傳成功'),
        onError: () => message.error('收據上傳失敗'),
      },
    );
  };

  // 收據圖片 URL (相對路徑透過 API base URL 存取)
  const getReceiptUrl = (path: string) => {
    if (path.startsWith('http')) return path;
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
    return `${base}/uploads/${path}`;
  };

  const invoice = data?.data;

  const handleApprove = async () => {
    if (!invoice) return;
    try {
      const res = await approveMutation.mutateAsync(invoice.id);
      const msg = res?.message ?? '審核推進成功';
      if (msg.includes('預算警告') || msg.includes('預算')) {
        Modal.warning({
          title: '預算警告',
          content: msg,
          okText: '我知道了',
          width: 480,
        });
      } else {
        message.success(msg);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '核准失敗';
      if (errMsg.includes('超支') || errMsg.includes('預算') || errMsg.includes('budget')) {
        Modal.error({
          title: '預算超支攔截',
          content: errMsg,
          okText: '我知道了',
          width: 520,
        });
      } else {
        message.error(errMsg);
      }
    }
  };

  const handleReject = async () => {
    if (!invoice) return;
    try {
      await rejectMutation.mutateAsync({ id: invoice.id });
      message.success('已駁回');
    } catch {
      message.error('駁回失敗');
    }
  };

  const openEdit = () => {
    if (!invoice) return;
    editForm.setFieldsValue({
      category: invoice.category,
      notes: invoice.notes,
    });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!invoice) return;
    try {
      const values = await editForm.validateFields();
      await updateMutation.mutateAsync({ id: invoice.id, data: values });
      message.success('更新成功');
      setEditOpen(false);
    } catch {
      message.error('更新失敗');
    }
  };

  const itemColumns: ColumnsType<ExpenseInvoiceItem> = [
    { title: '品名', dataIndex: 'item_name', key: 'item_name' },
    { title: '數量', dataIndex: 'qty', key: 'qty', width: 80, align: 'right' },
    { title: '單價', dataIndex: 'unit_price', key: 'unit_price', width: 120, align: 'right', render: (v: number) => v?.toLocaleString() },
    { title: '小計', dataIndex: 'amount', key: 'amount', width: 120, align: 'right', render: (v: number) => v?.toLocaleString() },
  ];

  if (isLoading) {
    return <ResponsiveContent maxWidth="full" padding="medium"><Spin size="large" /></ResponsiveContent>;
  }

  if (!invoice) {
    return <ResponsiveContent maxWidth="full" padding="medium"><Card><Title level={4}>找不到此費用發票</Title></Card></ResponsiveContent>;
  }

  const status = invoice.status as keyof typeof EXPENSE_STATUS_LABELS;
  const canEdit = invoice.status === 'pending';
  const canAdvance = canApprove && !['verified', 'rejected'].includes(invoice.status);
  const approveLabel: Record<string, string> = {
    pending: '主管核准',
    manager_approved: invoice.amount > APPROVAL_THRESHOLD ? '財務核准' : '最終核准',
    finance_approved: '最終核准',
    pending_receipt: '推進',
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} type="text" />
            <Title level={4} style={{ margin: 0 }}>費用報銷詳情 — {invoice.inv_num}</Title>
          </Space>
        }
        extra={
          <Space>
            {canEdit && (
              <Button icon={<EditOutlined />} onClick={openEdit}>編輯</Button>
            )}
            {canAdvance && (
              <>
                <Popconfirm title={`確定${approveLabel[invoice.status] ?? '核准'}？`} onConfirm={handleApprove}>
                  <Button type="primary" icon={<CheckCircleOutlined />} loading={approveMutation.isPending}>
                    {approveLabel[invoice.status] ?? '核准'}
                  </Button>
                </Popconfirm>
                <Popconfirm title="確定駁回？" onConfirm={handleReject}>
                  <Button danger icon={<CloseCircleOutlined />} loading={rejectMutation.isPending}>駁回</Button>
                </Popconfirm>
              </>
            )}
          </Space>
        }
      >
        <Descriptions bordered column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="發票號碼">{invoice.inv_num}</Descriptions.Item>
          <Descriptions.Item label="狀態">
            <Tag color={EXPENSE_STATUS_COLORS[status]}>{EXPENSE_STATUS_LABELS[status]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="開立日期">{invoice.date}</Descriptions.Item>
          <Descriptions.Item label="總金額 (TWD)">{invoice.amount?.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="稅額">{invoice.tax_amount?.toLocaleString() ?? '-'}</Descriptions.Item>
          {invoice.currency && invoice.currency !== 'TWD' && (
            <>
              <Descriptions.Item label="原幣金額">
                {CURRENCY_SYMBOLS[invoice.currency]}{invoice.original_amount?.toLocaleString()} {invoice.currency}
              </Descriptions.Item>
              <Descriptions.Item label="匯率">{invoice.exchange_rate}</Descriptions.Item>
            </>
          )}
          <Descriptions.Item label="案號">{invoice.case_code ?? '一般營運支出'}</Descriptions.Item>
          <Descriptions.Item label="費用分類">{invoice.category ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="來源">{EXPENSE_SOURCE_LABELS[invoice.source] ?? invoice.source}</Descriptions.Item>
          <Descriptions.Item label="買方統編">{invoice.buyer_ban ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="賣方統編">{invoice.seller_ban ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="備註" span={2}>{invoice.notes ?? '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {invoice.items && invoice.items.length > 0 && (
        <Card title="發票明細" style={{ marginTop: 16 }}>
          <Table<ExpenseInvoiceItem>
            columns={itemColumns}
            dataSource={invoice.items}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* 收據影像 */}
      <Card
        title={<><FileImageOutlined /> 收據影像</>}
        style={{ marginTop: 16 }}
        extra={
          !invoice.receipt_image_path && (
            <Upload
              accept="image/jpeg,image/png,image/webp,image/heic"
              maxCount={1}
              showUploadList={false}
              beforeUpload={(file) => {
                if (file.size > 10 * 1024 * 1024) {
                  message.error('檔案過大，上限為 10MB');
                  return Upload.LIST_IGNORE;
                }
                handleUploadReceipt(file);
                return false;
              }}
            >
              <Button
                icon={<UploadOutlined />}
                loading={uploadReceiptMutation.isPending}
              >
                上傳收據
              </Button>
            </Upload>
          )
        }
      >
        {invoice.receipt_image_path ? (
          <Image
            src={getReceiptUrl(invoice.receipt_image_path)}
            alt="收據影像"
            style={{ maxWidth: 400, maxHeight: 500 }}
            placeholder
          />
        ) : (
          <Typography.Text type="secondary">尚未上傳收據影像</Typography.Text>
        )}
      </Card>

      {/* 編輯 Modal */}
      <Modal
        title={`編輯報銷 — ${invoice.inv_num}`}
        open={editOpen}
        onOk={handleEdit}
        onCancel={() => { setEditOpen(false); editForm.resetFields(); }}
        confirmLoading={updateMutation.isPending}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="category" label="費用分類">
            <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} allowClear />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </ResponsiveContent>
  );
};

export default ERPExpenseDetailPage;
