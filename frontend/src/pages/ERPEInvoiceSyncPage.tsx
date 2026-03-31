/**
 * 電子發票同步管理頁面
 *
 * 功能：觸發同步 + 待核銷清單 + 收據上傳 + 同步歷史
 */
import React, { useState } from 'react';
import {
  Card, Table, Button, Tag, Typography, Statistic, Row, Col,
  Tabs, Modal, Form, Input, Select, Upload, App, Alert,
} from 'antd';
import {
  SyncOutlined, UploadOutlined, HistoryOutlined, FileImageOutlined, InboxOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  useSyncEInvoice, useEInvoicePendingList, useUploadReceipt,
  useEInvoiceSyncLogs, useAuthGuard,
} from '../hooks';
import type {
  ExpenseInvoice, EInvoiceSyncLog, PendingReceiptQuery,
} from '../types/erp';
import { EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS, EXPENSE_CATEGORY_OPTIONS } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title } = Typography;

const ERPEInvoiceSyncPage: React.FC = () => {
  const { message } = App.useApp();
  const { hasPermission } = useAuthGuard();
  const isAdmin = hasPermission('admin:access');

  // 待核銷清單
  const [pendingParams, setPendingParams] = useState<PendingReceiptQuery>({ skip: 0, limit: 20 });
  const { data: pendingData, isLoading: pendingLoading, isError: pendingError } = useEInvoicePendingList(pendingParams);
  // 同步歷史
  const { data: logsData, isLoading: logsLoading } = useEInvoiceSyncLogs();
  // Mutations
  const syncMutation = useSyncEInvoice();
  const uploadMutation = useUploadReceipt();

  // 收據上傳 Modal
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadForm] = Form.useForm();
  const [selectedInvoice, setSelectedInvoice] = useState<ExpenseInvoice | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync(undefined);
      const data = result?.data;
      message.success(
        `同步完成: 取得 ${data?.total_fetched ?? 0} 筆，新增 ${data?.new_imported ?? 0} 筆`,
      );
    } catch {
      message.error('同步失敗，請確認 API 設定');
    }
  };

  const handleUploadReceipt = async () => {
    if (!selectedInvoice || !uploadFile) {
      message.warning('請選擇收據圖片');
      return;
    }
    try {
      const values = await uploadForm.validateFields();
      await uploadMutation.mutateAsync({
        invoiceId: selectedInvoice.id,
        file: uploadFile,
        caseCode: values.case_code,
        category: values.category,
      });
      message.success('收據上傳成功，發票已轉為待審核');
      setUploadOpen(false);
      setSelectedInvoice(null);
      setUploadFile(null);
      uploadForm.resetFields();
    } catch {
      message.error('上傳失敗');
    }
  };

  const openUpload = (invoice: ExpenseInvoice) => {
    setSelectedInvoice(invoice);
    uploadForm.setFieldsValue({
      case_code: invoice.case_code,
      category: invoice.category,
    });
    setUploadOpen(true);
  };

  // 待核銷表格欄位
  const pendingColumns: ColumnsType<ExpenseInvoice> = [
    { title: '發票號碼', dataIndex: 'inv_num', key: 'inv_num', width: 140 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 120,
      align: 'right', render: (v: number) => v?.toLocaleString() ?? '-',
    },
    { title: '賣方統編', dataIndex: 'seller_ban', key: 'seller_ban', width: 120 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => (
        <Tag color={EXPENSE_STATUS_COLORS[s as keyof typeof EXPENSE_STATUS_COLORS] ?? 'default'}>
          {EXPENSE_STATUS_LABELS[s as keyof typeof EXPENSE_STATUS_LABELS] ?? s}
        </Tag>
      ),
    },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_: unknown, record: ExpenseInvoice) => (
        <Button
          type="primary" size="small" ghost
          icon={<UploadOutlined />}
          onClick={(e) => { e.stopPropagation(); openUpload(record); }}
        >
          上傳收據
        </Button>
      ),
    },
  ];

  // 同步歷史欄位
  const logColumns: ColumnsType<EInvoiceSyncLog> = [
    {
      title: '同步時間', dataIndex: 'started_at', key: 'started_at', width: 180,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    { title: '查詢起', dataIndex: 'query_start', key: 'query_start', width: 110 },
    { title: '查詢迄', dataIndex: 'query_end', key: 'query_end', width: 110 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => (
        <Tag color={s === 'success' ? 'green' : s === 'partial' ? 'orange' : s === 'running' ? 'blue' : 'red'}>
          {s === 'success' ? '成功' : s === 'partial' ? '部分成功' : s === 'running' ? '執行中' : '失敗'}
        </Tag>
      ),
    },
    { title: '取得', dataIndex: 'total_fetched', key: 'total_fetched', width: 80, align: 'right' },
    { title: '新增', dataIndex: 'new_imported', key: 'new_imported', width: 80, align: 'right' },
    { title: '重複', dataIndex: 'skipped_duplicate', key: 'skipped_duplicate', width: 80, align: 'right' },
    {
      title: '錯誤訊息', dataIndex: 'error_message', key: 'error_message', ellipsis: true,
      render: (v: string | null) => v ?? '-',
    },
  ];

  const pendingItems = pendingData?.items ?? [];
  const pendingTotal = pendingData?.total ?? 0;
  const logItems = logsData?.items ?? [];
  const logTotal = logsData?.total ?? 0;

  const tabItems = [
    {
      key: 'pending',
      label: <span><FileImageOutlined /> 待核銷清單 ({pendingTotal})</span>,
      children: (
        <Table<ExpenseInvoice>
          columns={pendingColumns}
          dataSource={pendingItems}
          rowKey="id"
          loading={pendingLoading}
          pagination={{
            current: Math.floor((pendingParams.skip ?? 0) / (pendingParams.limit ?? 20)) + 1,
            pageSize: pendingParams.limit ?? 20,
            total: pendingTotal,
            onChange: (page, pageSize) =>
              setPendingParams(p => ({ ...p, skip: (page - 1) * pageSize, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
          }}
          size="middle"
          scroll={{ x: 800 }}
        />
      ),
    },
    {
      key: 'logs',
      label: <span><HistoryOutlined /> 同步歷史 ({logTotal})</span>,
      children: (
        <Table<EInvoiceSyncLog>
          columns={logColumns}
          dataSource={logItems}
          rowKey="id"
          loading={logsLoading}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
          size="middle"
          scroll={{ x: 900 }}
        />
      ),
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>電子發票同步管理</Title></Col>
          <Col>
            {isAdmin && (
              <Button
                type="primary"
                icon={<SyncOutlined spin={syncMutation.isPending} />}
                loading={syncMutation.isPending}
                onClick={handleSync}
              >
                觸發同步
              </Button>
            )}
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}><Statistic title="待核銷發票" value={pendingTotal} /></Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="待核銷金額"
              value={pendingItems.reduce((s, i) => s + (i.amount || 0), 0)}
              precision={0}
            />
          </Col>
          <Col xs={12} sm={6}><Statistic title="同步記錄" value={logTotal} /></Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="最近同步"
              value={logItems[0]?.started_at ? dayjs(logItems[0].started_at).format('MM/DD HH:mm') : '無'}
            />
          </Col>
        </Row>
      </Card>

      {pendingError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <Tabs items={tabItems} />
      </Card>

      {/* 收據上傳 Modal */}
      <Modal
        title={`上傳收據 — ${selectedInvoice?.inv_num ?? ''}`}
        open={uploadOpen}
        onOk={handleUploadReceipt}
        onCancel={() => { setUploadOpen(false); setSelectedInvoice(null); setUploadFile(null); uploadForm.resetFields(); }}
        confirmLoading={uploadMutation.isPending}
        okButtonProps={{ disabled: !uploadFile }}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item label="收據圖片" required>
            <Upload.Dragger
              accept="image/jpeg,image/png,image/webp,image/heic"
              maxCount={1}
              beforeUpload={(file) => {
                if (file.size > 10 * 1024 * 1024) {
                  message.error('檔案過大，上限為 10MB');
                  return Upload.LIST_IGNORE;
                }
                setUploadFile(file);
                return false;
              }}
              onRemove={() => setUploadFile(null)}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">點擊或拖曳收據圖片至此</p>
              <p className="ant-upload-hint">支援 JPEG / PNG / WebP / HEIC，上限 10MB</p>
            </Upload.Dragger>
          </Form.Item>
          <Form.Item name="case_code" label="案號 (選填)">
            <Input placeholder="留空 = 一般營運支出" />
          </Form.Item>
          <Form.Item name="category" label="費用分類">
            <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} allowClear />
          </Form.Item>
        </Form>
      </Modal>
    </ResponsiveContent>
  );
};

export default ERPEInvoiceSyncPage;
