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
    // 必須先剝除註解才能比對位置（初版比對到註解裡的字 → 假綠）。
    const src = raw
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/^\s*\/\/.*$/gm, '');

    // 2026-09-06：操作欄已整欄移除（一畫面 19 顆按鈕），鑽取入口改為 onRow 點整列進詳情。
    // 契約不變：入口必須無條件存在——所以改驗 onRow 內有 ERP_EXPENSE_DETAIL，且它不在任何 canEdit 條件式之內。
    const rowIdx = src.indexOf('onRow=');
    expect(rowIdx, '找不到 onRow（元件結構已變，請更新本測試）').toBeGreaterThan(0);
    const rowBlock = src.slice(rowIdx, rowIdx + 1200);
    const detailIdx = rowBlock.indexOf('ERP_EXPENSE_DETAIL');
    expect(detailIdx, 'onRow 沒有導向核銷詳情').toBeGreaterThan(0);
    const gated = rowBlock.slice(0, detailIdx).includes('canEdit');
    expect(gated, '鑽取入口被 canEdit 條件包住 —— verified 的紀錄會失去入口').toBe(false);
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
