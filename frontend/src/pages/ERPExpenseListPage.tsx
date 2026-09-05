/**
 * ERP 費用核銷審核 — 主管/財務視角
 *
 * Tab 1: 專案費用 (按案件分組的費用核銷 + 展開明細 + 審核操作)
 * Tab 2: 收支帳本
 *
 * AR/AP 在各案件的 erp/quotations/:id 管理，此頁專注費用核銷。
 *
 * @version 5.0.0
 */
import React, { useState, useMemo, useCallback } from 'react';
import {
  Card, Button, Space, Tag, Typography,
  Row, Col, Tabs, Select,
} from 'antd';
import {
  PlusOutlined, BookOutlined,
  UploadOutlined, FileTextOutlined, ScanOutlined,
  ProjectOutlined, ShopOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { MobileCard } from '../components/common/MobileCardList';
import { ClickableStatCard } from '../components/common';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  useExpenses, useAuthGuard,
  useCaseCodeMap, useLedger,
} from '../hooks';
import type {
  FinanceLedger, LedgerQuery,
} from '../types/erp';
import {
  LEDGER_ENTRY_TYPE_LABELS,
  ledgerSourceLabel,
} from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { ERP_ENDPOINTS } from '../api/endpoints';
import apiClient from '../api/client';
import { ExpenseImportModal, SmartScanModal } from './erpExpense';
import { erpFinanceKeys } from '../hooks/business/useERPFinance';
import InvoiceSubTable from './erpExpense/InvoiceSubTable';
import type { ExpenseGroup } from './erpExpense/InvoiceSubTable';

const { Title } = Typography;

// ExpenseGroup type imported from erpExpense/InvoiceSubTable

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const ERPExpenseListPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const canApprove = hasPermission('projects:write');
  const { data: caseCodeMap } = useCaseCodeMap();

  // Tab = attribution filter (tab key maps to attribution_type)
  const [activeTab, setActiveTab] = useState('all');
  const attributionType = activeTab === 'ledger' ? 'all' : activeTab;

  // 2026-08-29 owner 裁示：「統計圖卡與列表互動篩選，皆以當年度為統計基準」。
  // 年度一律西元（§2.5）。0 = 全部年度。
  const [year, setYear] = useState<number>(new Date().getFullYear());

  // Grouped summary query
  const {
    data: groupedData,
    isLoading: groupedLoading,
  } = useQuery({
    queryKey: ['expense-grouped-summary', attributionType, year],
    queryFn: async () => {
      const body: Record<string, string | number> = {};
      if (attributionType !== 'all') body.attribution_type = attributionType;
      if (year) body.year = year;
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
  const { data: ledgerData } = useLedger(ledgerParams, { enabled: activeTab === 'ledger' });
  const ledgerItems = ledgerData?.items ?? [];

  // Import modal
  const queryClient = useQueryClient();
  const [importOpen, setImportOpen] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);

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
      render: (_: unknown, record: ExpenseGroup & { erp_quotation_id?: number }) => {
        if (record.case_code) {
          const display = record.group_label || caseCodeMap?.[record.case_code] || record.project_code || record.case_code;
          // 有 ERP 報價 → 導航到專案財務
          if (record.erp_quotation_id) {
            return (
              <a
                onClick={(e) => { e.stopPropagation(); navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.erp_quotation_id))); }}
                title={`專案財務: ${record.case_code}`}
              >
                {display}
              </a>
            );
          }
          // 無 ERP 報價 → 顯示案件代碼（不可點擊）
          return <span title={record.case_code}>{display}</span>;
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
          <Col><Title level={3} style={{ margin: 0 }}>費用核銷審核</Title></Col>
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
              {/* 2026-07-30：批次連續掃描 —— 建立頁是「單張→填表→送出」，
                  沒有「拍一張→自動建檔→接著下一張」的批次流程（月結/工地一次多張最需要）。
                  SmartScanModal 原本已寫好卻從未掛載（出生即孤兒），此處整合納入。 */}
              <Button icon={<ScanOutlined />} onClick={() => setScanOpen(true)}>批次掃描</Button>
              <Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>核銷匯入</Button>
              {/* 年度基準（owner 2026-08-29）：西元、預設當年度、0=全部 */}
              <Select
                style={{ width: 120 }}
                value={year}
                onChange={(v) => setYear(v)}
                options={[
                  { value: 0, label: '全部年度' },
                  ...Array.from({ length: 5 }, (_, i) => {
                    const y = new Date().getFullYear() - i;
                    return { value: y, label: `${y} 年` };
                  }),
                ]}
              />
            </Space>
          </Col>
        </Row>

        {/* Stats cards —— 2026-08-29：改為可點擊篩選（owner「統計圖卡與列表
            互動篩選機制」）。點卡片即切換對應歸屬 Tab，再點一次回全部。 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="核銷總筆數" value={totalCount.toLocaleString()}
              icon={<FileTextOutlined />} color="#1890ff"
              active={activeTab === 'all'}
              onClick={() => setActiveTab('all')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="專案費用合計" value={projectAmount.toLocaleString()}
              icon={<ProjectOutlined />} color="#52c41a"
              active={activeTab === 'project'}
              onClick={() => setActiveTab(activeTab === 'project' ? 'all' : 'project')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="營運費用合計" value={operationalAmount.toLocaleString()}
              icon={<ShopOutlined />} color="#faad14"
              active={activeTab === 'operational'}
              onClick={() => setActiveTab(activeTab === 'operational' ? 'all' : 'operational')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title="待審核" value={actualPendingCount.toLocaleString()}
              icon={<ClockCircleOutlined />}
              color={actualPendingCount > 0 ? '#faad14' : '#52c41a'}
              active={activeTab === 'none'}
              onClick={() => setActiveTab(activeTab === 'none' ? 'all' : 'none')}
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
            { key: 'all', label: <><FileTextOutlined /> 全部 <Tag>{totalCount}</Tag></> },
            { key: 'project', label: <>專案費用</> },
            { key: 'operational', label: <>營運費用</> },
            { key: 'none', label: <>未歸屬</> },
            { key: 'ledger', label: <><BookOutlined /> 收支帳本 <Tag>{ledgerItems.length}</Tag></> },
          ]}
        />

        {activeTab !== 'ledger' ? (
          <>
            <EnhancedTable<ExpenseGroup>
              columns={groupColumns}
              dataSource={groups}
              rowKey="group_key"
              loading={groupedLoading}
              size="middle"
              // 2026-09-05：分組表此前不分頁——「專案費用顯示所有案件」讓 100+ 組零費用案件全列，手機整頁 23,000px。
              // 有費用的組本來就排在前面，20 組一頁；資料在前端整份，分頁只是呈現。
              pagination={{ pageSize: 20, showSizeChanger: false, showTotal: (t) => `共 ${t} 組` }}
              expandable={{
                expandedRowKeys: expandedKeys,
                onExpandedRowsChange: (keys) => setExpandedKeys(keys as string[]),
                expandedRowRender: (record) => <ExpandedInvoiceTable record={record} />,
                rowExpandable: () => true,
              }}
              // 2026-09-05 RWD（weekly 111：本頁 134 個 <28px 點擊目標全在表格列內）：手機改卡片，點卡片展開該組明細
              mobileCard={(g: ExpenseGroup & { erp_quotation_id?: number }) => {
                const attr: Record<string, { label: string; color: string }> = {
                  project: { label: '專案', color: 'blue' }, operational: { label: '營運', color: 'green' }, none: { label: '未歸屬', color: 'default' },
                };
                const a = attr[g.attribution_type] ?? { label: g.attribution_type, color: 'default' };
                const label = g.case_code ? (g.group_label || caseCodeMap?.[g.case_code] || g.project_code || g.case_code) : g.group_label;
                const pct = groupedData?.total_amount ? (Number(g.total_amount) / groupedData.total_amount * 100) : 0;
                const open = expandedKeys.includes(g.group_key);
                return (
                  <div>
                    <MobileCard
                      title={label}
                      subtitle={g.case_code}
                      tags={[{ text: a.label, color: a.color }, { text: open ? '收起明細' : `展開 ${g.count} 筆`, color: open ? 'processing' : 'default' }]}
                      amounts={[{ label: '金額合計', value: `${Number(g.total_amount).toLocaleString()}（${pct.toFixed(0)}%）` }]}
                      onClick={() => setExpandedKeys(open ? expandedKeys.filter((k) => k !== g.group_key) : [...expandedKeys, g.group_key])}
                    />
                    {open && <div style={{ margin: '-4px 0 12px' }}><ExpandedInvoiceTable record={g} /></div>}
                  </div>
                );
              }}
            />
          </>
        ) : (
          /* 帳本 Tab */
          <EnhancedTable<FinanceLedger>
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
                // 2026-08-15：原本頁內自帶一份對照，與帳本頁各一份 ——
                // 同一個欄位兩份說法，改一邊另一邊不會知道。已收斂到 types/erp.ts。
                render: (v: string) => <Tag>{ledgerSourceLabel(v)}</Tag>,
              },
            ]}
            dataSource={ledgerItems}
            rowKey="id"
            size="small"
            mobileCard={(r) => (
              <MobileCard
                title={r.description || '（無摘要）'}
                subtitle={`${r.transaction_date ?? ''}${r.case_code ? ` · ${r.case_code}` : ''}`}
                tags={[{ text: LEDGER_ENTRY_TYPE_LABELS[r.entry_type as keyof typeof LEDGER_ENTRY_TYPE_LABELS] ?? r.entry_type, color: r.entry_type === 'income' ? 'green' : 'red' }]}
                rows={[{ label: '分類', value: r.category || '—' }, { label: '來源', value: r.source_type }]}
                amounts={[{ label: '金額', value: `${r.entry_type === 'income' ? '+' : '-'} ${Number(r.amount).toLocaleString()}`, tone: r.entry_type === 'income' ? 'good' : 'bad' }]}
              />
            )}
            pagination={{ pageSize: 20, showTotal: (t: number) => `共 ${t} 筆` }}
          />
        )}
      </Card>

      <ExpenseImportModal open={importOpen} onClose={() => setImportOpen(false)} onSuccess={() => void 0} />
      <SmartScanModal
        open={scanOpen}
        onClose={() => setScanOpen(false)}
        onSuccess={() => {
          // 批次建檔後刷新清單與統計（掃描是直接 auto_create，不走 useCreateExpense mutation）
          queryClient.invalidateQueries({ queryKey: erpFinanceKeys.expenses.all });
          queryClient.invalidateQueries({ queryKey: ['expense-grouped-summary'] });
        }}
      />
    </ResponsiveContent>
  );
};

export default ERPExpenseListPage;
