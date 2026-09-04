/**
 * 經費名詞字典（UI 端 SSOT）—— 2026-09-04 owner：「各類經費名詞或定義請增列註記補充，以利釐清對應與語意」。
 *
 * 每個名詞：顯示文字＋一句定義（來源欄位、含稅／未稅、與其他名詞的關係）。
 * 統計卡、欄位標題一律用 `termTitle(key)` 產生「文字＋ⓘ tooltip」，不再各頁自己寫字串——
 * 同一個數字曾經有三個名字（合約總額／議價金額／契約金額），就是各頁各寫一份的後果。
 *
 * 文件端對照表＝ docs/architecture/FIELD_SEMANTICS.md「經費名詞字典」；改這裡要同步改那裡。
 */
import React from 'react';
import { Tooltip } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';

export interface FinanceTerm {
  label: string;
  note: string;
}

export const FINANCE_TERMS = {
  // ── 契約／報價 ──
  contract_amount: {
    label: '契約金額',
    note: '承攬案 contract_projects.contract_amount，含稅：成案時的報價（投標）金額。決標後若有議價，實際承攬金額是「議價金額」。舊稱「合約總額」。',
  },
  winning_amount: {
    label: '議價金額',
    note: '承攬案 winning_amount，含稅：決標／議價後的實際承攬金額。只有 01 委辦招標有議價程序（必填）；02 承攬報價顯示「—」、承攬金額＝契約金額。',
  },
  awarded_amount: {
    label: '承攬金額（含稅）',
    note: '＝議價金額，沒有議價則＝契約金額（含稅）。所有應收面的數字都用這個。',
  },
  contract_amount_sum: {
    label: '承攬金額（含稅）',
    note: '篩選範圍內所有承攬案的承攬金額（議價金額→契約金額→報價總價）加總，含稅。承攬案頁與專案帳款頁同一個名字、同一個算法、同一個數（owner 09-05 統一）；未稅＝÷1.05。',
  },
  quotation_total: {
    label: '報價總價（含稅）',
    note: 'erp_quotations.total_price，含稅；請款、發票都以它為上限。未稅＝總價 − 稅額。',
  },
  receivable_total_untaxed: {
    label: '應收總額（未稅）',
    note: '同上但扣掉稅額（總價 − 稅額）。畫面統一以含稅呈現，此鍵保留給報表。',
  },
  // ── 應收 ──
  billed: {
    label: '已請款',
    note: '各期請款金額（erp_billings.billing_amount）加總，含稅；成案時自動建第一期＝承攬金額（議價金額，無則報價總價）。',
  },
  unbilled: {
    label: '未請款',
    note: '報價總價 − 已請款，含稅。',
  },
  received: {
    label: '已收款',
    note: '已收款的請款實收金額（erp_billings.payment_amount）加總，含稅。',
  },
  outstanding: {
    label: '應收未收',
    note: '已請款 − 已收款，含稅。列表頁點此卡只列有未收餘額的案。',
  },
  receivable_column: {
    label: '應收帳款',
    note: '該案已請款合計（含稅）＋已收比例；「未開請款」＝一筆請款都沒有。',
  },
  receipt_rate: {
    label: '收款率',
    note: '已收款 ÷ 已請款。',
  },
  // ── 應付 ──
  payable_total: {
    label: '應付款項',
    note: '協力廠商應付（erp_vendor_payables.payable_amount）加總，含稅；承攬案協力廠商分頁的指派金額會自動建一筆（指派即應付）。',
  },
  payable_column: {
    label: '應付帳款',
    note: '該案應付合計（含稅）＋已付比例；「—」＝沒有協力廠商應付。',
  },
  paid_total: {
    label: '已付',
    note: '應付中已付款的金額（paid_amount）加總，含稅。',
  },
  payable_outstanding: {
    label: '未付餘額',
    note: '應付 − 已付，含稅。',
  },
  payment_rate: {
    label: '付款率',
    note: '已付 ÷ 應付。',
  },
  // ── 成本／毛利 ──
  cost_total: {
    label: '成本總額',
    note: '報價單估列成本：外包費＋人事費＋管銷費＋其他成本（erp_quotations 四欄），未稅。不是實際支出。',
  },
  cost_estimated: {
    label: '估列成本（報價單）',
    note: '同「成本總額」：報價時估的四項成本，未稅。',
  },
  cost_actual: {
    label: '實際成本（已入帳）',
    note: '帳本支出：協力廠商應付已付款＋費用核銷入帳的合計。應付與核銷是帳本的鏡像，三者相加會重複計算。',
  },
  gross_profit: {
    label: '預估毛利',
    note: '（報價總價 − 稅額）− 估列成本。各頁口徑尚未統一，列表頁的毛利卡先隱藏。',
  },
  gross_margin: {
    label: '預估毛利率',
    note: '預估毛利 ÷ 未稅營收。',
  },
  // ── 發票 ──
  invoice_amount: {
    label: '發票金額',
    note: 'erp_invoices.amount，含稅（銷售額＋稅額）；一筆請款一張票，發票額不得超過該期請款。',
  },
} as const satisfies Record<string, FinanceTerm>;

export type FinanceTermKey = keyof typeof FINANCE_TERMS;

/** 「文字＋ⓘ」——給統計卡 title、欄位 title、Statistic title 用 */
export function termTitle(key: FinanceTermKey, override?: string): React.ReactNode {
  const t = FINANCE_TERMS[key];
  return (
    <span>
      {override ?? t.label}
      <Tooltip title={t.note}>
        <InfoCircleOutlined style={{ marginInlineStart: 4, color: '#8c8c8c', fontSize: 12 }} />
      </Tooltip>
    </span>
  );
}

/** 純文字（給 placeholder、訊息） */
export function termLabel(key: FinanceTermKey): string {
  return FINANCE_TERMS[key].label;
}
