/**
 * ERP 統一帳本頁面
 *
 * 功能：帳本列表 + 手動記帳 + 分類拆解 + 專案餘額
 */
import React, { useState } from 'react';
import {
  Card, Button, Space, Tag, Select, Typography,
  Statistic, Row, Col, Popconfirm, App, Alert,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  ArrowUpOutlined, ArrowDownOutlined, SwapOutlined, FileTextOutlined, FileSearchOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { ROUTES } from '../router/types';
import { ClickableStatCard } from '../components/common';
import {
  useLedger, useDeleteLedger,
  useLedgerCategoryBreakdown, useAuthGuard, useProjectsDropdown,
  useCaseCodeMap,
} from '../hooks';
import type { FinanceLedger, LedgerQuery, LedgerEntryType } from '../types/erp';
import { LEDGER_ENTRY_TYPE_LABELS, LEDGER_SOURCE_TYPE_OPTIONS, ledgerSourceLabel } from '../types/erp';
import { EnhancedTable } from '../components/common/EnhancedTable';
import type { ColumnsType } from 'antd/es/table';

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
  const deleteMutation = useDeleteLedger();

  const [statFilter, setStatFilter] = useState<string | null>(null);

  // 2026-08-16：移除「手動記帳 Modal」死碼。
  // 記帳早已改為導覽模式（`/erp/ledger/create` → ERPLedgerCreatePage，
  // 下方工具列的按鈕就是 navigate 過去），但 Modal 連同它的 form、
  // handleCreate、createMutation 一起被留了下來 ——
  // **`setCreateOpen(true)` 全檔不存在，那個 Modal 永遠打不開**。
  // 留著的代價不只是行數：它裡面的分類欄是自由輸入的 Input，
  // 任何人照著它改都會以為分類可以隨便打。

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
    {
      // 2026-08-15：原本直接顯示 raw 值（erp_billing／expense_invoice）。
      // 標籤與篩選收在 types/erp.ts 單一處，兩個頁面共用 —— 不各寫一份對照。
      title: '來源', dataIndex: 'source_type', key: 'source_type', width: 110,
      render: (v: string | null) => ledgerSourceLabel(v),
      filters: LEDGER_SOURCE_TYPE_OPTIONS.map(o => ({ text: o.label, value: o.value })),
      onFilter: (value, record: FinanceLedger) => record.source_type === value,
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: FinanceLedger) => (
        <Space size={0}>
          {/* 2026-07-30（owner）：帳本看得到分錄卻「無對應內容可檢視」——
              source_type/source_id 資料一直都在，只是前端沒接鑽取入口。
              有來源單據者提供「檢視來源」直接開原始核銷紀錄。 */}
          {record.source_type === 'expense_invoice' && record.source_id ? (
            <Button
              type="link" size="small" icon={<FileSearchOutlined />}
              onClick={() => navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(record.source_id)))}
            >
              檢視來源
            </Button>
          ) : null}
          {canWrite && record.source_type === 'manual' ? (
            <Popconfirm title="確定刪除？" onConfirm={() => handleDelete(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          ) : null}
        </Space>
      ),
    },
  ];

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  // 2026-07-20：amount 由 API 回字串（Decimal），須 Number() 轉數字防字串串接
  const incomeSum = items.filter(i => i.entry_type === 'income').reduce((s, i) => s + Number(i.amount || 0), 0);
  const expenseSum = items.filter(i => i.entry_type === 'expense').reduce((s, i) => s + Number(i.amount || 0), 0);
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

        <EnhancedTable<FinanceLedger>
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

    </ResponsiveContent>
  );
};

export default ERPLedgerPage;
