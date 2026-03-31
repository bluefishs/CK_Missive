/**
 * ERP 費用報銷詳情頁面 — 統一 DetailPageLayout 模板
 *
 * Tab: 發票資訊 / 明細項目 / 收據影像
 * 操作：核准/駁回（導航式確認），編輯（導航模式）
 *
 * @version 2.0.0 — DetailPageLayout + 導航模式
 */
import React, { useState } from 'react';
import {
  Descriptions, Tag, Button, Table, Popconfirm, Typography,
  Upload, Image, Spin, App, Form, Input, Select,
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, EditOutlined, SaveOutlined, CloseOutlined,
  UploadOutlined, FileImageOutlined, InfoCircleOutlined, UnorderedListOutlined, CloudSyncOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { useExpenseDetail, useApproveExpense, useRejectExpense, useUpdateExpense, useUploadExpenseReceipt, useAuthGuard, useAutoLinkEinvoice, useAssetsByInvoice } from '../hooks';
import { expensesApi } from '../api/erp';
import type { ExpenseInvoiceItem } from '../types/erp';
import { EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS, EXPENSE_SOURCE_LABELS, EXPENSE_CATEGORY_OPTIONS, CURRENCY_SYMBOLS, APPROVAL_THRESHOLD } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';

import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';

const ERPExpenseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { hasPermission } = useAuthGuard();
  const { message } = App.useApp();
  const canApprove = hasPermission('projects:write');
  const { data, isLoading, isError } = useExpenseDetail(id ? Number(id) : null);
  const approveMutation = useApproveExpense();
  const rejectMutation = useRejectExpense();
  const updateMutation = useUpdateExpense();
  const uploadReceiptMutation = useUploadExpenseReceipt();
  const autoLinkMutation = useAutoLinkEinvoice();
  const { data: linkedAssets } = useAssetsByInvoice(data?.data?.id ?? null);

  const [isEditing, setIsEditing] = useState(false);
  const [editForm] = Form.useForm();

  const invoice = data?.data;

  // 收據影像
  const [receiptBlobUrl, setReceiptBlobUrl] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (!invoice?.receipt_image_path || !invoice?.id) return;
    let revoked = false;
    expensesApi.receiptImage(invoice.id).then((blob) => {
      if (!revoked) setReceiptBlobUrl(URL.createObjectURL(blob));
    }).catch(() => {});
    return () => { revoked = true; if (receiptBlobUrl) URL.revokeObjectURL(receiptBlobUrl); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoice?.id, invoice?.receipt_image_path]);

  React.useEffect(() => {
    if (invoice && !isEditing) {
      editForm.setFieldsValue({ category: invoice.category, notes: invoice.notes });
    }
  }, [invoice, isEditing, editForm]);

  if (isError || (!invoice && !isLoading)) {
    return <DetailPageLayout header={{ title: '找不到此費用發票', backPath: ROUTES.ERP_EXPENSES }} tabs={[]} hasData={false} />;
  }

  const status = (invoice?.status ?? 'pending') as keyof typeof EXPENSE_STATUS_LABELS;
  const canEdit = invoice?.status === 'pending';
  const canAdvance = canApprove && invoice && !['verified', 'rejected'].includes(invoice.status);
  const approveLabel: Record<string, string> = {
    pending: '主管核准', manager_approved: (invoice?.amount ?? 0) > APPROVAL_THRESHOLD ? '財務核准' : '最終核准',
    finance_approved: '最終核准', pending_receipt: '推進',
  };

  const handleApprove = async () => {
    if (!invoice) return;
    try {
      const res = await approveMutation.mutateAsync(invoice.id);
      message.success(res?.message ?? '審核推進成功');
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : '核准失敗');
    }
  };
  const handleReject = async () => {
    if (!invoice) return;
    try { await rejectMutation.mutateAsync({ id: invoice.id }); message.success('已駁回'); } catch { message.error('駁回失敗'); }
  };
  const handleSave = async () => {
    if (!invoice) return;
    try {
      const values = await editForm.validateFields();
      await updateMutation.mutateAsync({ id: invoice.id, data: values });
      message.success('更新成功'); setIsEditing(false);
    } catch { message.error('更新失敗'); }
  };

  const headerConfig = {
    title: `費用報銷 — ${invoice?.inv_num ?? ''}`,
    backPath: ROUTES.ERP_EXPENSES,
    tags: invoice ? [{ text: EXPENSE_STATUS_LABELS[status] ?? status, color: EXPENSE_STATUS_COLORS[status] ?? 'default' }] : [],
    extra: isEditing ? (
      <>
        <Button icon={<CloseOutlined />} onClick={() => setIsEditing(false)}>取消</Button>
        <Button type="primary" icon={<SaveOutlined />} loading={updateMutation.isPending} onClick={handleSave}>儲存</Button>
      </>
    ) : (
      <>
        {invoice?.inv_num && !invoice?.synced_at && (
          <Button
            type="dashed"
            icon={<CloudSyncOutlined />}
            onClick={() => autoLinkMutation.mutate(invoice.id, {
              onSuccess: () => message.success('電子發票關聯成功'),
              onError: () => message.error('電子發票關聯失敗'),
            })}
            loading={autoLinkMutation.isPending}
          >
            關聯電子發票
          </Button>
        )}
        {canEdit && <Button icon={<EditOutlined />} onClick={() => setIsEditing(true)}>編輯</Button>}
        {canAdvance && (
          <>
            <Popconfirm title={`確定${approveLabel[invoice!.status] ?? '核准'}？`} onConfirm={handleApprove}>
              <Button type="primary" icon={<CheckCircleOutlined />} loading={approveMutation.isPending}>
                {approveLabel[invoice!.status] ?? '核准'}
              </Button>
            </Popconfirm>
            <Popconfirm title="確定駁回？" onConfirm={handleReject}>
              <Button danger icon={<CloseCircleOutlined />} loading={rejectMutation.isPending}>駁回</Button>
            </Popconfirm>
          </>
        )}
      </>
    ),
  };

  const itemColumns: ColumnsType<ExpenseInvoiceItem> = [
    { title: '品名', dataIndex: 'item_name', key: 'item_name' },
    { title: '數量', dataIndex: 'qty', key: 'qty', width: 80, align: 'right' },
    { title: '單價', dataIndex: 'unit_price', key: 'unit_price', width: 120, align: 'right', render: (v: number) => v?.toLocaleString() },
    { title: '小計', dataIndex: 'amount', key: 'amount', width: 120, align: 'right', render: (v: number) => v?.toLocaleString() },
  ];

  const tabs = invoice ? [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '發票資訊' },
      isEditing ? (
        <Form form={editForm} layout="vertical" size="small">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item label="發票號碼"><Input value={invoice.inv_num} disabled /></Form.Item>
            <Form.Item label="狀態"><Tag color={EXPENSE_STATUS_COLORS[status]}>{EXPENSE_STATUS_LABELS[status]}</Tag></Form.Item>
            <Form.Item label="開立日期"><Input value={invoice.date} disabled /></Form.Item>
            <Form.Item label="總金額"><Input value={`${invoice.amount?.toLocaleString()} TWD`} disabled /></Form.Item>
            <Form.Item name="category" label="費用分類"><Select options={EXPENSE_CATEGORY_OPTIONS} allowClear /></Form.Item>
            <Form.Item label="案號"><Input value={invoice.case_code ?? '一般營運支出'} disabled /></Form.Item>
            <Form.Item name="notes" label="備註" style={{ gridColumn: 'span 2' }}><Input.TextArea rows={2} /></Form.Item>
          </div>
        </Form>
      ) : (
        <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="發票號碼">{invoice.inv_num}</Descriptions.Item>
          <Descriptions.Item label="狀態"><Tag color={EXPENSE_STATUS_COLORS[status]}>{EXPENSE_STATUS_LABELS[status]}</Tag></Descriptions.Item>
          <Descriptions.Item label="開立日期">{invoice.date}</Descriptions.Item>
          <Descriptions.Item label="總金額">{invoice.amount?.toLocaleString()} TWD</Descriptions.Item>
          <Descriptions.Item label="稅額">{invoice.tax_amount?.toLocaleString() ?? '-'}</Descriptions.Item>
          {invoice.currency && invoice.currency !== 'TWD' && (
            <>
              <Descriptions.Item label="原幣金額">{CURRENCY_SYMBOLS[invoice.currency]}{invoice.original_amount?.toLocaleString()} {invoice.currency}</Descriptions.Item>
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
      )
    ),
    ...(invoice.items && invoice.items.length > 0 ? [
      createTabItem('items', { icon: <UnorderedListOutlined />, text: '明細項目', count: invoice.items.length },
        <Table<ExpenseInvoiceItem> columns={itemColumns} dataSource={invoice.items} rowKey="id" pagination={false} size="small" />
      ),
    ] : []),
    createTabItem('receipt', { icon: <FileImageOutlined />, text: '收據影像' },
      <div>
        {!invoice.receipt_image_path && (
          <Upload accept="image/jpeg,image/png,image/webp" maxCount={1} showUploadList={false}
            beforeUpload={(file) => {
              if (file.size > 10 * 1024 * 1024) { message.error('檔案過大，上限 10MB'); return Upload.LIST_IGNORE; }
              if (!invoice) return false;
              uploadReceiptMutation.mutate({ invoiceId: invoice.id, file }, {
                onSuccess: () => message.success('收據上傳成功'),
                onError: () => message.error('收據上傳失敗'),
              });
              return false;
            }}
          >
            <Button icon={<UploadOutlined />} loading={uploadReceiptMutation.isPending}>上傳收據</Button>
          </Upload>
        )}
        <div style={{ marginTop: 12 }}>
          {invoice.receipt_image_path && receiptBlobUrl ? (
            <Image src={receiptBlobUrl} alt="收據影像" style={{ maxWidth: 400, maxHeight: 500 }} placeholder />
          ) : invoice.receipt_image_path ? (
            <Spin size="small" />
          ) : (
            <Typography.Text type="secondary">尚未上傳收據影像</Typography.Text>
          )}
        </div>
      </div>
    ),
    ...(linkedAssets && linkedAssets.length > 0 ? [
      createTabItem('assets', { icon: <DatabaseOutlined />, text: '關聯資產', count: linkedAssets.length },
        <Table
          dataSource={linkedAssets}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: '資產編號', dataIndex: 'asset_code', width: 120 },
            { title: '名稱', dataIndex: 'name' },
            { title: '類別', dataIndex: 'category', width: 80 },
            { title: '購入金額', dataIndex: 'purchase_amount', width: 120, align: 'right' as const,
              render: (v: number) => Number(v).toLocaleString() },
            { title: '狀態', dataIndex: 'status', width: 80,
              render: (v: string) => <Tag>{v}</Tag> },
          ]}
        />
      ),
    ] : []),
  ] : [];

  return (
    <DetailPageLayout header={headerConfig} tabs={tabs} loading={isLoading} hasData={!!invoice} />
  );
};

export default ERPExpenseDetailPage;
