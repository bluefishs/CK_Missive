/**
 * ERP 財務總覽 — 主管/財務視角
 *
 * Tab 1: 全案件財務總覽 (應收/應付/費用核銷 by case)
 * Tab 2: 費用核銷審核 (分組+展開+審核操作)
 * Tab 3: 收支帳本
 *
 * @version 4.0.0
 */
import React, { useState, useMemo, useCallback } from 'react';
import {
  Card, Table, Button, Space, Tag, Typography,
  Statistic, Row, Col, Tabs, Segmented, Spin,
} from 'antd';
import {
  PlusOutlined, BookOutlined,
  UploadOutlined, FileTextOutlined,
  FundOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  useExpenses, useAuthGuard,
  useCaseCodeMap, useLedger,
} from '../hooks';
import type {
  FinanceLedger, LedgerQuery,
} from '../types/erp';
import {
  LEDGER_ENTRY_TYPE_LABELS,
} from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { ERP_ENDPOINTS } from '../api/endpoints';
import apiClient from '../api/client';
import { ExpenseImportModal } from './erpExpense';
import InvoiceSubTable from './erpExpense/InvoiceSubTable';
import type { ExpenseGroup } from './erpExpense/InvoiceSubTable';

const { Title, Text } = Typography;

// ExpenseGroup type imported from erpExpense/InvoiceSubTable

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const ERPExpenseListPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const canApprove = hasPermission('projects:write');
  const { data: caseCodeMap } = useCaseCodeMap();

  // Tab state
  const [activeTab, setActiveTab] = useState('overview');

  // 全案件財務總覽
  interface OverviewCase {
    case_code: string; case_name: string | null; project_code: string | null;
    billing_count: number; billing_total: number; billing_received: number;
    payable_count: number; payable_total: number; payable_paid: number;
    expense_count: number; expense_total: number; expense_verified: number; expense_pending: number;
  }
  interface OverviewData {
    cases: OverviewCase[];
    totals: Record<string, number>;
    unlinked_expenses: { count: number; total: number };
  }
  const { data: overviewData, isLoading: overviewLoading } = useQuery<OverviewData>({
    queryKey: ['financial-overview'],
    queryFn: async () => {
      const res = await apiClient.post<{ data: OverviewData }>(ERP_ENDPOINTS.EXPENSES_FINANCIAL_OVERVIEW, {});
      return res.data;
    },
  });

  // Segmented filter (費用核銷 Tab)
  const [attributionType, setAttributionType] = useState<string>('all');

  // Grouped summary query
  const {
    data: groupedData,
    isLoading: groupedLoading,
  } = useQuery({
    queryKey: ['expense-grouped-summary', attributionType],
    queryFn: async () => {
      const body: Record<string, string> = {};
      if (attributionType !== 'all') body.attribution_type = attributionType;
      const res = await apiClient.post<{ data: { groups: ExpenseGroup[]; total_count: number; total_amount: number } }>(
        ERP_ENDPOINTS.EXPENSES_GROUPED_SUMMARY,
        body,
      );
      return res.data;
    },
  });

  const groups: ExpenseGroup[] = useMemo(() => groupedData?.groups ?? [], [groupedData]);
  const totalCount = groupedData?.total_count ?? 0;

  // Derived stats
  const projectAmount = useMemo(
    () => groups
      .filter((g: ExpenseGroup) => g.attribution_type === 'project')
      .reduce((s: number, g: ExpenseGroup) => s + g.total_amount, 0),
    [groups],
  );
  const operationalAmount = useMemo(
    () => groups
      .filter((g: ExpenseGroup) => g.attribution_type === 'operational')
      .reduce((s: number, g: ExpenseGroup) => s + g.total_amount, 0),
    [groups],
  );

  // 帳本 (Tab 2)
  const [ledgerParams] = useState<LedgerQuery>({ skip: 0, limit: 50 });
  const { data: ledgerData } = useLedger(ledgerParams);
  const ledgerItems = ledgerData?.items ?? [];

  // Import modal
  const [importOpen, setImportOpen] = useState(false);

  // Pending count — use a lightweight expenses query
  const { data: pendingSummary } = useExpenses({ status: 'pending', skip: 0, limit: 1 });
  const actualPendingCount = pendingSummary?.pagination?.total ?? 0;

  // ---------------------------------------------------------------------------
  // Expanded row: fetch invoices for a specific group
  // ---------------------------------------------------------------------------
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  const ExpandedInvoiceTable: React.FC<{ record: ExpenseGroup }> = useCallback(
    ({ record }) => <InvoiceSubTable record={record} navigate={navigate} canApprove={canApprove} />,
    [navigate, canApprove],
  );

  // ---------------------------------------------------------------------------
  // Group columns (main table)
  // ---------------------------------------------------------------------------
  const groupColumns: ColumnsType<ExpenseGroup> = [
    {
      title: '歸屬',
      dataIndex: 'attribution_type',
      key: 'attribution_type',
      width: 110,
      render: (v: string) => {
        const map: Record<string, { label: string; color: string }> = {
          project: { label: '專案', color: 'blue' },
          operational: { label: '營運', color: 'green' },
          none: { label: '未歸屬', color: 'default' },
        };
        const item = map[v] ?? { label: v, color: 'default' };
        return <Tag color={item.color}>{item.label}</Tag>;
      },
    },
    {
      title: '分類/案件',
      key: 'group_label',
      ellipsis: true,
      render: (_: unknown, record: ExpenseGroup) => {
        if (record.case_code) {
          const display = record.group_label || caseCodeMap?.[record.case_code] || record.project_code || record.case_code;
          return (
            <a
              onClick={(e) => { e.stopPropagation(); navigate(`/pm/cases?search=${record.case_code}`); }}
              title={`案件: ${record.case_code}`}
            >
              {display}
            </a>
          );
        }
        return record.group_label;
      },
    },
    {
      title: '筆數',
      dataIndex: 'count',
      key: 'count',
      width: 90,
      align: 'right',
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '金額合計',
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 200,
      render: (v: number) => {
        const pct = groupedData?.total_amount ? (Number(v) / groupedData.total_amount * 100) : 0;
        return (
          <Space size={8}>
            <span style={{ fontWeight: 500, minWidth: 80, textAlign: 'right', display: 'inline-block' }}>
              {Number(v).toLocaleString()}
            </span>
            <div style={{ width: 60 }}>
              <div style={{ background: '#f0f0f0', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: pct > 50 ? '#1890ff' : '#52c41a', borderRadius: 4 }} />
              </div>
              <span style={{ fontSize: 11, color: '#999' }}>{pct.toFixed(0)}%</span>
            </div>
          </Space>
        );
      },
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* Header + Toolbar */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>財務總覽</Title></Col>
          <Col>
            <Space wrap>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate(ROUTES.ERP_EXPENSE_CREATE)}
                size="large"
              >
                新增核銷
              </Button>
              <Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>核銷匯入</Button>
            </Space>
          </Col>
        </Row>

        {/* Stats cards */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}>
            <Statistic title="核銷總筆數" value={totalCount} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="專案費用合計" value={projectAmount} precision={0} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="營運費用合計" value={operationalAmount} precision={0} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="待審核"
              value={actualPendingCount}
              styles={{ content: { color: actualPendingCount > 0 ? '#faad14' : undefined } }}
            />
          </Col>
        </Row>
      </Card>

      {/* Main content */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'overview',
              label: <><FundOutlined /> 全案件總覽 <Tag>{overviewData?.cases.length ?? 0}</Tag></>,
              children: null,
            },
            {
              key: 'expenses',
              label: <><FileTextOutlined /> 費用核銷審核 <Tag>{totalCount}</Tag></>,
              children: null,
            },
            {
              key: 'ledger',
              label: <><BookOutlined /> 收支帳本 <Tag>{ledgerItems.length}</Tag></>,
              children: null,
            },
          ]}
        />

        {activeTab === 'overview' ? (
          overviewLoading ? <Spin style={{ display: 'block', margin: '40px auto' }} /> : (
            <Table<OverviewCase>
              columns={[
                {
                  title: '案件', key: 'case',
                  render: (_: unknown, r: OverviewCase) => (
                    <Button type="link" size="small" style={{ padding: 0 }}
                      onClick={() => navigate(ROUTES.ERP_QUOTATIONS)}>
                      {r.project_code || r.case_code}
                      {r.case_name && <span style={{ marginLeft: 4, fontSize: 12, color: '#999' }}>{r.case_name.slice(0, 20)}</span>}
                    </Button>
                  ),
                },
                {
                  title: '應收(請款)', key: 'billing', width: 140, align: 'right',
                  render: (_: unknown, r: OverviewCase) => (
                    <span>
                      <span style={{ color: '#1890ff' }}>{r.billing_total.toLocaleString()}</span>
                      <Text type="secondary" style={{ fontSize: 11 }}> ({r.billing_count})</Text>
                    </span>
                  ),
                  sorter: (a: OverviewCase, b: OverviewCase) => a.billing_total - b.billing_total,
                },
                {
                  title: '已收', key: 'received', width: 120, align: 'right',
                  render: (_: unknown, r: OverviewCase) => (
                    <span style={{ color: r.billing_received > 0 ? '#52c41a' : '#999' }}>
                      {r.billing_received.toLocaleString()}
                    </span>
                  ),
                },
                {
                  title: '應付(外包)', key: 'payable', width: 140, align: 'right',
                  render: (_: unknown, r: OverviewCase) => (
                    <span>
                      <span style={{ color: '#ff4d4f' }}>{r.payable_total.toLocaleString()}</span>
                      <Text type="secondary" style={{ fontSize: 11 }}> ({r.payable_count})</Text>
                    </span>
                  ),
                  sorter: (a: OverviewCase, b: OverviewCase) => a.payable_total - b.payable_total,
                },
                {
                  title: '已付', key: 'paid', width: 120, align: 'right',
                  render: (_: unknown, r: OverviewCase) => (
                    <span style={{ color: r.payable_paid > 0 ? '#52c41a' : '#999' }}>
                      {r.payable_paid.toLocaleString()}
                    </span>
                  ),
                },
                {
                  title: '費用核銷', key: 'expense', width: 130, align: 'right',
                  render: (_: unknown, r: OverviewCase) => (
                    <span>
                      <span style={{ color: '#fa8c16' }}>{r.expense_total.toLocaleString()}</span>
                      {r.expense_pending > 0 && <Tag color="orange" style={{ marginLeft: 4, fontSize: 10 }}>待審</Tag>}
                    </span>
                  ),
                },
              ]}
              dataSource={overviewData?.cases ?? []}
              rowKey="case_code"
              size="small"
              pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 個案件` }}
              summary={() => {
                const t = overviewData?.totals;
                if (!t) return null;
                return (
                  <Table.Summary fixed>
                    <Table.Summary.Row>
                      <Table.Summary.Cell index={0}><Text strong>合計</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={1} align="right"><Text strong style={{ color: '#1890ff' }}>{(t.billing ?? 0).toLocaleString()}</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={2} align="right"><Text strong style={{ color: '#52c41a' }}>{(t.billing_received ?? 0).toLocaleString()}</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={3} align="right"><Text strong style={{ color: '#ff4d4f' }}>{(t.payable ?? 0).toLocaleString()}</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={4} align="right"><Text strong style={{ color: '#52c41a' }}>{(t.payable_paid ?? 0).toLocaleString()}</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right"><Text strong style={{ color: '#fa8c16' }}>{(t.expense ?? 0).toLocaleString()}</Text></Table.Summary.Cell>
                    </Table.Summary.Row>
                  </Table.Summary>
                );
              }}
            />
          )
        ) : activeTab === 'expenses' ? (
          <>
            <Segmented
              style={{ marginBottom: 16 }}
              value={attributionType}
              onChange={(v) => setAttributionType(v as string)}
              options={[
                { value: 'all', label: '全部' },
                { value: 'project', label: '專案費用' },
                { value: 'operational', label: '營運費用' },
                { value: 'none', label: '未歸屬' },
              ]}
            />

            <Table<ExpenseGroup>
              columns={groupColumns}
              dataSource={groups}
              rowKey="group_key"
              loading={groupedLoading}
              size="middle"
              pagination={false}
              expandable={{
                expandedRowKeys: expandedKeys,
                onExpandedRowsChange: (keys) => setExpandedKeys(keys as string[]),
                expandedRowRender: (record) => <ExpandedInvoiceTable record={record} />,
                rowExpandable: () => true,
              }}
            />
          </>
        ) : (
          /* 帳本 Tab */
          <Table<FinanceLedger>
            columns={[
              {
                title: '日期', dataIndex: 'transaction_date', key: 'date', width: 110,
                render: (v?: string) => v ?? '-',
              },
              {
                title: '類型', dataIndex: 'entry_type', key: 'type', width: 80,
                render: (v: string) => (
                  <Tag color={v === 'income' ? 'green' : 'red'}>
                    {LEDGER_ENTRY_TYPE_LABELS[v as keyof typeof LEDGER_ENTRY_TYPE_LABELS] ?? v}
                  </Tag>
                ),
              },
              {
                title: '金額', dataIndex: 'amount', key: 'amount', width: 120, align: 'right',
                render: (v: number, r: FinanceLedger) => (
                  <span style={{ color: r.entry_type === 'income' ? '#52c41a' : '#ff4d4f' }}>
                    {r.entry_type === 'income' ? '+' : '-'} {Number(v).toLocaleString()}
                  </span>
                ),
              },
              { title: '分類', dataIndex: 'category', key: 'category', width: 100 },
              { title: '摘要', dataIndex: 'description', key: 'description', ellipsis: true },
              {
                title: '案號', dataIndex: 'case_code', key: 'case_code', width: 140,
                render: (v?: string) => v ? (caseCodeMap?.[v] || v) : '-',
              },
              {
                title: '來源', dataIndex: 'source_type', key: 'source', width: 100,
                render: (v: string) => {
                  const labels: Record<string, string> = {
                    manual: '手動', expense_invoice: '報銷', erp_billing: '請款',
                    vendor_payable: '付款', operational: '營運',
                  };
                  return <Tag>{labels[v] ?? v}</Tag>;
                },
              },
            ]}
            dataSource={ledgerItems}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 筆` }}
          />
        )}
      </Card>

      <ExpenseImportModal open={importOpen} onClose={() => setImportOpen(false)} onSuccess={() => void 0} />
    </ResponsiveContent>
  );
};

export default ERPExpenseListPage;
