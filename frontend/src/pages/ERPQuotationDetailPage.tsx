/**
 * ERP 報價詳情頁面 — 統一 DetailPageLayout 模板
 *
 * 與 documents、pm-cases、contract-cases 共用佈局/標頭/Tab。
 * 採導航模式編輯（navigate to edit page），非 inline。
 *
 * @version 2.0.0 — 遷移至 DetailPageLayout
 */
import React from 'react';
import { termTitle } from '../constants/financeTerms';
import {
  Button, Descriptions, Statistic, Row, Col, Card, Alert, Popconfirm, App, Typography,
  } from 'antd';
import {
  EditOutlined, DeleteOutlined, DollarOutlined,
  InfoCircleOutlined, BankOutlined,
} from '@ant-design/icons';
import { FileTextOutlined, ProfileOutlined, PaperClipOutlined } from '@ant-design/icons';
import { QuotationItemsTab } from './erpQuotation';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useERPQuotation, useAuthGuard } from '../hooks';
import { AccountRecordTab } from './erpQuotation/AccountRecordTab';
import ExpensesTab from './erpQuotation/ExpensesTab';
import { AttachmentPanel } from '../components/common/AttachmentPanel';
import { ROUTES } from '../router/types';
import { queryKeys } from '../config/queryConfig';
import { apiClient } from '../api/client';
import { ERP_ENDPOINTS } from '../api/endpoints';

import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';
import { ExpenseQRButton } from '../components/common/ExpenseQRCode';
import { getErrorMessage } from '../utils/apiErrorParser';

const { Text } = Typography;

const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿', color: 'default' },
  { value: 'confirmed', label: '已確認', color: 'success' },
  { value: 'revised', label: '修訂中', color: 'warning' },
  { value: 'closed', label: '已結案', color: 'default' },
];

export const ERPQuotationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { message } = App.useApp();
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
  const { data: quotation, isLoading } = useERPQuotation(id ? Number(id) : null);
  // ⚠️ 必須在早退（`if (!quotation && !isLoading) return`）**之前** ——
  // exporting / pdfUrl / pdfName 已移入 `useQuotationExport`（2026-08-27）

  // 報價明細筆數 —— 與 `QuotationItemsTab` **共用同一組 queryKey**，
  // 所以不會多打一次 API，而且那邊存檔後這裡的數字會一起更新。
  //
  // 為什麼詳情頁需要知道：實測 256 張報價單**沒有任何一張填過明細**，
  // 而輸出的報價單長這樣 —— 抬頭、客戶、案名都對，「項次／工作內容／
  // 數量／單價」整片空白。系統產出一張空表時一句話都沒說，
  // 使用者要等打開檔案才發現。
  // ⚠️ 這個 key 與 QuotationItemsTab／QuotationRecordsTab 共用（工廠 SSOT），
  // queryFn 的**回傳形狀必須與那兩處一致（解 .data）** ——
  // 2026-08-28 修正：原本回整包 SuccessResponse，詳情頁先載入時
  // 明細分頁從快取拿到錯的形狀 ⇒ 有明細也顯示空表（L39 家族）。
  const { data: itemsData } = useQuery({
    queryKey: queryKeys.erpQuotations.items(quotation?.id ?? 0),
    queryFn: async () => {
      const res = await apiClient.post<{ data?: { items?: unknown[] } }>(
        ERP_ENDPOINTS.QUOTATION_ITEMS_DETAIL, { quotation_id: quotation!.id },
      );
      return res?.data;
    },
    enabled: !!quotation?.id,
  });
  const itemCount = itemsData?.items?.length ?? 0;

  // ⚠️ Hook 必須在早退之前呼叫 —— 這一頁原本就有一段註解警告過同一件事
  //   （「放在早退之後會在『報價不存在』那條路徑上少呼叫一個 Hook」），
  //   而我抽共用時還是把它放到了早退後面，ESLint 當場擋下。
  // 2026-08-27（第二次修正）：**輸出報價單／輸出 PDF 已從本頁移除**。
  //
  // 我上一版做成「兩邊都有、共用同一支 hook」，而 owner 要的是**只在邀標報價**：
  //   「/erp/quotations/385 不應有輸出報價單與輸出 pdf 兩功能鈕，
  //     包含 /erp/quotations 首頁也不應該有新增報價鈕，都要在邀標報價程序」
  //
  // 抽共用是對的（四件事容易各自演化），但抽完仍留在這裡就不是他要的收斂：
  // **報價的產生與產出都屬於邀標報價流程，ERP 這一頁是財務視角的檢視。**
  // 唯一的輸出入口＝`/pm/cases/:id?tab=quotations`（`pmCase/QuotationRecordsTab`）。

  if (!quotation && !isLoading) {
    return <DetailPageLayout header={{ title: '報價不存在', backPath: ROUTES.ERP_QUOTATIONS }} tabs={[]} hasData={false} />;
  }

  const grossProfit = Number(quotation?.gross_profit ?? 0);

  const statusOpt = STATUS_OPTIONS.find(o => o.value === quotation?.status);

  const headerConfig = {
    title: quotation?.case_name ?? quotation?.case_code ?? '載入中...',
    // 2026-08-17：報價單號要看得到 —— 客戶回覆時引用的是「你們那張 QT-…」，
    // 不是我們內部的案號。版次 >1 才顯示（v1 是常態，標它只是噪音）。
    //
    // ⚠️ 這一行是「產出端完成但接收端沒接」的補救：單號在 08-17 就產好並回填
    // 78 筆，但 response schema 與前端型別都沒有它 → 使用者永遠看不到。
    subtitle: [
      quotation?.quotation_no,
      (quotation?.revision ?? 1) > 1 ? `rev ${quotation?.revision}` : null,
      quotation?.case_code,
    ].filter(Boolean).join('　'),
    icon: <DollarOutlined />,
    backPath: ROUTES.ERP_QUOTATIONS,
    backText: '返回列表',
    tags: statusOpt ? [{ text: statusOpt.label, color: statusOpt.color }] : [],
    extra: canWrite ? (
      <>
        {quotation?.case_code && (
          <ExpenseQRButton caseCode={quotation.case_code} caseName={quotation.case_name} />
        )}
        {/* 2026-08-27 owner（第二次指出）：「/erp/quotations/385 不應有
            輸出報價單與輸出 pdf 兩功能鈕 …… 都要在邀標報價程序」
            ⇒ **輸出鈕已從本頁移除**，唯一入口＝`/pm/cases/:id?tab=quotations`。

            那兩顆鈕的歷史（08-17／08-18／08-19 owner 三次要求、以及委辦招標
            不顯示的判準 `case_category !== '01'`）**沒有消失，只是搬家了** ——
            全部保留在 `pmCase/QuotationRecordsTab.tsx` 與 `useQuotationExport.tsx`。
            在這裡留這段是為了讓下一個想「ERP 這頁怎麼不能輸出」的人知道去哪找，
            而不是重新加一顆回來。 */}
        <Button type="primary" icon={<EditOutlined />}
          onClick={() => navigate(ROUTES.ERP_QUOTATION_EDIT.replace(':id', String(quotation?.id)))}
        >編輯</Button>
        <Popconfirm title="確定刪除此報價？" okText="確定" cancelText="取消"
          okButtonProps={{ danger: true }}
          onConfirm={async () => {
            try {
              const { erpQuotationsApi } = await import('../api/erp/quotationsApi');
              await erpQuotationsApi.delete(quotation!.id);
              message.success('報價已刪除');
              navigate(ROUTES.ERP_QUOTATIONS);
            } catch (e) { message.error(getErrorMessage(e, '刪除失敗'), 8); }
          }}
        >
          <Button danger icon={<DeleteOutlined />}>刪除</Button>
        </Popconfirm>
      </>
    ) : undefined,
  };

  const tabs = quotation ? [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '成本結構' }, (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {quotation.amount_mismatch && (
          <Alert
            type="warning"
            showIcon
            message={`PM 合約金額 (NT$ ${Number(quotation.pm_contract_amount ?? 0).toLocaleString()}) 與 ERP 報價總額不一致，請確認是否需要同步更新。`}
          />
        )}
        {/* 合約概況 */}
        {/* 2026-08-15：金額欄改為 lg 才分四欄。
            原本 sm={6}（≥576px 就四欄）—— 768px 扣掉側欄約 568px 可用，
            四欄各約 126px，而「22,675,000」在 24px 字級約需 132px，**必然裁切**。
            390px 時是兩欄（約 175px）所以行動觀測量不到 ——
            `pageOverflow: 0` 只代表文件沒被撐寬，**元素在固定寬度欄位裡被裁切不會撐寬文件**。
            這一類要靠真人看，或看下方 money-stat 的字級收斂。 */}
        {/* 金額字級收斂：AntD Statistic 預設 24px 不會隨欄寬縮小，
            長數字（22,675,000＝10 字元）在窄欄會被裁切。
            clamp 讓它在窄欄自動降到 16px，寬螢幕維持 24px。 */}
        <style>{`.money-stat .ant-statistic-content-value {
          font-size: clamp(16px, 2.2vw, 24px) !important;
          white-space: nowrap;
        }`}</style>
        <Card size="small" title="合約概況" className="money-stat">
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={12} lg={6}><Statistic title="合約總價" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
            {/* 2026-08-18 owner：「若可設定公司固定利潤如 10%，那總金額扣除前述
                才應該是專案毛利」。

                只在比率 > 0 時才顯示這一格：預設 0（不扣）時多一個「留成 0」
                只是噪音，而畫面上每多一個永遠是 0 的數字，就多一個訓練人略過它的東西。

                但比率一旦設了就**必須顯示** —— 否則毛利會莫名少一截而查不出
                是誰扣的，而「數字變了但看不出為什麼」比數字錯更難處理。 */}
            {Number(quotation.company_profit_rate ?? 0) > 0 && (
              <Col xs={12} sm={12} lg={6}>
                <Statistic
                  title={`公司留成（${(Number(quotation.company_profit_rate) * 100).toFixed(0)}%）`}
                  value={Number(quotation.company_reserve ?? 0)}
                  precision={0}
                  styles={{ content: { color: '#8c8c8c' } }}
                />
                <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4, lineHeight: 1.4 }}>
                  專案可用 {Number(quotation.project_base ?? 0).toLocaleString()} 元
                  <br />（毛利率的分母）
                </div>
              </Col>
            )}
            {/* 2026-08-15 owner：「報價單估列費用、實際成本、毛利皆由區分清楚不可混淆」。
                原本只有一個「估計成本」，看的人不知道那是報價時填的估列還是真的花掉的錢。
                三個數字各自標明基準：估列來自報價單、實際來自統一帳本、待入帳是填報缺口。 */}
            <Col xs={12} sm={12} lg={6}>
              <Statistic title={termTitle('cost_estimated')} value={Number(quotation.total_cost)} precision={0} />
            </Col>
            <Col xs={12} sm={12} lg={6}>
              <Statistic title={termTitle('cost_actual')} value={Number(quotation.actual_cost ?? 0)} precision={0} />
              {Number(quotation.pending_cost ?? 0) > 0 && (
                <div style={{ fontSize: 12, color: '#faad14', marginTop: 4, lineHeight: 1.4 }}>
                  另有 {Number(quotation.pending_cost).toLocaleString()} 元
                  <br />「應付未付＋核銷未入帳」
                </div>
              )}
            </Col>
            {/* 2026-08-15：成本未填時不得呈現毛利數字。
                後端 schema 把未填的成本存成 0，於是「沒填」與「真的是零」
                在資料裡分不出來，毛利率會顯示 100% —— 實測 77 筆報價有 37 筆
                落在這裡，其中最大一筆收入 943 萬。
                報一個 100% 比不報更糟：它看起來像結論。 */}
            {quotation.cost_declared === false ? (
              <Col xs={24} sm={12}>
                <Statistic title={termTitle('gross_profit')} value="—" />
                <div style={{ fontSize: 12, color: '#faad14', marginTop: 4 }}>
                  尚未填寫成本，無法計算毛利
                </div>
              </Col>
            ) : (
              <>
                <Col xs={12} sm={12} lg={6}><Statistic title={termTitle('gross_profit')} value={grossProfit} precision={0} styles={{ content: { color: grossProfit >= 0 ? '#3f8600' : '#cf1322' } }} /></Col>
                <Col xs={12} sm={12} lg={6}><Statistic title={termTitle('gross_margin')} value={quotation.gross_margin ? Number(quotation.gross_margin) : 0} suffix="%" precision={1} /></Col>
              </>
            )}
          </Row>
        </Card>

        {/* 應收/應付概況 */}
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            {/* 2026-08-29 owner：「/erp/quotations/161?tab=info 的未收款與
                ?tab=receivable 對不上」。查證：本頁「未收款」算的是
                **合約額 − 已收款**（16,935,000 − 1,020,000 = 15,915,000），
                而 receivable 分頁與 `/erp/client-accounts` 用的是
                **已請款 − 已收款**（＝應收帳款餘額 2,680,000）。
                同一個詞兩種算法，而標籤沒說是哪一種。

                改為全系統一致（已請款 − 已收款），並補「未請款」讓兩條
                等式在畫面上可驗算，合約額的資訊不會因此消失：
                  應收總額 = 已請款 + 未請款
                  已請款   = 已收款 + 未收款 */}
            <Card size="small" title="應收概況 (委託單位)">
              <Row gutter={[16, 8]}>
                <Col xs={12} sm={8} lg={4}><Statistic title={termTitle('quotation_total')} value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
                <Col xs={12} sm={8} lg={5}><Statistic title={termTitle('billed')} value={Number(quotation.total_billed)} precision={0} /></Col>
                <Col xs={12} sm={8} lg={5}><Statistic title={termTitle('unbilled')} value={Number(quotation.total_price ?? 0) - Number(quotation.total_billed)} precision={0} styles={{ content: { color: '#8c8c8c' } }} /></Col>
                <Col xs={12} sm={12} lg={5}><Statistic title={termTitle('received')} value={Number(quotation.total_received)} precision={0} styles={{ content: { color: '#52c41a' } }} /></Col>
                <Col xs={12} sm={12} lg={5}><Statistic title={termTitle('outstanding', '未收款')} value={Number(quotation.total_billed) - Number(quotation.total_received)} precision={0} styles={{ content: { color: Number(quotation.total_billed) > Number(quotation.total_received) ? '#ff4d4f' : '#52c41a' } }} /></Col>
              </Row>
              <Text type="secondary" style={{ fontSize: 12 }}>
                未請款＝合約額−已請款｜未收款＝已請款−已收款（應收帳款餘額，與委託單位帳款頁同一定義）
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card size="small" title="應付概況 (協力廠商)">
              <Row gutter={[16, 8]}>
                <Col xs={12} sm={12} lg={8}><Statistic title="應付總額" value={Number(quotation.total_payable)} precision={0} /></Col>
                <Col xs={12} sm={12} lg={8}><Statistic title="已付款" value={Number(quotation.total_paid)} precision={0} styles={{ content: { color: '#52c41a' } }} /></Col>
                <Col xs={12} sm={12} lg={8}><Statistic title="未付款" value={Number(quotation.total_payable) - Number(quotation.total_paid)} precision={0} styles={{ content: { color: Number(quotation.total_payable) > Number(quotation.total_paid) ? '#ff4d4f' : '#52c41a' } }} /></Col>
              </Row>
            </Card>
          </Col>
        </Row>

        {quotation.budget_limit && (
          <Alert
            type={quotation.is_over_budget ? 'error' : 'info'}
            message={`預算上限: ${Number(quotation.budget_limit).toLocaleString()} | 使用率: ${quotation.budget_usage_pct ?? '0'}%`}
            showIcon
          />
        )}

        {/* 損益分析 */}
        <Card size="small" title="損益分析">
          <Row gutter={[16, 8]}>
            <Col xs={12} sm={12} lg={6}><Statistic title="營收 (含稅)" value={Number(quotation.total_price ?? 0)} precision={0} /></Col>
            <Col xs={12} sm={12} lg={6}><Statistic title="稅額" value={Number(quotation.tax_amount)} precision={0} /></Col>
            <Col xs={12} sm={12} lg={6}><Statistic title="營收 (未稅)" value={Number(quotation.total_price ?? 0) - Number(quotation.tax_amount)} precision={0} /></Col>
            {/* 2026-08-15：原本這裡顯示「淨利」，而 net_profit 與 gross_profit
                是**同一個數字** —— 兩者並排會被讀成兩個不同的財務指標。
                真正的淨利要再扣營運費用與稅，那些資料不在報價這一層。
                改顯示「實際毛利」：以已入帳的實際成本為基準，與上方的預估毛利對照。 */}
            <Col xs={12} sm={12} lg={6}>
              <Statistic
                title="實際毛利（已入帳成本）"
                value={Number(quotation.total_price ?? 0) - Number(quotation.tax_amount) - Number(quotation.actual_cost ?? 0)}
                precision={0}
                styles={{ content: { color: '#1677ff' } }}
              />
              <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                僅計已入帳成本，與上方預估毛利基準不同
              </div>
            </Col>
          </Row>
          <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small" style={{ marginTop: 16 }}>
            <Descriptions.Item label="外包費">
              {Number(quotation.outsourcing_fee).toLocaleString()}
              {/* 2026-08-16：外包費與已建應付的落差。
                  實測 35 筆有應付的報價，**32 筆的外包費已經等於應付合計** ——
                  也就是有人在手動抄。剩下 3 筆沒抄，於是估列成本是 0
                  而應付已建 100 萬／200 萬／90 萬，毛利率顯示 100%。
                  **刻意不自動覆寫**：估列與實際是兩件事（owner 明確要求區分），
                  自動帶入會把「還沒估」與「估了剛好等於應付」混成一樣。
                  只把落差說出來，帶不帶入由人決定。 */}
              {Number(quotation.total_payable) > 0
                && Number(quotation.outsourcing_fee) !== Number(quotation.total_payable) && (
                <div style={{ fontSize: 12, color: '#faad14', marginTop: 4 }}>
                  已建應付 {Number(quotation.total_payable).toLocaleString()}
                  {Number(quotation.outsourcing_fee) === 0 ? '，但外包費尚未估列' : '，與估列不符'}
                </div>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="人事費">{Number(quotation.personnel_fee).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="管銷費">{Number(quotation.overhead_fee).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="其他成本">{Number(quotation.other_cost).toLocaleString()}</Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 合約明細 */}
        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small" title="合約資訊">
          <Descriptions.Item label="案號">{quotation.case_code}</Descriptions.Item>
          <Descriptions.Item label="案名">{quotation.case_name ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="年度">{quotation.year ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="狀態">{quotation.status}</Descriptions.Item>
          {/* owner 2026-08-21：「服務人員 等同 承辦同仁」。
              2026-09-03 owner：「填報者、舊案號非必要資訊；落實線上報價單後也無舊案號呈現必要」——
              兩欄自畫面移除。舊案號仍在資料表（匯入比對鍵、回簽 PDF 檔名比對），只是不呈現；
              填報者留在審計紀錄（audit_create）。 */}
          <Descriptions.Item label="承辦同仁">
            {quotation.staff_name ?? <span style={{ color: '#999' }}>—</span>}
          </Descriptions.Item>
          <Descriptions.Item label="報價單編號">
            {quotation.quotation_no ?? <span style={{ color: '#999' }}>—</span>}
          </Descriptions.Item>
          <Descriptions.Item label="備註" span={2}>{quotation.notes ?? '-'}</Descriptions.Item>
        </Descriptions>
      </div>
    )),
    // 2026-08-17 owner：「若是標案應無報價明細 tab 以及其填報效益」。
    // category 01=委辦招標（標案類）／02=承攬報價。
    // 標案涉及多項程序、不易逐項填列作業單價 —— 顯示一個填不了的分頁
    // 就是在要求對方做不可能的事（同「要求標案填成本」那個錯，同日已修）。
    // 未知類別時**仍顯示**：寧可多一個分頁，不要讓承攬報價案件失去它。
    ...(quotation.case_category === '01' ? [] : [
    // 2026-08-16 owner：「線上報價單機制」。
    // 報價的起點是逐項內容，成本是後面才拆的。
    createTabItem('items', { icon: <ProfileOutlined />, text: '報價明細', count: itemCount }, (
      // 2026-09-02 owner：「已承攬不應有報價明細編輯機制」——成案（有 project_code）即鎖定
      <QuotationItemsTab quotationId={quotation.id} caseName={quotation.case_name} caseCode={quotation.case_code}
        readOnly={!!quotation.project_code} />
    ))
    ]),
    createTabItem('receivable', { icon: <BankOutlined />, text: '應收帳款' }, (
      id ? <AccountRecordTab erpQuotationId={Number(id)} direction="receivable"
          clientName={(quotation as { client_name?: string })?.client_name} /> : null
    )),
    createTabItem('payable', { icon: <DollarOutlined />, text: '應付帳款' }, (
      id ? <AccountRecordTab erpQuotationId={Number(id)} direction="payable" /> : null
    )),
    createTabItem('expenses', { icon: <FileTextOutlined />, text: '費用核銷' }, (
      quotation?.case_code ? <ExpensesTab caseCode={quotation.case_code} /> : null
    )),
    // 2026-08-19 owner：「每筆報價單呈現可參照公文模式提供上傳與預覽機制，
    // 統一整體系統呈現與程式維護，降低異質同工機制」。
    //
    // 用共用的 AttachmentPanel（抽自 pmCase/QuotationRecordsTab，那是盤點
    // 全前端 9 處附件實作後唯一四項功能齊全的一份）——不另寫第 10 份。
    //
    // 附件以 case_code 關聯，與 PM 案件的報價紀錄**是同一批檔案**：
    // 系統輸出的報價單（archive 自動標 generated_quotation）與客戶回簽
    // （匯入時標 signed_quotation）都在這裡看得到。
    createTabItem('attachments', { icon: <PaperClipOutlined />, text: '附件' }, (
      quotation?.case_code
        ? <AttachmentPanel
            caseCode={quotation.case_code}
            isEditing={canWrite}
            title="報價單附件"
            uploadTitle="上傳附件"
            showDocType
          />
        : null
    )),
  ] : [];

  return (
    <>
      <DetailPageLayout
        header={headerConfig}
        tabs={tabs}
        loading={isLoading}
        hasData={!!quotation}
      />
    </>
  );
};

export default ERPQuotationDetailPage;
