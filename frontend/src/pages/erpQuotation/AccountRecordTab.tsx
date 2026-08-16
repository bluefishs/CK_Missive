/**
 * 統一帳款紀錄 Tab — 應收/應付共用
 *
 * 統一欄位: 期別、對象、請款日期、請款金額、發票號碼、
 *          發票金額、收付款狀態、收付款日期、收付款金額
 *
 * 2026-08-02：新增／編輯改為獨立路由頁 `ERPAccountRecordFormPage`（owner：ERP 填報
 * 參考公文設計、減少彈跳視窗）。原 04-05 的豁免理由（欄位少＋緊耦合＋導頁會失去
 * tab 狀態）在**桌面**成立，但未把行動情境納入考慮；返回時已帶 `?tab=` 保留分頁。
 * 2026-08-04：操作欄移除（詳情頁 tab 只呈現不操作，比照 /documents/:id）——
 * 點列進填報頁，編輯與刪除都在那一頁的標題列。
 *
 * @version 2.0.0
 * @date 2026-08-02
 */
import React, { useState } from 'react';
import {
  Button, Tag, Row, Col,
} from 'antd';
import ClickableStatCard from '../../components/common/ClickableStatCard';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import { PlusOutlined } from '@ant-design/icons';

import type { ResponsiveColumn } from '../../components/common/EnhancedTable';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { ROUTES } from '../../router/types';
import { useResponsive } from '../../hooks';

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
  const navigate = useNavigate();
  const { isMobile } = useResponsive();

  const isReceivable = direction === 'receivable';
  const dirLabel = isReceivable ? '應收' : '應付';
  const counterpartyLabel = isReceivable ? '委託單位' : '協力廠商';
  const paymentLabel = isReceivable ? '收款' : '付款';
  const listEndpoint = isReceivable ? ERP_ENDPOINTS.BILLINGS_LIST : ERP_ENDPOINTS.VENDOR_PAYABLES_LIST;
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
  // 2026-08-15：統計卡片要能與列表互動篩選。
  // 原本是三張純顯示的 Card + Statistic —— 看到「未結餘額 200 萬」卻不知道是哪幾筆，
  // 只能自己往下捲著找。ClickableStatCard 早就存在（有 active 樣式與 onClick），
  // 只是沒有擴散到這裡。
  const [statFilter, setStatFilter] = useState<'all' | 'paid' | 'outstanding'>('all');
  const totalRequest = records.reduce((s, r) => s + (r.request_amount || 0), 0);
  const totalPaid = records.reduce((s, r) => s + (r.payment_amount || 0), 0);
  const outstanding = totalRequest - totalPaid;


  const goCreate = () =>
    navigate(
      ROUTES.ERP_ACCOUNT_RECORD_CREATE
        .replace(':quotationId', String(erpQuotationId))
        .replace(':direction', direction),
    );

  const goEdit = (recordId: number) =>
    navigate(
      ROUTES.ERP_ACCOUNT_RECORD_EDIT
        .replace(':quotationId', String(erpQuotationId))
        .replace(':direction', direction)
        .replace(':recordId', String(recordId)),
    );

  // 統一欄位
  // 卡片與列表的對應：點「已收/付」只留有實付金額的、點「未結」只留還有餘額的。
  // 判準與卡片的數字用**同一個欄位**，否則卡片說 3 筆、列表給 5 筆，
  // 那比沒有互動更糟 —— 使用者會以為自己看錯。
  const filteredRecords = records.filter((r) => {
    if (statFilter === 'paid') return (r.payment_amount || 0) > 0;
    if (statFilter === 'outstanding') return (r.request_amount || 0) - (r.payment_amount || 0) > 0;
    return true;
  });

  const columns: ResponsiveColumn<AccountRecord>[] = [
    { title: '期別', dataIndex: 'period', width: 80, render: (v) => v || '-' },
    { title: counterpartyLabel, dataIndex: 'counterparty', width: 140, ellipsis: true },
    { title: '請款日期', dataIndex: 'request_date', width: 110, hideOnMobile: true },
    { title: '請款金額', dataIndex: 'request_amount', width: 110, align: 'right', render: (v: number) => v?.toLocaleString() },
    { title: '發票號碼', dataIndex: 'invoice_number', width: 120, hideOnMobile: true, render: (v) => v || '-' },
    { title: `${paymentLabel}狀態`, dataIndex: 'payment_status', width: 90, align: 'center',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{STATUS_LABELS[s] || s}</Tag> },
    { title: `${paymentLabel}日期`, dataIndex: 'payment_date', width: 110, hideOnMobile: true },
    { title: `${paymentLabel}金額`, dataIndex: 'payment_amount', width: 110, align: 'right', render: (v) => v?.toLocaleString() || '-' },
  ];


  return (
    <div>
      {/* 統計摘要 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}><ClickableStatCard title={`${dirLabel}總額`} value={totalRequest}
          active={statFilter === 'all'} onClick={() => setStatFilter('all')} /></Col>
        <Col xs={24} sm={8}><ClickableStatCard title={`已${paymentLabel}`} value={totalPaid} color="#52c41a"
          active={statFilter === 'paid'} onClick={() => setStatFilter('paid')} /></Col>
        <Col xs={24} sm={8}><ClickableStatCard title="未結餘額" value={outstanding}
          color={outstanding > 0 ? '#ff4d4f' : '#52c41a'}
          active={statFilter === 'outstanding'} onClick={() => setStatFilter('outstanding')} /></Col>
      </Row>

      <div style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={goCreate} block={isMobile}>新增{dirLabel}</Button>
      </div>

      <EnhancedTable<AccountRecord>
        columns={columns}
        dataSource={filteredRecords}
        rowKey="id"
        onRow={(row: AccountRecord) => ({
          // 2026-08-04：操作欄移除後改為點列進填報頁（編輯／刪除都在那一頁的標題列）。
          onClick: () => goEdit(row.id),
          style: { cursor: 'pointer' },
        })}
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
      />

      {/* 新增／編輯已改為獨立頁 ERPAccountRecordFormPage（見檔首說明） */}
    </div>
  );
};

export default AccountRecordTab;
