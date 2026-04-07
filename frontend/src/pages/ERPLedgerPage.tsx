/**
 * ERP 統一帳本頁面
 *
 * 功能：帳本列表 + 手動記帳 + 分類拆解 + 專案餘額
 */
import React, { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Input, Select, Typography,
  Statistic, Row, Col, Modal, Form, DatePicker, Popconfirm, App, Alert,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  ArrowUpOutlined, ArrowDownOutlined, SwapOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { ROUTES } from '../router/types';
import { ClickableStatCard } from '../components/common';
import {
  useLedger, useCreateLedger, useDeleteLedger,
  useLedgerCategoryBreakdown, useAuthGuard, useProjectsDropdown,
  useCaseCodeMap,
} from '../hooks';
import type { FinanceLedger, LedgerQuery, LedgerCreate, LedgerEntryType } from '../types/erp';
import { LEDGER_ENTRY_TYPE_LABELS } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title } = Typography;

const ERPLedgerPage: React.FC = () => {
  const { hasPermission } = useAuthGuard();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const canWrite = hasPermission('projects:write');
  const [params, setParams] = useState<LedgerQuery>({ skip: 0, limit: 20 });
  const { projects: projectOptions } = useProjectsDropdown();
  const { data: caseCodeMap } = useCaseCodeMap();
  const { data, isLoading, isError, refetch } = useLedger(params);
  const { data: breakdownData } = useLedgerCategoryBreakdown({ entry_type: 'expense' });
  const createMutation = useCreateLedger();
  const deleteMutation = useDeleteLedger();

  const [statFilter, setStatFilter] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm<LedgerCreate>();

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      const payload: LedgerCreate = {
        ...values,
        amount: Number(values.amount),
        transaction_date: values.transaction_date ? dayjs(values.transaction_date).format('YYYY-MM-DD') : undefined,
      };
      await createMutation.mutateAsync(payload);
      message.success('記帳成功');
      setCreateOpen(false);
      createForm.resetFields();
    } catch {
      message.error('記帳失敗');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('已刪除');
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '刪除失敗';
      message.error(errMsg);
    }
  };

  const columns: ColumnsType<FinanceLedger> = [
    { title: '日期', dataIndex: 'transaction_date', key: 'transaction_date', width: 110 },
    {
      title: '類型',
      dataIndex: 'entry_type',
      key: 'entry_type',
      width: 80,
      render: (v: LedgerEntryType) => (
        <Tag color={v === 'income' ? 'green' : 'red'}>{LEDGER_ENTRY_TYPE_LABELS[v]}</Tag>
      ),
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right',
      render: (v: number, record: FinanceLedger) => (
        <span style={{ color: record.entry_type === 'income' ? '#52c41a' : '#ff4d4f' }}>
          {v?.toLocaleString()}
        </span>
      ),
    },
    { title: '分類', dataIndex: 'category', key: 'category', width: 120 },
    {
      title: '案號', dataIndex: 'case_code', key: 'case_code', width: 160,
      render: (v: string | null) => {
        if (!v) return '一般營運';
        const pc = caseCodeMap?.[v];
        return pc ? <span title={v}>{pc}</span> : v;
      },
    },
    { title: '說明', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '來源', dataIndex: 'source_type', key: 'source_type', width: 100 },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: FinanceLedger) =>
        canWrite && record.source_type === 'manual' ? (
          <Popconfirm title="確定刪除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        ) : null,
    },
  ];

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const incomeSum = items.filter(i => i.entry_type === 'income').reduce((s, i) => s + (i.amount || 0), 0);
  const expenseSum = items.filter(i => i.entry_type === 'expense').reduce((s, i) => s + (i.amount || 0), 0);
  const breakdownItems = breakdownData?.data ?? [];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>統一帳本</Title></Col>
          <Col>
            {canWrite && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(ROUTES.ERP_LEDGER_CREATE)}>手動記帳</Button>
            )}
          </Col>
        </Row>
        <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="本頁收入" value={incomeSum.toLocaleString()}
              icon={<ArrowUpOutlined />} color="#3f8600"
              active={statFilter === 'income'}
              onClick={() => { const v = statFilter === 'income' ? null : 'income'; setStatFilter(v); setParams(p => ({ ...p, entry_type: v as LedgerEntryType | undefined ?? undefined, skip: 0 })); }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="本頁支出" value={expenseSum.toLocaleString()}
              icon={<ArrowDownOutlined />} color="#cf1322"
              active={statFilter === 'expense'}
              onClick={() => { const v = statFilter === 'expense' ? null : 'expense'; setStatFilter(v); setParams(p => ({ ...p, entry_type: v as LedgerEntryType | undefined ?? undefined, skip: 0 })); }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="本頁淨額" value={(incomeSum - expenseSum).toLocaleString()}
              icon={<SwapOutlined />} color={incomeSum - expenseSum >= 0 ? '#52c41a' : '#ff4d4f'}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="總筆數" value={total}
              icon={<FileTextOutlined />} color="#1890ff"
              active={statFilter === null}
              onClick={() => { setStatFilter(null); setParams(p => ({ ...p, entry_type: undefined, skip: 0 })); }}
            />
          </Col>
        </Row>
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      {/* 支出分類拆解 */}
      {Array.isArray(breakdownItems) && breakdownItems.length > 0 && (
        <Card title="支出分類拆解" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={[8, 8]}>
            {breakdownItems.map((item: { category: string; total: number; count: number }) => (
              <Col key={item.category} xs={12} sm={8} md={6}>
                <Statistic title={item.category} value={item.total} precision={0} suffix={`(${item.count}筆)`} />
              </Col>
            ))}
          </Row>
        </Card>
      )}

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            placeholder="篩選專案"
            allowClear
            showSearch
            optionFilterProp="label"
            value={params.case_code}
            onChange={(v) => setParams(p => ({ ...p, case_code: v || undefined, skip: 0 }))}
            style={{ width: 220 }}
            options={projectOptions?.filter(p => p.project_code).map(p => ({ value: p.project_code, label: `${p.project_code} ${p.project_name}` })) ?? []}
          />
          <Select
            placeholder="類型"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => setParams(p => ({ ...p, entry_type: v as LedgerEntryType, skip: 0 }))}
            options={Object.entries(LEDGER_ENTRY_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
        </Space>

        <Table<FinanceLedger>
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
          size="middle"
          scroll={{ x: 900 }}
        />
      </Card>

      {/* 手動記帳 Modal */}
      <Modal
        title="手動記帳"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); createForm.resetFields(); }}
        confirmLoading={createMutation.isPending}
        width={480}
      >
        <Form form={createForm} layout="vertical" initialValues={{ entry_type: 'expense' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="entry_type" label="類型" rules={[{ required: true }]}>
                <Select options={Object.entries(LEDGER_ENTRY_TYPE_LABELS).map(([value, label]) => ({ value, label }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="amount" label="金額" rules={[{ required: true }]}>
                <Input type="number" min={0} step={0.01} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分類">
                <Input placeholder="例：交通費、材料費" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="transaction_date" label="交易日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="case_code" label="案號 (選填)">
            <Input placeholder="留空 = 一般營運支出" />
          </Form.Item>
          <Form.Item name="description" label="說明">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </ResponsiveContent>
  );
};

export default ERPLedgerPage;
