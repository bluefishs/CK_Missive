/**
 * Regression — 財務清單「看得到卻點不進去」防回歸（2026-07-31）
 *
 * 事故：owner 兩度回報「費用核銷已核准但無法檢視該紀錄」。
 * 07-30 只修了 pages/pmCase/ExpensesTab.tsx，但 owner 實際在看的
 * /erp/quotations/:id 用的是 pages/erpQuotation/ExpensesTab.tsx（同名不同檔）
 * → 漏修 → 症狀完全沒變 =「改錯檔」家族再現。
 *
 * 且該檔的「編輯」按鈕受 canEdit（pending/rejected）限制，
 * verified 的紀錄整列沒有任何可點的東西 —— 這是最容易漏掉的邊角：
 * 開發時看到的多是 pending 紀錄，核准後才失去入口。
 *
 * 本測試以**檔案集合**為單位驗證，避免「修一個、漏一個」：
 * 任何呈現 FinanceRecord 的元件都必須提供無條件的鑽取入口。
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (name === 'node_modules' || name === '__tests__') continue;
      walk(p, acc);
    } else if (name.endsWith('.tsx')) {
      acc.push(p);
    }
  }
  return acc;
}

/** 呈現 FinanceRecord 清單的元件（動態掃描，不寫死清單 → 新增第三個也會被納管） */
function financeListComponents(): { path: string; src: string }[] {
  return walk(SRC)
    .map((p) => ({ path: p, src: readFileSync(p, 'utf-8') }))
    .filter(({ src }) =>
      src.includes('FinanceRecord') &&
      (src.includes('EnhancedTable') || src.includes('<Table')),
    );
}

describe('財務清單必須可鑽取', () => {
  it('至少掃到兩個財務清單元件（掃描器本身沒壞）', () => {
    const comps = financeListComponents();
    expect(comps.length).toBeGreaterThanOrEqual(2);
  });

  it.each(financeListComponents().map((c) => c.path))(
    '%s 提供進入核銷詳情的入口',
    (path) => {
      const src = readFileSync(path, 'utf-8');
      expect(
        src.includes('ERP_EXPENSE_DETAIL'),
        `${path} 呈現財務紀錄卻沒有任何導向 ERP_EXPENSE_DETAIL 的路徑`,
      ).toBe(true);
    },
  );

  it('erpQuotation/ExpensesTab 的鑽取入口不得被 canEdit 限制', () => {
    const raw = readFileSync(join(SRC, 'pages/erpQuotation/ExpensesTab.tsx'), 'utf-8');
    // 必須先剝除註解才能比對位置。
    // （本測試初版忘了剝除，結果比對到說明用註解裡的「檢視」二字 → 負向測試證實為假綠，
    //   即「測試自己也會沉默成功」。修法：只看實際程式碼。）
    const src = raw
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/^\s*\/\/.*$/gm, '');

    const idx = src.indexOf("title: '操作'");
    expect(idx).toBeGreaterThan(0);
    const actions = src.slice(idx, idx + 2000);

    const detailIdx = actions.indexOf('ERP_EXPENSE_DETAIL');
    const canEditIdx = actions.indexOf('{canEdit');
    expect(detailIdx, '操作欄沒有任何導向核銷詳情的按鈕').toBeGreaterThan(0);
    expect(canEditIdx, '找不到 canEdit 條件式（元件結構已變，請更新本測試）').toBeGreaterThan(0);
    // 第一個鑽取入口必須出現在第一個 canEdit 條件之前 → 代表它不在條件式內
    expect(
      detailIdx < canEditIdx,
      '鑽取入口被包在 canEdit 條件內：verified（已核准）紀錄將再次失去入口',
    ).toBe(true);
  });
});

describe('財務型別 SSOT', () => {
  // 2026-07-31：兩個 ExpensesTab 原本各自宣告 FinanceRecord / CaseFinanceData，
  // 後端 case-finance 端點又回未綁 response_model 的裸 dict
  // → 後端改欄位，兩處都要手動跟，漏改是靜默錯位（欄位變 undefined、畫面只少一格）。
  // 現已收斂：後端 CaseFinanceResponse（綁 response_model）＋前端 types/erp.ts。

  it('pages/ 內不得本地宣告 FinanceRecord / CaseFinanceData', () => {
    const offenders: string[] = [];
    for (const p of walk(join(SRC, 'pages'))) {
      const src = readFileSync(p, 'utf-8')
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/^\s*\/\/.*$/gm, '');
      if (/interface\s+(FinanceRecord|CaseFinanceData)/.test(src)) {
        offenders.push(p);
      }
    }
    expect(
      offenders,
      '財務紀錄型別必須從 types/erp import（對應後端 CaseFinanceResponse），不得各頁自宣告',
    ).toEqual([]);
  });

  it('財務清單元件皆從 types/erp 取得型別', () => {
    for (const { path } of financeListComponents()) {
      const src = readFileSync(path, 'utf-8');
      expect(
        /from '.*types\/erp'/.test(src),
        `${path} 未從 types/erp import 財務型別`,
      ).toBe(true);
    }
  });
});
