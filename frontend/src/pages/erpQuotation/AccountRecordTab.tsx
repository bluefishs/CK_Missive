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
import { Button, Tag, Row, Col, Alert, Modal, Form, Input, DatePicker, App, Tooltip, Space } from 'antd';
import ClickableStatCard from '../../components/common/ClickableStatCard';
import { useCreateInvoiceFromBilling } from '../../hooks/business/useERPQuotations';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import { PlusOutlined } from '@ant-design/icons';

import type { ResponsiveColumn } from '../../components/common/EnhancedTable';
import type { ERPBilling, ERPVendorPayable } from '../../types/erp';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { extractApiMessage } from '../../utils/apiMessage';
import { ROUTES } from '../../router/types';
import { useResponsive } from '../../hooks';

/** 帳款方向 */
type AccountDirection = 'receivable' | 'payable';

interface AccountRecord {
  id: number;
  period?: string;
  /** 說明 —— 只有應付有（`erp_vendor_payables.description`）。
   *  應收的對手方與案名由報價帶出，不需要這一欄。 */
  description?: string;
  counterparty?: string;       // 對象 (委託單位 or 廠商)
  /** 2026-08-27（V4）：廠商身分以 FK 為單一來源，而應付單自存的那份
   *  文字若與之不同會放這裡 ⇒ **這一筆的廠商身分有出入，要看得見**。 */
  counterpartyRecorded?: string;
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
  /** 委託單位名稱（應收列表的對象）。2026-08-17：原本 counterparty 是硬編
   *  字串 '委託單位'，所以每列都顯示欄位名而不是真實單位名。 */
  clientName?: string;
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
//
// 2026-08-17 owner：「委託單位無同步顯示」。
// 原因很直接：`counterparty` 原本是**硬編字串 `'委託單位'`**（欄位標題被當成值），
// 所以每一列都顯示「委託單位」四個字而不是真實名稱
// （該案實際是「嘉義縣竹崎地政事務所」，資料一直都在 contract_projects.client_agency）。
// `invoice_number` 也寫死 undefined —— 而請款其實有關聯發票（erp_invoices.billing_id）。
//
// 兩者都是「資料在，缺的是接出來」，同本專案反覆記錄的形狀。
const billingToRecord = (
  b: ERPBilling,
  clientName?: string,
): AccountRecord => ({
  id: b.id,
  period: b.billing_period ?? '',
  // 應收沒有說明欄位（對手方與案名由報價帶出）—— 給 undefined 讓兩邊型別一致
  description: undefined,
  counterparty: clientName || '（未設定委託單位）',
  request_date: b.billing_date,
  request_amount: Number(b.billing_amount || 0),
  invoice_number: b.invoice_number || undefined,
  invoice_date: b.invoice_date || undefined,
  invoice_amount: b.invoice_amount != null ? Number(b.invoice_amount) : undefined,
  payment_status: b.payment_status || 'pending',
  payment_date: b.payment_date,
  payment_amount: b.payment_amount ? Number(b.payment_amount) : undefined,
  notes: b.notes,
});

// 資料轉換: vendor_payable → 統一格式
// 2026-08-18：參數改用 `ERPVendorPayable` 而非 `Record<string, unknown>`。
//
// 原本每個欄位都 `as` 轉型 —— 於是 08-18 我在後端補了 `payable_period`
// 卻漏了前端型別，**tsc 完全沒有機會發現**（轉型把它繞過去了）。
// 同一次比對還揪出前端介面少了 7 個後端一直有回傳的欄位。
//
// **繞過型別的地方，型別就守不住那個欄位。**
const payableToRecord = (p: ERPVendorPayable): AccountRecord => ({
  id: p.id,
  // 2026-08-18：應付已補 `payable_period`（owner：「應收與應付兩者設計不一致」）。
  // 08-17 曾把 `description` 擠進這一格當權宜 —— 那讓「期別」欄裝著說明，
  // 是本專案反覆記錄的「一欄多語意」。現在兩者各自成欄。
  period: p.payable_period || undefined,
  description: p.description || undefined,
  counterparty: p.vendor_name,
  counterpartyRecorded: p.vendor_name_recorded,
  request_date: p.due_date,
  request_amount: Number(p.payable_amount || 0),
  invoice_number: p.invoice_number,
  payment_status: p.payment_status || 'unpaid',
  payment_date: p.paid_date,
  payment_amount: p.paid_amount ? Number(p.paid_amount) : undefined,
  notes: p.notes,
});

export const AccountRecordTab: React.FC<AccountRecordTabProps> = ({
  erpQuotationId,
  direction,
  clientName,
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

  const records: AccountRecord[] = (
    rawData?.data ?? (rawData as unknown as Record<string, unknown>[]) ?? []
  ).map((row) =>
    isReceivable
      ? billingToRecord(row as unknown as ERPBilling, clientName)
      : payableToRecord(row as unknown as ERPVendorPayable),
  );

  const collectedNoInvoice = records.filter((r) => !r.invoice_number && (r.payment_status === 'paid' || r.payment_status === 'partial'));

  // 統計
  // 2026-08-15：統計卡片要能與列表互動篩選。
  // 原本是三張純顯示的 Card + Statistic —— 看到「未結餘額 200 萬」卻不知道是哪幾筆，
  // 只能自己往下捲著找。ClickableStatCard 早就存在（有 active 樣式與 onClick），
  // 只是沒有擴散到這裡。
  const [statFilter, setStatFilter] = useState<'all' | 'paid' | 'outstanding'>('all');

  // 2026-08-17 owner：「請款如何與發票關聯 前端填列時無項目」。
  //
  // 查證結果：整條鏈**都建好了** —— `erp_invoices.billing_id` 欄位、
  // `create_from_billing` 服務（含「已有關聯發票」防重）、
  // `/erp/invoices/create-from-billing` 端點、前端 api + `useCreateInvoiceFromBilling`
  // hook（含 cache 失效）。**缺的只有頁面上的那顆按鈕。**
  //
  // 這與 08-02 移除 `InvoicesTab` 有關：當時判定它「沒有任何頁面在使用」而刪掉，
  // 那個判斷是對的（它真的是孤兒），但**沒有把功能接回真正該在的位置** ——
  // 於是能力還在、入口消失了。同「資料在，缺的是出口」那個形狀。
  const [invoiceFor, setInvoiceFor] = useState<AccountRecord | null>(null);
  const [invoiceForm] = Form.useForm();
  const createInvoice = useCreateInvoiceFromBilling();
  const { message: msg } = App.useApp();
  const totalRequest = records.reduce((s, r) => s + (r.request_amount || 0), 0);
  const totalPaid = records.reduce((s, r) => s + (r.payment_amount || 0), 0);
  const outstanding = totalRequest - totalPaid;

  // 2026-08-17 owner：「已受經費無登入與卡片互動」。
  //
  // 查證後這兩件是**同一件事**：那筆的 payment_status='paid' 但 payment_amount
  // 是空的（根因＝ERPBillingCreate 少了該欄位，Pydantic 靜默丟棄，同日已修），
  // 於是「已收款」算 0、點下去也篩不到任何一筆 —— 看起來像互動壞掉。
  //
  // 這一段不是修根因（根因在後端），是**讓矛盾看得見**：
  // 「狀態說已收付、金額卻是空的」顯示成 0 等於把資料缺失偽裝成「還沒收」。
  // 兩者對使用者的意義完全相反。
  const paidButNoAmount = records.filter(
    (r) => r.payment_status === 'paid' && !(r.payment_amount || 0),
  );

  // ── 代墊風險：付協力廠商時，客戶那邊還沒付 ──────────────────────
  //
  // 外部評估建議在應付表新增 `linked_billing_id`（綁定請款期別）。
  // **不採用那個做法**：新欄位要人去填，而本專案剛付過這個代價 ——
  // 承辦同仁欄位存在多時，257 張報價單裡 122 張是空的，因為沒人填。
  // 一個沒人填的欄位提供的不是精確度，是**假的精確度**。
  //
  // 改成用**已經存在的事實**判斷：同一張報價單底下有沒有未收的請款。
  // 這不需要任何人多填一格，而且涵蓋所有案子（實測當日 4 件符合）。
  // 代價是它說不出「是哪一期」—— 那正是誠實的界線，寫在提示文字裡。
  const { data: arRaw } = useQuery({
    queryKey: ['erp-billings', erpQuotationId, 'for-backtoback'],
    queryFn: () => apiClient.post<{ data: Record<string, unknown>[] }>(
      ERP_ENDPOINTS.BILLINGS_LIST, { erp_quotation_id: erpQuotationId }),
    enabled: !isReceivable,   // 只有應付那一側需要問這件事
  });
  const unpaidAr = (
    (arRaw?.data ?? (arRaw as unknown as Record<string, unknown>[]) ?? [])
  ).filter((b) => b.payment_status !== 'paid');
  const unpaidArAmount = unpaidAr.reduce(
    (sum, b) => sum + (Number(b.billing_amount) || 0) - (Number(b.payment_amount) || 0), 0);
  const hasUnpaidPayable = !isReceivable
    && records.some((r) => r.payment_status !== 'paid');


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
    /* 期別 —— 兩方向共用同一份詞彙表（`schemas/erp/billing.py: BillingPeriod`）。
       2026-08-18 應付補上 `payable_period` 後，這一欄不再身兼二職。 */
    { title: '期別', dataIndex: 'period', width: 90, render: (v) => v || '-' },
    /* 說明只有應付有（`description`，DB 一直有值但表單與列表都沒有入口，
       08-18 才接上）。應收的對手方與案名由報價帶出，不需要這一欄。 */
    ...(isReceivable ? [] : [{
      title: '說明',
      dataIndex: 'description' as const,
      width: 180,
      ellipsis: true,
      render: (v: unknown) => (v as string) || '-',
    }]),
    {
      title: counterpartyLabel, dataIndex: 'counterparty', width: 140, ellipsis: true,
      // 2026-08-27（V4）：廠商名以 FK 為單一來源。若這一筆自存的名字與之不同，
      // **要看得見** —— 實測「林晉廷」vs FK 的「林宥廷測量技師事務所」是不同的人，
      // 只顯示其中一個就等於替使用者決定了哪個對（而系統不知道）。
      render: (v: string, r: AccountRecord) => (
        r.counterpartyRecorded ? (
          <Tooltip title={`此筆自行填寫的名稱是「${r.counterpartyRecorded}」，與廠商檔登記的不同 —— 請確認是同一家。`}>
            <span>{v} <Tag color="orange" style={{ marginInlineStart: 4 }}>名稱不符</Tag></span>
          </Tooltip>
        ) : <span>{v}</span>
      ),
    },
    { title: '請款日期', dataIndex: 'request_date', width: 110, hideOnMobile: true },
    // 2026-08-17 owner：「建議列表表單僅顯示已收款經費資訊」。
    // 請款金額與收款金額實測 36/36 完全相同（見 ERPAccountRecordFormPage 的說明），
    // 兩欄併列只是讓表變寬。請款金額降為窄螢幕隱藏 —— **不移除**：
    // 部分收款時兩者會不同，那時它是唯一能看出差額的欄位。
    { title: `${dirLabel}金額`, dataIndex: 'request_amount', width: 110, align: 'right',
      hideOnMobile: true, render: (v: number) => v?.toLocaleString() },
    { title: `${paymentLabel}狀態`, dataIndex: 'payment_status', width: 90, align: 'center',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{STATUS_LABELS[s] || s}</Tag> },
    { title: `${paymentLabel}日期`, dataIndex: 'payment_date', width: 110, hideOnMobile: true },
    { title: `${paymentLabel}金額`, dataIndex: 'payment_amount', width: 110, align: 'right', render: (v) => v?.toLocaleString() || '-' },
    // 開立發票只對應收有意義（銷項）。已有發票號的不再顯示按鈕 ——
    // 服務層本來就會擋（一筆請款只能有一張發票），但按鈕留著會讓人按了才知道。
    // 2026-09-04 owner「更新發票後變成無按鈕但也無顯示」：此前「發票號碼」欄 hideOnMobile、而「發票」動作欄
    // 有票就 null ⇒ 窄螢幕上兩欄都空。合成一欄（owner：文字統一「發票號碼」）：有票印號碼（日期／金額在 tooltip），
    // 沒票給「開立發票」；已收款卻沒票的標「已收未開票」——那是 168 那種「填報了」卻沒有紀錄的防呆點。
    ...(isReceivable ? [{
      title: '發票號碼', width: 150, align: 'center' as const,
      render: (_: unknown, r: AccountRecord) => {
        if (r.invoice_number) {
          return (
            <Tooltip title={`開立日期 ${r.invoice_date ?? '-'}｜發票金額 ${(r.invoice_amount ?? r.request_amount ?? 0).toLocaleString()}`}>
              <Tag color="blue" style={{ margin: 0 }}>{r.invoice_number}</Tag>
            </Tooltip>
          );
        }
        const collected = r.payment_status === 'paid' || r.payment_status === 'partial';
        return (
          <Space size={4}>
            {collected && <Tag color="orange" style={{ margin: 0 }}>已收未開票</Tag>}
            <Button type="link" size="small" style={{ padding: 0 }}
              onClick={(e) => { e.stopPropagation(); setInvoiceFor(r); invoiceForm.resetFields(); }}
            >開立發票</Button>
          </Space>
        );
      },
    }] : []),
  ];


  return (
    <div>
      {/* 統計摘要 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}><ClickableStatCard title={`${dirLabel}總額`} value={totalRequest}
          active={statFilter === 'all'} onClick={() => setStatFilter('all')} /></Col>
        <Col xs={24} sm={8}><ClickableStatCard
          title={paidButNoAmount.length
            ? `已${paymentLabel}（${paidButNoAmount.length} 筆缺金額）`
            : `已${paymentLabel}`}
          value={totalPaid}
          color={paidButNoAmount.length ? '#faad14' : '#52c41a'}
          active={statFilter === 'paid'} onClick={() => setStatFilter('paid')} /></Col>
        <Col xs={24} sm={8}><ClickableStatCard title="未結餘額" value={outstanding}
          color={outstanding > 0 ? '#ff4d4f' : '#52c41a'}
          active={statFilter === 'outstanding'} onClick={() => setStatFilter('outstanding')} /></Col>
      </Row>

      {isReceivable && collectedNoInvoice.length > 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message={`已收款但尚未登錄發票 ${collectedNoInvoice.length} 筆（${collectedNoInvoice.reduce((a, r) => a + (r.request_amount ?? 0), 0).toLocaleString()} 元）——收款前應先開立發票，請補登號碼`} />
      )}
      {/* 開立發票：3 欄（發票號／日期／備註），在 Modal 豁免範圍內
          （UI_DESIGN_STANDARDS 2026-04-06：欄位 3-5 個且緊耦合 context）。
          它必須貼著「哪一筆請款」，做成獨立頁反而要再帶一次 context。 */}
      <Modal
        title={`開立發票 — ${invoiceFor?.period || `#${invoiceFor?.id ?? ''}`}（${(invoiceFor?.request_amount ?? 0).toLocaleString()} 元）`}
        open={!!invoiceFor}
        onCancel={() => setInvoiceFor(null)}
        confirmLoading={createInvoice.isPending}
        onOk={async () => {
          const v = await invoiceForm.validateFields();
          try {
            await createInvoice.mutateAsync({
              billing_id: invoiceFor!.id,
              invoice_number: v.invoice_number,
              invoice_date: v.invoice_date?.format('YYYY-MM-DD'),
              notes: v.notes,
            });
            msg.success('發票已開立並關聯到此請款');
            setInvoiceFor(null);
          } catch (e) {
            msg.error(extractApiMessage(e, '開立發票失敗'));
          }
        }}
      >
        <Form form={invoiceForm} layout="vertical">
          <Form.Item name="invoice_number" label="發票號碼" normalize={(v?: string) => (v ?? '').toUpperCase().trim()}
            rules={[{ required: true, message: '請輸入發票號碼' }, { pattern: /^[A-Z]{2}\d{8}$/, message: '統一發票為 2 個英文字母＋8 碼數字（例 EE15019500）' },
                    { pattern: /^[A-Z]{2}\d{8}$/, message: '格式為 2 英文 + 8 數字（如 AB12345678）' }]}>
            <Input placeholder="AB12345678" maxLength={10} />
          </Form.Item>
          <Form.Item name="invoice_date" label="開立日期"
            extra="留空則以今日為開立日">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} maxLength={200} />
          </Form.Item>
        </Form>
      </Modal>

      {hasUnpaidPayable && unpaidAr.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="這個案子的客戶款還沒收齊，而底下有未付的協力款"
          description={
            <span>
              客戶端還有 <strong>{unpaidAr.length}</strong> 筆請款未收訖
              （未收約 <strong>NT$ {Math.round(unpaidArAmount).toLocaleString()}</strong>）。
              現在付協力廠商等於<strong>公司先行代墊</strong> —— 請評估資金水位再送出。
              <br />
              ⚠️ 這是<strong>案件層級</strong>的提醒，說不出「哪一期對哪一期」——
              系統沒有那個對應關係，而硬要人手動綁定只會多一個沒人填的欄位。
            </span>
          }
        />
      )}

      {paidButNoAmount.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={`${paidButNoAmount.length} 筆標記為「已${paymentLabel}」但沒有${paymentLabel}金額`}
          description={
            <span>
              這些紀錄不會計入「已{paymentLabel}」，也<strong>不會進入統一帳本</strong>
              （入帳條件要求有金額）—— 公司層財務彙總會少掉這幾筆。
              請點入該筆補填{paymentLabel}金額。
              期別：{paidButNoAmount.map(r => r.period || `#${r.id}`).join('、')}
            </span>
          }
        />
      )}

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
