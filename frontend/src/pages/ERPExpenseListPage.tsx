/**
 * ERP 費用報銷列表頁面
 *
 * 功能：費用發票列表 + 篩選 + 審核/駁回 + QR 掃描建立
 */
import React, { useState, useMemo } from 'react';
import {
  Card, Table, Button, Space, Tag, Input, Select, Typography,
  Statistic, Row, Col, Popconfirm, Modal, Form, DatePicker,
  AutoComplete, App, Alert,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, CheckCircleOutlined,
  CloseCircleOutlined, QrcodeOutlined, CameraOutlined,
  CloudDownloadOutlined, SearchOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  useExpenses, useApproveExpense, useRejectExpense,
  useAuthGuard, useEInvoicePendingList,
} from '../hooks';
import { useProjectsDropdown } from '../hooks';
import type { ExpenseInvoice, ExpenseInvoiceCreate, ExpenseInvoiceQuery, ExpenseInvoiceStatus } from '../types/erp';
import {
  EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS,
  EXPENSE_SOURCE_LABELS, EXPENSE_CATEGORY_OPTIONS,
  CURRENCY_SYMBOLS, APPROVAL_THRESHOLD,
} from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { ExpenseCreateModal, QRScanModal, OCRModal, MofInvoiceModal } from './erpExpense';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const ERPExpenseListPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { hasPermission } = useAuthGuard();
  const canApprove = hasPermission('projects:write');
  const initialCaseCode = searchParams.get('case_code') || undefined;
  const [params, setParams] = useState<ExpenseInvoiceQuery>({ skip: 0, limit: 20, case_code: initialCaseCode });
  const { projects: projectOptions } = useProjectsDropdown();
  const { data, isLoading, isError, refetch } = useExpenses(params);
  const approveMutation = useApproveExpense();
  const rejectMutation = useRejectExpense();

  // Modal 狀態
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm<ExpenseInvoiceCreate>();
  const [qrOpen, setQrOpen] = useState(false);
  const [ocrOpen, setOcrOpen] = useState(false);
  const [mofOpen, setMofOpen] = useState(false);

  // 衍生資料
  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const pendingCount = items.filter(i => i.status === 'pending').length;
  const totalAmount = items.reduce((s, i) => s + (i.amount || 0), 0);

  // MOF 待核銷數量 badge
  const { data: mofPendingData } = useEInvoicePendingList({ skip: 0, limit: 1 });

  // 主列表 AutoComplete
  const [listSearch, setListSearch] = useState('');
  const listAutoCompleteOptions = useMemo(() => {
    if (!listSearch.trim()) return [];
    const kw = listSearch.trim().toLowerCase();
    return items
      .filter(i => i.inv_num?.toLowerCase().includes(kw))
      .slice(0, 8)
      .map(i => ({ value: i.inv_num, label: `${i.inv_num} — ${i.date} — NT$${i.amount?.toLocaleString()}` }));
  }, [items, listSearch]);

  const handleApprove = async (id: number) => {
    try {
      const res = await approveMutation.mutateAsync(id);
      const msg = res?.message ?? '審核推進成功';
      if (msg.includes('預算警告') || msg.includes('預算')) {
        Modal.warning({ title: '預算警告', content: msg, okText: '我知道了', width: 480 });
      } else {
        message.success(msg);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '核准失敗';
      if (errMsg.includes('超支') || errMsg.includes('預算') || errMsg.includes('budget')) {
        Modal.error({ title: '預算超支攔截', content: errMsg, okText: '我知道了', width: 520 });
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

  const columns: ColumnsType<ExpenseInvoice> = [
    { title: '發票號碼', dataIndex: 'inv_num', key: 'inv_num', width: 140 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '金額 (TWD)', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
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
      title: '來源', dataIndex: 'source', key: 'source', width: 100,
      render: (v: string) => EXPENSE_SOURCE_LABELS[v as keyof typeof EXPENSE_SOURCE_LABELS] ?? v,
    },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (status: ExpenseInvoiceStatus) => <Tag color={EXPENSE_STATUS_COLORS[status]}>{EXPENSE_STATUS_LABELS[status]}</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 200,
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

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>財務記錄管理</Title></Col>
          <Col>
            <Space wrap>
              <Button icon={<CloudDownloadOutlined />} onClick={() => setMofOpen(true)}>
                財政部發票 {(mofPendingData?.total ?? 0) > 0 && <Tag color="blue" style={{ marginLeft: 4 }}>{mofPendingData?.total}</Tag>}
              </Button>
              <Button icon={<CameraOutlined />} onClick={() => setOcrOpen(true)}>OCR 辨識</Button>
              <Button icon={<QrcodeOutlined />} onClick={() => setQrOpen(true)}>QR 掃描</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(ROUTES.ERP_EXPENSE_CREATE)}>新增報銷</Button>
              <Button icon={<PlusOutlined />} onClick={() => navigate(ROUTES.ERP_LEDGER_CREATE)}>手動記帳</Button>
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

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <AutoComplete
            options={listAutoCompleteOptions}
            onSearch={setListSearch}
            onSelect={(val) => {
              const found = items.find(i => i.inv_num === val);
              if (found) navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(found.id)));
            }}
            style={{ width: 220 }}
          >
            <Input prefix={<SearchOutlined />} placeholder="搜尋發票號碼..." allowClear />
          </AutoComplete>
          <Select
            placeholder="篩選專案" allowClear showSearch optionFilterProp="label"
            value={params.case_code}
            onChange={(v) => setParams(p => ({ ...p, case_code: v || undefined, skip: 0 }))}
            style={{ width: 220 }}
            options={projectOptions?.map(p => ({ value: p.project_code, label: `${p.project_code} ${p.project_name}` })) ?? []}
          />
          <Select
            placeholder="狀態" allowClear style={{ width: 120 }}
            onChange={(v) => setParams(p => ({ ...p, status: v, skip: 0 }))}
            options={Object.entries(EXPENSE_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Select
            placeholder="分類" allowClear style={{ width: 140 }}
            onChange={(v) => setParams(p => ({ ...p, category: v, skip: 0 }))}
            options={EXPENSE_CATEGORY_OPTIONS}
          />
          <RangePicker
            onChange={(dates) => {
              setParams(p => ({
                ...p,
                date_from: dates?.[0] ? dates[0].format('YYYY-MM-DD') : undefined,
                date_to: dates?.[1] ? dates[1].format('YYYY-MM-DD') : undefined,
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

      <ExpenseCreateModal open={createOpen} onClose={() => setCreateOpen(false)} form={createForm} />
      <QRScanModal open={qrOpen} onClose={() => setQrOpen(false)} />
      <OCRModal open={ocrOpen} onClose={() => setOcrOpen(false)} createForm={createForm} onOpenCreate={() => setCreateOpen(true)} />
      <MofInvoiceModal open={mofOpen} onClose={() => setMofOpen(false)} />
    </ResponsiveContent>
  );
};

export default ERPExpenseListPage;
