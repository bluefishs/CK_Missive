/**
 * 年度選項（**西元**）—— 全系統統一。
 *
 * ## 為什麼有這個檔
 *
 * owner 2026-08-20：「之前有標註統一西元年為主」。而實際狀況是三份說法：
 *
 * | 位置 | 說的是 |
 * |---|---|
 * | 承攬案件表單 | 西元下拉（`getFullYear()`）—— **正確** |
 * | PM 案件表單 | `placeholder="民國年"` 自由輸入 |
 * | 報價單表單 | `placeholder="民國年"` 自由輸入 |
 * | 後端 `case_service` | `dump.get("year") or 114` —— 預設值是**民國且寫死** |
 * | schema description | 「年度 (民國)」 |
 *
 * 結果：`pm_cases` 裡 73 筆西元、1 筆民國（`CK2026_PM_01_006` 填了 115）。
 * **那不是使用者填錯 —— 他是照著畫面上的「民國年」填的。**
 * 而以 115 篩選時看不到該看到的案件，以 2026 篩選時看不到那一筆。
 *
 * 正確的那份實作本來就存在（藏在 `useContractCaseForm` 裡），
 * 只是沒有擴散出去。這個檔把它抽出來，讓另外兩處用同一份。
 */

/** 目前年度前後各 N 年的西元年選項（預設前 2 後 2） */
export function generateYearOptions(before = 2, after = 2): number[] {
  const current = new Date().getFullYear();
  const years: number[] = [];
  for (let y = current - before; y <= current + after; y++) years.push(y);
  return years;
}

/** AntD Select/InputNumber 用的 `{ value, label }` 形式 */
export function yearSelectOptions(before = 2, after = 2): Array<{ value: number; label: string }> {
  return generateYearOptions(before, after).map((y) => ({ value: y, label: `${y} 年` }));
}

/**
 * 把民國年正規化成西元年。
 *
 * 民國 100–199 與西元 1990–2100 兩個區間**不重疊**，所以可以精確判定，
 * 不會把西元誤判成民國。
 *
 * 前端也要做一次（不只後端）：使用者輸入當下就看到轉換結果，
 * 比送出後才被默默改掉容易理解。
 */
export function toADYear(v: number | null | undefined): number | null {
  if (v === null || v === undefined || Number.isNaN(v)) return null;
  const n = Math.trunc(v);
  if (n >= 100 && n <= 199) return n + 1911;
  return n;
}
