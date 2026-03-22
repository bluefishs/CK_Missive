/**
 * ERP 費用報銷列表頁面
 *
 * 功能：費用發票列表 + 篩選 + 審核/駁回 + QR 掃描建立
 */
import React, { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Input, Select, Typography,
  Statistic, Row, Col, Popconfirm, message, Modal, Form, DatePicker,
  Upload, Progress, Alert,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, CheckCircleOutlined,
  CloseCircleOutlined, QrcodeOutlined, CameraOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import {
  useExpenses, useCreateExpense, useApproveExpense, useRejectExpense,
  useQRScanExpense, useOCRParseExpense, useAuthGuard,
} from '../hooks';
import type {
  ExpenseInvoice, ExpenseInvoiceCreate, ExpenseInvoiceQuery,
  ExpenseInvoiceStatus, ExpenseInvoiceOCRResult,
} from '../types/erp';
import {
  EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS,
  EXPENSE_SOURCE_LABELS, EXPENSE_CATEGORY_OPTIONS,
  CURRENCY_OPTIONS, CURRENCY_SYMBOLS,
  APPROVAL_THRESHOLD,
} from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const ERPExpenseListPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const canApprove = hasPermission('projects:write');
  const [params, setParams] = useState<ExpenseInvoiceQuery>({ skip: 0, limit: 20 });
  const { data, isLoading, refetch } = useExpenses(params);
  const approveMutation = useApproveExpense();
  const rejectMutation = useRejectExpense();
  const createMutation = useCreateExpense();
  const qrScanMutation = useQRScanExpense();
  const ocrMutation = useOCRParseExpense();

  // 建立表單
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm<ExpenseInvoiceCreate>();
  // QR 掃描
  const [qrOpen, setQrOpen] = useState(false);
  const [qrForm] = Form.useForm();
  // OCR 辨識
  const [ocrOpen, setOcrOpen] = useState(false);
  const [ocrResult, setOcrResult] = useState<ExpenseInvoiceOCRResult | null>(null);

  const handleApprove = async (id: number) => {
    try {
      const res = await approveMutation.mutateAsync(id);
      const msg = res?.message ?? '審核推進成功';
      // 預算聯防：包含警告時改用 warning 提示
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
      // 預算超支攔截 → AlertDialog 明確告知
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

  const handleReject = async (id: number) => {
    try {
      await rejectMutation.mutateAsync({ id });
      message.success('已駁回');
    } catch {
      message.error('駁回失敗');
    }
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      const payload: ExpenseInvoiceCreate = {
        ...values,
        date: values.date ? dayjs(values.date).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      };
      await createMutation.mutateAsync(payload);
      message.success('報銷發票已建立');
      setCreateOpen(false);
      createForm.resetFields();
    } catch {
      message.error('建立失敗');
    }
  };

  const handleOCRUpload = (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      message.error('檔案過大，上限為 10MB');
      return;
    }
    ocrMutation.mutate(file, {
      onSuccess: (res) => {
        const result = res.data;
        if (!result) {
          message.error('OCR 回傳空結果');
          return;
        }
        setOcrResult(result);
        // 自動填入建立表單
        if (result.inv_num || result.amount) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const formValues: Record<string, any> = {
            inv_num: result.inv_num ?? '',
            amount: result.amount,
            source: 'ocr',
          };
          if (result.date) formValues.date = dayjs(result.date);
          if (result.buyer_ban) formValues.buyer_ban = result.buyer_ban;
          if (result.seller_ban) formValues.seller_ban = result.seller_ban;
          createForm.setFieldsValue(formValues);
          message.success(`OCR 辨識完成 (信心度: ${Math.round(result.confidence * 100)}%)，請確認後送出`);
          setOcrOpen(false);
          setCreateOpen(true);
        } else {
          message.warning('OCR 未能辨識出發票資訊，請手動輸入');
        }
      },
      onError: () => message.error('OCR 辨識失敗'),
    });
  };

  const handleQRScan = async () => {
    try {
      const values = await qrForm.validateFields();
      await qrScanMutation.mutateAsync(values);
      message.success('QR 掃描建立成功');
      setQrOpen(false);
      qrForm.resetFields();
    } catch {
      message.error('QR 掃描失敗');
    }
  };

  const columns: ColumnsType<ExpenseInvoice> = [
    { title: '發票號碼', dataIndex: 'inv_num', key: 'inv_num', width: 140 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '金額 (TWD)',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right',
      render: (_: number, record: ExpenseInvoice) => {
        const display = record.amount?.toLocaleString() ?? '-';
        if (record.currency && record.currency !== 'TWD') {
          return (
            <span title={`${CURRENCY_SYMBOLS[record.currency]}${record.original_amount?.toLocaleString()} × ${record.exchange_rate}`}>
              {display} <Tag style={{ fontSize: 10, marginLeft: 4 }}>{record.currency}</Tag>
            </span>
          );
        }
        return display;
      },
    },
    { title: '分類', dataIndex: 'category', key: 'category', width: 110 },
    { title: '案號', dataIndex: 'case_code', key: 'case_code', width: 130, render: (v: string | null) => v ?? '一般營運' },
    {
      title: '來源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (v: string) => EXPENSE_SOURCE_LABELS[v as keyof typeof EXPENSE_SOURCE_LABELS] ?? v,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: ExpenseInvoiceStatus) => (
        <Tag color={EXPENSE_STATUS_COLORS[status]}>{EXPENSE_STATUS_LABELS[status]}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: ExpenseInvoice) => {
        const canAdvance = canApprove && !['verified', 'rejected'].includes(record.status);
        const approveLabel: Record<string, string> = {
          pending: '主管核准',
          manager_approved: record.amount > APPROVAL_THRESHOLD ? '財務核准' : '最終核准',
          finance_approved: '最終核准',
          pending_receipt: '推進',
        };
        return (
          <Space>
            <Button type="link" size="small" onClick={(e) => { e.stopPropagation(); navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(record.id))); }}>
              詳情
            </Button>
            {canAdvance && (
              <>
                <Popconfirm title={`確定${approveLabel[record.status] ?? '核准'}？`} onConfirm={() => handleApprove(record.id)} okText="確定" cancelText="取消">
                  <Button type="link" size="small" style={{ color: '#52c41a' }} icon={<CheckCircleOutlined />} onClick={(e) => e.stopPropagation()}>
                    {approveLabel[record.status] ?? '核准'}
                  </Button>
                </Popconfirm>
                <Popconfirm title="確定駁回？" onConfirm={() => handleReject(record.id)} okText="確定" cancelText="取消">
                  <Button type="link" size="small" danger icon={<CloseCircleOutlined />} onClick={(e) => e.stopPropagation()}>駁回</Button>
                </Popconfirm>
              </>
            )}
          </Space>
        );
      },
    },
  ];

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pendingCount = items.filter(i => i.status === 'pending').length;
  const totalAmount = items.reduce((s, i) => s + (i.amount || 0), 0);

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>費用報銷管理</Title></Col>
          <Col>
            <Space>
              <Button icon={<CameraOutlined />} onClick={() => setOcrOpen(true)}>OCR 辨識</Button>
              <Button icon={<QrcodeOutlined />} onClick={() => setQrOpen(true)}>QR 掃描</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增報銷</Button>
            </Space>
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}><Statistic title="發票總數" value={total} /></Col>
          <Col xs={12} sm={6}><Statistic title="待審核" value={pendingCount} styles={{ content: { color: pendingCount > 0 ? '#faad14' : undefined } }} /></Col>
          <Col xs={12} sm={6}><Statistic title="本頁金額合計" value={totalAmount} precision={0} /></Col>
          <Col xs={12} sm={6}><Statistic title="總筆數" value={total} /></Col>
        </Row>
      </Card>

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜尋案號"
            allowClear
            onSearch={(v) => setParams(p => ({ ...p, case_code: v || undefined, skip: 0 }))}
            style={{ width: 200 }}
          />
          <Select
            placeholder="狀態"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => setParams(p => ({ ...p, status: v, skip: 0 }))}
            options={Object.entries(EXPENSE_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Select
            placeholder="分類"
            allowClear
            style={{ width: 140 }}
            onChange={(v) => setParams(p => ({ ...p, category: v, skip: 0 }))}
            options={EXPENSE_CATEGORY_OPTIONS}
          />
          <RangePicker
            onChange={(dates) => {
              setParams(p => ({
                ...p,
                date_from: dates?.[0] ? dayjs(dates[0]).format('YYYY-MM-DD') : undefined,
                date_to: dates?.[1] ? dayjs(dates[1]).format('YYYY-MM-DD') : undefined,
                skip: 0,
              }));
            }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
        </Space>

        <Table<ExpenseInvoice>
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor((params.skip ?? 0) / (params.limit ?? 20)) + 1,
            pageSize: params.limit ?? 20,
            total,
            onChange: (page, pageSize) => setParams(p => ({ ...p, skip: (page - 1) * pageSize, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(record.id))),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1100 }}
        />
      </Card>

      {/* 新增報銷 Modal */}
      <Modal
        title="新增費用報銷"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        confirmLoading={createMutation.isPending}
        width={560}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="inv_num" label="發票號碼" rules={[{ required: true, pattern: /^[A-Z]{2}\d{8}$/, message: '格式: AB12345678' }]}>
            <Input placeholder="AB12345678" maxLength={10} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="date" label="開立日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="amount" label="總金額 (含稅)" rules={[{ required: true }]}>
                <Input type="number" min={0} step={0.01} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="currency" label="幣別" initialValue="TWD">
                <Select options={CURRENCY_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item noStyle shouldUpdate={(prev, cur) => prev.currency !== cur.currency}>
                {({ getFieldValue }) => getFieldValue('currency') && getFieldValue('currency') !== 'TWD' ? (
                  <Form.Item name="original_amount" label="原幣金額" rules={[{ required: true, message: '必填' }]}>
                    <Input type="number" min={0} step={0.01} />
                  </Form.Item>
                ) : null}
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item noStyle shouldUpdate={(prev, cur) => prev.currency !== cur.currency}>
                {({ getFieldValue }) => getFieldValue('currency') && getFieldValue('currency') !== 'TWD' ? (
                  <Form.Item name="exchange_rate" label="匯率" rules={[{ required: true, message: '必填' }]}>
                    <Input type="number" min={0} step={0.000001} placeholder="例: 32.15" />
                  </Form.Item>
                ) : null}
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="case_code" label="案號 (選填)">
                <Input placeholder="留空 = 一般營運支出" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="category" label="費用分類">
                <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} allowClear />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>

      {/* QR 掃描 Modal */}
      <Modal
        title="QR Code 掃描建立"
        open={qrOpen}
        onOk={handleQRScan}
        onCancel={() => { setQrOpen(false); qrForm.resetFields(); }}
        confirmLoading={qrScanMutation.isPending}
      >
        <Form form={qrForm} layout="vertical">
          <Form.Item name="raw_qr" label="QR Code 內容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="貼上電子發票 QR Code 掃描結果" />
          </Form.Item>
          <Form.Item name="case_code" label="案號 (選填)">
            <Input placeholder="留空 = 一般營運支出" />
          </Form.Item>
          <Form.Item name="category" label="費用分類">
            <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} allowClear />
          </Form.Item>
        </Form>
      </Modal>
      {/* OCR 辨識 Modal */}
      <Modal
        title="OCR 發票辨識"
        open={ocrOpen}
        onCancel={() => { setOcrOpen(false); setOcrResult(null); }}
        footer={ocrResult ? (
          <Space>
            <Button onClick={() => { setOcrOpen(false); setOcrResult(null); }}>關閉</Button>
          </Space>
        ) : null}
        width={480}
      >
        {!ocrResult && (
          <Upload.Dragger
            accept="image/jpeg,image/png,image/webp,image/heic"
            maxCount={1}
            showUploadList={false}
            beforeUpload={(file) => {
              handleOCRUpload(file);
              return false;
            }}
          >
            <p className="ant-upload-drag-icon"><CameraOutlined style={{ fontSize: 48, color: '#1890ff' }} /></p>
            <p className="ant-upload-text">點擊或拖曳發票影像至此</p>
            <p className="ant-upload-hint">支援 JPEG/PNG/WebP/HEIC，上限 10MB</p>
          </Upload.Dragger>
        )}
        {ocrMutation.isPending && <Progress percent={99} status="active" style={{ marginTop: 16 }} />}
        {ocrResult && (
          <div style={{ marginTop: 8 }}>
            <Alert
              type={ocrResult.confidence >= 0.6 ? 'success' : 'warning'}
              message={`辨識信心度: ${Math.round(ocrResult.confidence * 100)}%`}
              style={{ marginBottom: 12 }}
            />
            {ocrResult.warnings.length > 0 && (
              <Alert type="info" message={ocrResult.warnings.join('、')} style={{ marginBottom: 12 }} />
            )}
          </div>
        )}
      </Modal>
    </ResponsiveContent>
  );
};

export default ERPExpenseListPage;
