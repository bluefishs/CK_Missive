/**
 * ERP 報價/成本管理列表頁面
 */
import React, { useState } from 'react';
import { FilterBar } from '../components/common/FilterBar';
import { MobileCard } from '../components/common/MobileCardList';
import { fmtMoney } from '../utils/money';
import { termTitle } from '../constants/financeTerms';
import { Card, Button, Space, Input, Select, Typography, Row, Col, Alert, App, Upload, Tag } from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { PlusOutlined, ReloadOutlined, UploadOutlined, FileExcelOutlined, DollarOutlined, FundOutlined, BankOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { erpQuotationsApi } from '../api/erp';
import { useNavigate } from 'react-router-dom';
import { useERPQuotations, useERPProfitSummary, useAuthGuard } from '../hooks';
import { useERPQuotationClientOptions } from '../hooks/business/useERPQuotations';
import type { ERPQuotation, ERPQuotationListParams } from '../types/erp';
import type { ResponsiveColumn } from '../components/common/EnhancedTable';
import { ROUTES } from '../router/types';
import { ClickableStatCard } from '../components/common';
import { getErrorMessage } from '../utils/apiErrorParser';

const { Title, Text } = Typography;

// development-rules §2.6 ③：列表以**當年度**為統計基準；§2.5：紀年一律西元。
// 2026-08-29 複查發現本頁**完全沒有年度篩選 UI** —— `params.year` 只在匯出時
// 用得到，於是列表把所有年度混在一起，統計卡也是歷年總和。
const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = [
  { value: 0, label: '全部年度' },
  ...Array.from({ length: 5 }, (_, i) => {
    const y = CURRENT_YEAR - i;
    return { value: y, label: `${y} 年` };
  }),
];

/** 案件年度：由建案案號 CK{年}_… 取；取不到才用報價單 year */
const caseYear = (r: ERPQuotation): number | undefined => {
  const m = /^CK(\d{4})_/.exec(r.case_code ?? '');
  return m ? Number(m[1]) : (r.year ?? undefined);
};

export const ERPQuotationListPage: React.FC = () => {
  const navigate = useNavigate();
  const { message, modal } = App.useApp();
  const { hasPermission } = useAuthGuard();
  // 2026-08-27：原本用 `projects:write` 守著，而那個名字**不存在於任何地方**
  //   （沒有角色擁有、兩份 SSOT 都沒有）⇒ 只有 superuser 看得到這些按鈕，
  //   admin 與業務同仁都看不到。
  //
  //   ⚠️ 改成 `projects:edit` **不會放寬任何 API 存取** ——
  //   這一頁對應的後端端點全部只有 `require_auth`（實測：quotations 5 支、
  //   pm/cases 1 支，零個 require_admin／require_permission）
  //   ⇒ 任何登入者本來就打得到那些 API。前端的守衛只是在隱藏入口，
  //   而它隱藏的對象包含本來就有權限的人。
  //
  //   為什麼是 `projects:edit`：它是最接近的**既有**權限（admin／staff／ops 擁有），
  //   而報價單與 PM 案件在資料模型上都掛在承攬案件之下（case_code 橋接）。
  //   「新增」動作刻意用同一個守衛而不是 `projects:create`（admin 專屬）——
  //   因為後端沒有做這個區分，前端多做一層會再製造一次「前後端不一致」。
  //
  //   ⚠️ 這是**過渡對齊**，不是最終答案。正解是 `quotations:*` / `pm:*` 自己的
  //   權限詞彙，那需要 owner 決定（A23 後續）。在那之前，這個對齊讓畫面
  //   與後端說同一件事。
  const canWrite = hasPermission('projects:edit');
  const [statFilter, setStatFilter] = useState<string | null>(null);
  // 卡片＝互動篩選（§2.6 ②）：點下去進查詢參數 card，再點取消；revenue 是分母、不篩
  const toggleCard = (key: 'revenue' | 'outstanding' | 'payable' | 'cost') => {
    const next = statFilter === key ? null : key;
    setStatFilter(next);
    setParams((p) => ({ ...p, card: next && next !== 'revenue' ? next : undefined, page: 1 }));
  };
  // 2026-09-04 owner：「專案帳款接續處理已承攬案件，不含非成案紀錄」——固定只列成案（後端預設 include_unawarded=false），
  // 「含未成案」開關已移除；未成案的報價單在各案件的「報價單」分頁處理。
  const [params, setParams] = useState<ERPQuotationListParams>({ page: 1, limit: 20, sort_by: 'case_code', sort_order: 'desc', year: CURRENT_YEAR });
  const { data, isLoading, isError, refetch } = useERPQuotations(params);
  // 選項與列表同一個年度／類別範圍——否則預設 2026 下 178 家有 84 家選了是空表（owner 09-04 晚）
  const { data: clientOptionsResp } = useERPQuotationClientOptions({ year: params.year, category: params.category });
  const clientOptions = clientOptionsResp?.data ?? [];
  // ⚠️ 統計卡必須跟著年度篩選走，否則會出現「列表 92 筆／卡片 257 筆」的
  // 不一致 —— 那比沒有年度篩選更糟：兩個數字都在畫面上，而使用者無從
  // 判斷哪一個才是他要的。後端 get_profit_summary 本來就收 year，
  // 是前端沒傳（同「送出的與收到的不一致」家族）。
  // 2026-09-04：統計卡跟著列表的年度＋關鍵字走（分母＝列表範圍）
  // 統計卡＝列表的分母：年度／關鍵字／類別／委託單位四個條件都跟（§2.6 ①；2026-09-04 前 api 層固定送空物件）
  const { data: profitSummary } = useERPProfitSummary({ year: params.year, search: params.search, category: params.category, client_name: params.client_name });
  // 2026-08-15：刪除改由詳情頁提供（對照 /documents 的導航設計），
  // 列表不再持有刪除能力，故 useDeleteERPQuotation 與 handleDelete 一併移除。

  // 前端過濾：僅顯示已承攬

  const columns: ResponsiveColumn<ERPQuotation>[] = [
    // 2026-09-03 owner：「配合總表調整核心資訊；填報者、舊案號非必要，落實線上報價單後也無舊案號呈現必要」。
    // 欄序照總表：年度／報價單編號／案名／客戶／承辦／報價日期／總價／狀態／收款／發票／毛利率。
    // 舊案號（B114-B002）不再呈現，但仍是搜尋鍵（列表搜尋涵蓋 legacy 與 QT 號）與匯入比對鍵。
    // 2026-09-04 owner 專案帳款頁改版：年度＝案件年度；名詞統一（成案編號／建案案號／委託單位）；
    // 欄位＝年度、成案編號、專案名稱、委託單位、承辦同仁、協力廠商、議價金額、應收帳款、應付帳款。
    // 2026-09-04 晚 owner「表格標頭無篩選排序機制」：§2.6 ④——漏斗不帶 onFilter（後端分頁），勾選值進 params；
    // 與工具列的下拉共用同一份 params，在哪邊改另一邊同步。排序 sort_by=case_code（CK{年}_ 前綴＝案件年度）。
    {
      title: '年度', dataIndex: 'case_code', key: 'case_code', width: 80, align: 'center', sorter: true,
      filters: YEAR_OPTIONS.map((y) => ({ text: y.label, value: y.value })), filterMultiple: false,
      filteredValue: params.year ? [params.year] : null,
      render: (_: unknown, r: ERPQuotation) => caseYear(r) ?? '—',
    },
    {
      title: '成案編號', dataIndex: 'project_code', key: 'project_code', sorter: true, width: 150,
      filters: [{ text: '01 委辦招標', value: '01' }, { text: '02 承攬報價', value: '02' }], filterMultiple: false,
      filteredValue: params.category ? [params.category] : null,
      render: (_: unknown, r: ERPQuotation) => (
        <Space direction="vertical" size={0}>
          <span>{r.project_code || <Text type="secondary">未成案</Text>}</span>
          {/* 舊制成案編號＝建案案號時不重複印（owner 09-04） */}
          {r.case_code && r.case_code !== r.project_code && (
            <Text type="secondary" style={{ fontSize: 11 }} title="建案案號">{r.case_code}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '專案名稱', dataIndex: 'case_name', key: 'case_name', sorter: true, ellipsis: true,
      render: (text: string | null) => <strong>{text ?? '-'}</strong>,
    },
    {
      title: '委託單位', dataIndex: 'client_name', key: 'client_name', width: 150, ellipsis: true,
      filters: clientOptions.map((c) => ({ text: `${c.name}（${c.count}）`, value: c.name })), filterMultiple: false, filterSearch: true,
      filteredValue: params.client_name ? [params.client_name] : null,
      render: (v?: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '承辦同仁', dataIndex: 'staff_name', key: 'staff_name', width: 120, ellipsis: true,
      render: (v: string | null) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '協力廠商', dataIndex: 'vendor_names', key: 'vendor_names', width: 170, hideOnMobile: true,
      render: (v?: string) => v ? (
        <Space size={[4, 4]} wrap>{v.split('、').map((n) => <Tag key={n} style={{ margin: 0 }}>{n}</Tag>)}</Space>
      ) : <Text type="secondary">—</Text>,
    },
    {
      title: termTitle('awarded_amount'), dataIndex: 'contract_amount', key: 'contract_amount', width: 130, align: 'right', sorter: true,
      // 2026-09-04 晚：顯示承攬金額＝議價金額（有）否則契約金額；有議價時把原契約金額印在下面，兩個數都看得到
      render: (v: string | number | null, r: ERPQuotation) => {
        const contract = v != null ? Number(v) : null;
        const winning = r.winning_amount != null && Number(r.winning_amount) > 0 ? Number(r.winning_amount) : null;
        const shown = winning ?? contract ?? (r.total_price != null ? Number(r.total_price) : null);
        if (shown == null) return '-';
        return (
          <Space direction="vertical" size={0} style={{ alignItems: 'flex-end' }}>
            <span title={winning != null ? '議價金額（含稅）' : contract != null ? '契約金額（含稅，無議價）' : '尚未成案，顯示報價總價（含稅）'}>
              {shown.toLocaleString()}{winning != null && <Tag color="purple" style={{ marginInlineStart: 4 }}>議價</Tag>}{contract == null && <Text type="secondary" style={{ fontSize: 11, marginInlineStart: 4 }}>報價</Text>}
            </span>
            {winning != null && contract != null && winning !== contract && (
              <Text type="secondary" style={{ fontSize: 11 }} title="契約金額（原報價）">原 {contract.toLocaleString()}</Text>
            )}
          </Space>
        );
      },
    },
    {
      title: termTitle('receivable_column'), key: 'receivable', width: 130, align: 'right',
      render: (_: unknown, r: ERPQuotation) => {
        const billed = Number(r.total_billed ?? 0); const received = Number(r.total_received ?? 0);
        if (!billed) return <Tag color="orange">未開請款</Tag>;
        const pct = Math.round((received / billed) * 100);
        return (
          <Space direction="vertical" size={0} style={{ alignItems: 'flex-end' }}>
            <span>{billed.toLocaleString()}</span>
            <Tag color={pct >= 100 ? 'green' : pct > 0 ? 'gold' : 'orange'} style={{ margin: 0 }}>
              {pct >= 100 ? '已收齊' : pct > 0 ? `已收 ${pct}%` : '待收'}
            </Tag>
          </Space>
        );
      },
    },
    {
      // 2026-09-05 owner「請在應收帳款增列應付款項」：此前這欄 hideOnMobile，窄螢幕看不到 ⇒ 常駐；名稱與卡片一致「應付款項」
      title: termTitle('payable_column'), key: 'payable', width: 130, align: 'right',
      render: (_: unknown, r: ERPQuotation) => {
        const payable = Number(r.total_payable ?? 0); const paid = Number(r.total_paid ?? 0);
        if (!payable) return <Text type="secondary">—</Text>;
        const pct = Math.round((paid / payable) * 100);
        return (
          <Space direction="vertical" size={0} style={{ alignItems: 'flex-end' }}>
            <span>{payable.toLocaleString()}</span>
            <Tag color={pct >= 100 ? 'green' : pct > 0 ? 'gold' : 'default'} style={{ margin: 0 }}>
              {pct >= 100 ? '已付清' : pct > 0 ? `已付 ${pct}%` : '未付'}
            </Tag>
          </Space>
        );
      },
    },
    // 2026-08-15 移除「操作」欄（詳情／編輯／刪除）。
    // 對照 `/documents` 列表：它沒有操作欄 —— 點列進詳情，所有操作在詳情頁。
    // 這三顆在報價詳情頁本來就有，列表這一欄是重複的；
    // 而且每一顆都要 stopPropagation 才不會和點列進詳情打架，
    // 那個 stopPropagation 本身就是「這一欄不該在這裡」的訊號。
    // 點列進詳情由下方 onRow 提供。
  ];


  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          {/* 2026-08-27 階段 1（QUOTATION_PHASE_POSITIONING §5）：
              標題原本是「財務管理 (ERP)」，而這一頁七成的內容是**還沒確認承攬**的報價
              （256 張裡 178 張對應的 PM 案件沒有 project_code）。
              ERP 是確認承攬「之後」的程序，用它當標題等於把位階講反了。
              選單同步移到「專案管理」底下並更名為「報價單總覽」。
              ⚠️ 路由與 API 前綴**刻意不動**（階段 2 才處理，且需 owner 先定階段 0 判準）。

              2026-08-29 owner：「報價單總覽改為專案帳款，隸屬專案財務群組下，
              統整專案財務紀錄」⇒ 導覽項 id 57 由「專案管理」(33) 移入
              「專案財務」(95)，與委託帳款／協力帳款同群，並排在第一
              （它是統整視圖，另兩者是分視角）。
              ⚠️ **路由仍是 `/erp/quotations`** —— 改路由要動書籤與既有連結，
              而更名的目的是講清楚它是什麼，不是換位址。*/}
          <Col>
            <Title level={3} style={{ margin: 0 }}>專案帳款</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              跨案件的財務統整 —— 建立與線上填寫明細請至各案件的「邀標報價」頁
            </Text>
          </Col>
          <Col>
            {/* 2026-08-27 owner：「/erp/quotations 首頁也不應該有新增報價鈕，
                都要在邀標報價程序」⇒ 建立入口只留在 PM 案件頁。

                ⚠️ 刻意留一個**指路**而不是整個拿掉：這一頁一直是大家找報價的地方，
                按鈕忽然不見會變成「功能沒了」而不是「換地方了」——
                本專案已經有過同型（空清單退化成數字、標案查無資料沒說出真正原因）。
                它是連結不是動作，不受 canWrite 影響（找路不需要權限）。 */}
            <Button
              type="link"
              icon={<PlusOutlined />}
              onClick={() => navigate(ROUTES.PM_CASES)}
            >
              新增報價請至「邀標報價案件」
            </Button>
          </Col>
        </Row>
        {/* 2026-09-04 晚 owner：卡片依序＝應收總額（未稅）／應收未收／應付款項／成本總額。
            「毛利」先隱藏——各頁毛利的計算口徑尚未統一（報價成本欄 vs 應付 vs 核銷，三者相加會重複，見 FIELD_SEMANTICS）。
            統一口徑後再放回，statFilter 'profit' 的篩選邏輯保留。 */}
        {profitSummary && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title={termTitle('contract_amount_sum')}
                value={Number(profitSummary.total_awarded ?? profitSummary.total_revenue).toLocaleString()}
                icon={<DollarOutlined />}
                color="#1890ff"
                active={statFilter === 'revenue'}
                onClick={() => toggleCard('revenue')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title={termTitle('outstanding')}
                value={Number(profitSummary.total_outstanding).toLocaleString()}
                icon={<ExclamationCircleOutlined />}
                color="#ff4d4f"
                active={statFilter === 'outstanding'}
                onClick={() => toggleCard('outstanding')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title={termTitle('payable_total')}
                value={Number(profitSummary.total_payable ?? 0).toLocaleString()}
                icon={<FundOutlined />}
                color="#722ed1"
                active={statFilter === 'payable'}
                onClick={() => toggleCard('payable')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title={termTitle('cost_total')}
                value={Number(profitSummary.total_cost).toLocaleString()}
                icon={<BankOutlined />}
                color="#faad14"
                active={statFilter === 'cost'}
                onClick={() => toggleCard('cost')}
              />
            </Col>
          </Row>
        )}
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        {/* 2026-09-05 owner：手機上這一列佔了 1/3 螢幕 ⇒ 改 FilterBar：只常駐搜尋框，篩選與操作收進「篩選」鈕 */}
        <FilterBar
          summary={(
            <Input.Search
                        placeholder="搜尋成案編號／建案案號／專案名稱"
                        allowClear
                        onSearch={(v) => setParams((p) => ({ ...p, search: v || undefined, page: 1 }))}
                        style={{ width: 240 }}
                      />
          )}
          activeCount={[params.category, params.client_name, params.card].filter(Boolean).length + (params.year ? 0 : 1)}
        >
          <Select
            value={params.year ?? 0}
            onChange={(v) => setParams((p) => ({ ...p, year: v || undefined, page: 1 }))}
            options={YEAR_OPTIONS}
            style={{ width: 130 }}
            aria-label="年度"
          />
          {/* 2026-09-02：後端 08-31 加了 include_unawarded（預設只給已成案），前端從沒接
              ⇒ 剛新建、尚未成案的報價單在這頁永遠看不到。owner 實測「CCC」找不到即此。
              端點實測：預設 0 筆、帶 true 1 筆、export-document 回 200 —— 輸出本身是好的，
              是「列表看不到 ⇒ 進不了詳情 ⇒ 按不到輸出」。半接通：後端有、前端沒傳、沒人報錯。 */}
          <Select

            placeholder="計畫類別" allowClear style={{ width: 130 }} value={params.category}

            onChange={(v) => setParams((p) => ({ ...p, category: v || undefined, page: 1 }))}

            options={[{ value: '01', label: '01 委辦招標' }, { value: '02', label: '02 承攬報價' }]}

          />

          <Select
            placeholder="委託單位" allowClear showSearch style={{ width: 220 }} value={params.client_name}
            optionFilterProp="label"
            onChange={(v) => setParams((p) => ({ ...p, client_name: v || undefined, page: 1 }))}
            options={clientOptions.map((c) => ({ value: c.name, label: `${c.name}（${c.count}）` }))}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
          <Button
            icon={<FileExcelOutlined />}
            onClick={async () => {
              try {
                const blob = await erpQuotationsApi.exportExcel({ year: params.year });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'erp_quotations.xlsx';
                a.click();
                URL.revokeObjectURL(url);
                message.success('匯出成功');
              } catch (e) { message.error(getErrorMessage(e, '匯出失敗'), 8); }
            }}
           title="匯出目前篩選範圍的彙整表（38 欄，與範本、匯入同一份表頭）">匯出彙整表</Button>
          {canWrite && (
            <>
              {/* 2026-09-04 晚 owner：已有匯出／匯入彙整表（同一份表頭、可往返），「下載空白範本」冗餘，移除。 */}
              {/* owner 2026-08-19：「若線上產出報價單未完全上線前，如何匯入與管理
                  既有 XLS 為目前階段重點」「新增與更新整合為一個按鍵鈕」。
                  依舊案號（B114-B002）upsert —— 有就更新、沒有就新增，
                  使用者不需要先知道 277 列裡哪些已在系統。
                  按下去**先預覽再確認**：這是第一次把數百筆業務資料寫進系統。 */}
              <Upload
                accept=".xlsx"
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    message.loading({ content: '解析中...', key: 'legacy' });
                    const p = await erpQuotationsApi.importLegacy(file, true);
                    message.destroy('legacy');
                    modal.confirm({
                      title: '匯入既有報價單彙整',
                      width: 560,
                      content: (
                        <div>
                          <p>共讀到 <b>{p.total_rows}</b> 列：</p>
                          <ul>
                            <li>將<b>新增 {p.will_create}</b> 筆</li>
                            <li>將<b>更新 {p.will_update}</b> 筆（依舊案號比對到既有資料）</li>
                            {p.skipped > 0 && <li>略過 {p.skipped} 筆（檔案內重複或缺案名）</li>}
                          </ul>
                          {/* 2026-08-27：08-20 那次匯入靜靜建出 26 件分身 ——
                              既有 `B114-B003`、彙整表帶 `B114-B003-0`，
                              case_code 不同故判為「不存在」而再建一件。
                              事後查證那 26 組兩側**案名完全相同**，且有碼那一側全部都有金流。
                              ⚠️ 只提醒不阻擋：實測另有 4 組同形態但案名完全不同
                              （B114-B026「平鎮區查估」vs B114-B026-0「永翠76透地雷達」），
                              合併與否要看案名與金額語意，是人的判斷。 */}
                          {(p.duplicate_candidate_count ?? 0) > 0 && (
                            <Alert
                              type="warning"
                              showIcon
                              style={{ marginBottom: 8 }}
                              message={`有 ${p.duplicate_candidate_count} 筆可能是既有案件的分身`}
                              description={
                                <div>
                                  <div style={{ marginBottom: 4 }}>
                                    這些新案號與既有案件<b>只差版次尾碼，且案名完全相同</b>：
                                  </div>
                                  {(p.duplicate_candidates ?? []).slice(0, 5).map((d) => (
                                    <div key={d.new_case_code} style={{ fontSize: 12 }}>
                                      · <b>{d.new_case_code}</b> ← 既有 {d.existing_case_code}
                                      {' '}— {d.case_name}
                                    </div>
                                  ))}
                                  {(p.duplicate_candidate_count ?? 0) > 5 && (
                                    <div style={{ fontSize: 12 }}>
                                      …其餘 {(p.duplicate_candidate_count ?? 0) - 5} 筆
                                    </div>
                                  )}
                                  <div style={{ marginTop: 4 }}>
                                    仍會建立（系統不自動合併）——確認是同一件的話，匯入後請自行處理。
                                  </div>
                                </div>
                              }
                            />
                          )}
                          {(p.skipped_detail?.length ?? 0) > 0 && (
                            <Alert type="warning" showIcon message="略過明細"
                              description={p.skipped_detail!.slice(0, 5)
                                .map(x => `${x.legacy_no}：${x.reason}`).join('；')} />
                          )}
                        </div>
                      ),
                      okText: '確認寫入', cancelText: '取消',
                      onOk: async () => {
                        const r = await erpQuotationsApi.importLegacy(file, false);
                        message.success(`匯入完成：新增 ${r.created} 筆、更新 ${r.updated} 筆`);
                        refetch();
                      },
                    });
                  } catch {
                    message.destroy('legacy');
                    message.error('彙整表解析失敗');
                  }
                  return false;
                }}
              >
                <Button icon={<FileExcelOutlined />} title="上傳彙整表（與匯出／範本同格式）：依舊案號或報價單編號比對，有就更新、沒有就新增；先預覽再寫入">匯入彙整表</Button>
              </Upload>
              {/* owner 2026-08-19：「產生報價單只是步驟一，其需將客戶回簽檔案
                  上傳確認才正式完成邀標報價承攬」。
                  檔名就是對應關係：回簽報價單_<舊案號>_<客戶>_<標的>_<項目>.pdf
                  ⚠️ 相依：要先匯入彙整表（系統才有舊案號可比對），
                  否則會全部回報「找不到舊案號」—— 訊息會講清楚，不會靜靜跳過。 */}
              <Upload
                accept=".pdf"
                multiple
                showUploadList={false}
                beforeUpload={() => false}
                onChange={async (info) => {
                  // AntD 的 originFileObj 型別是 RcFile（File 的子型別，多了 uid），
                  // 這裡只需要當成 File 傳給 FormData
                  const files: File[] = info.fileList
                    .map((f) => f.originFileObj)
                    .filter(Boolean) as unknown as File[];
                  if (files.length !== info.fileList.length) return;
                  try {
                    message.loading({ content: '比對中...', key: 'signed' });
                    const p = await erpQuotationsApi.importSigned(files, true);
                    message.destroy('signed');
                    modal.confirm({
                      title: '匯入客戶回簽報價單',
                      width: 620,
                      content: (
                        <div>
                          <p>共 <b>{p.total_files}</b> 個檔案：</p>
                          <ul>
                            <li>可掛回 <b>{p.will_attach}</b> 份</li>
                            {p.unmatched > 0 && <li>對不上 {p.unmatched} 份</li>}
                          </ul>
                          {(p.unmatched_detail?.length ?? 0) > 0 && (
                            <Alert type="warning" showIcon message="對不上的檔案"
                              description={
                                <ul style={{ margin: 0, paddingLeft: 18 }}>
                                  {p.unmatched_detail!.slice(0, 5).map((u) => (
                                    <li key={u.file_name}>{u.file_name}：{u.reason}</li>
                                  ))}
                                </ul>
                              } />
                          )}
                        </div>
                      ),
                      okText: '確認掛回', cancelText: '取消',
                      okButtonProps: { disabled: p.will_attach === 0 },
                      onOk: async () => {
                        const r = await erpQuotationsApi.importSigned(files, false);
                        message.success(`回簽掛回完成：${r.attached} 份`);
                        refetch();
                      },
                    });
                  } catch {
                    message.destroy('signed');
                    message.error('回簽檔解析失敗');
                  }
                }}
              >
                <Button icon={<UploadOutlined />} title="批次上傳回簽 PDF：檔名含舊案號（B115-C017-0）、報價單編號（QT2026_063）或案號（CK2026_PM_02_083）任一即可對應；先預覽再寫入。單一案件也可到案件頁的報價單分頁上傳">批次匯入回簽 PDF</Button>
              </Upload>
            </>
          )}
        </FilterBar>

        <EnhancedTable<ERPQuotation>
          columns={columns}
          // 2026-09-05 RWD：手機改卡片——主鍵／案名／委託單位／承攬同仁／金額三欄都在卡上，不再因窄而藏
          mobileCard={(r) => {
            const winning = r.winning_amount != null && Number(r.winning_amount) > 0 ? Number(r.winning_amount) : null;
            const awarded = winning ?? (r.contract_amount != null ? Number(r.contract_amount) : null) ?? (r.total_price != null ? Number(r.total_price) : null);
            const billed = Number(r.total_billed ?? 0); const received = Number(r.total_received ?? 0); const payable = Number(r.total_payable ?? 0);
            return (
              <MobileCard
                title={<>{r.project_code || r.case_code}{caseYear(r) ? <Text type="secondary" style={{ marginInlineStart: 6 }}>{caseYear(r)}</Text> : null}</>}
                subtitle={r.case_name ?? '-'}
                tags={[...(winning != null ? [{ text: '議價', color: 'purple' }] : []), ...(r.project_code ? [] : [{ text: '未成案', color: 'default' }])]}
                rows={[{ label: '委託單位', value: r.client_name }, { label: '承辦同仁', value: r.staff_name }, { label: '協力廠商', value: r.vendor_names }]}
                amounts={[
                  { label: '承攬金額（含稅）', value: fmtMoney(awarded) },
                  { label: '應收帳款', value: billed ? `${fmtMoney(billed)}${received >= billed ? '（已收齊）' : received > 0 ? `（已收 ${Math.round(received / billed * 100)}%）` : '（待收）'}` : '未開請款', tone: billed && received < billed ? 'warn' : 'default' },
                  { label: '應付款項', value: payable ? fmtMoney(payable) : '—' },
                ]}
                onClick={() => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(r.id)))}
              />
            );
          }}
          dataSource={data?.items ?? []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: params.page,
            pageSize: params.limit,
            total: data?.pagination?.total ?? 0,
            onChange: (page, pageSize) => setParams((p) => ({ ...p, page, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
          }}
          // 表頭排序交給後端（2026-09-01）。
          //
          // 這一頁是伺服器分頁 ⇒ `EnhancedTable` 會剝掉前端的排序比較器
          // （它只看得到當前這一頁，會給出看起來合理的錯答案）。
          // 但**剝掉不等於修好** —— 09-01 04:15 的 `SelfAudit-Flow` 就抓到
          // 「/erp/quotations 表格沒有排序圖示」而失敗，同一支檢核的
          // `--role user` 卻通過（該身分只有 6 張報價單、全量在手 ⇒ 不算伺服器分頁）。
          // 檢核抓對了：我拿掉了錯的排序，卻沒有補上對的。
          //
          // 只有真欄位標 `sorter: true`。承辦同仁／填報者／毛利／毛利率
          // 都是**聚合出來的**，走這條路徑排序會靜靜地照 `id` 排。
          onChange={(_p, filters, sorter) => {
            const sd = Array.isArray(sorter) ? sorter[0] : sorter;
            const field = typeof sd?.field === 'string' ? sd.field : undefined;
            // 表頭篩選也送進查詢參數（伺服器端篩選）。取消篩選時要送 undefined，
            // 不能留空字串 —— API 層是 truthy 判斷，空字串會被丟掉而看起來像沒改。
            const st = filters?.status?.[0];
            const first = (k: string) => { const v = filters?.[k]; return Array.isArray(v) && v.length ? v[0] : undefined; };
            const yr = first('case_code'); const cat = first('project_code'); const client = first('client_name');
            // 議價金額不是報價單欄位（承攬案合約額）；後端排序只認報價單欄位 ⇒ 用報價總價代替
            const sortField = field === 'contract_amount' ? 'total_price' : field;
            setParams((prev) => ({
              ...prev,
              status: typeof st === 'string' ? st : undefined,
              year: typeof yr === 'number' ? yr : undefined,
              category: typeof cat === 'string' ? cat : undefined,
              client_name: typeof client === 'string' ? client : undefined,
              sort_by: sortField && sd?.order ? sortField : 'case_code',
              sort_order: sortField && sd?.order ? (sd.order === 'ascend' ? 'asc' : 'desc') : 'desc',
              page: 1,
            }));
          }}
          onRow={(record) => ({
            onClick: () => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.id))),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1000 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPQuotationListPage;
