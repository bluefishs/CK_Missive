/** 金額顯示：null／空 → 「—」；其餘千分位、**取整到元**。
 *
 * 2026-09-06 owner 從 `/erp/quotations` 回報：四張統計卡裡只有「應收未收」帶小數
 *（39,431,749.5）——含稅換算會生出 .5，而其他卡剛好整除。兩個後果：
 *   ① 同一排卡片一個有小數一個沒有，看起來像兩種東西；
 *   ② 多出的字元讓那張卡在 390px 換行，卡片高度就不齊了。
 * 台幣記帳到元，顯示層一律 `Math.round`（**只改顯示**，資料庫仍存原值——
 * 四捨五入寫回資料才是真的把帳改掉）。
 */
export const fmtMoney = (v: unknown): string => {
  if (v == null || v === '') return '—';
  const n = Number(v);
  return Number.isFinite(n) ? Math.round(n).toLocaleString() : String(v);
};

/** 金額為 0 或空時用**語意文字**取代「0」。
 *
 * 2026-09-09 owner：「呈現面一致性——未開請款、—、0 三種並存，數字 0 容易誤解」。
 * 同一個「還沒有請款」在報價單列表是橙色「未開請款」、手機卡片是「—」、委託單位帳款是「0」。
 * 規則收成一條：**沒有那類紀錄就說沒有（未開請款／未收款／無應付／未付款），有才印數字**；
 * 「—」只留給「這個欄位不適用」（例如未成案的案沒有年度）。呼叫端傳語意字。
 */
export const fmtMoneyOr = (v: unknown, empty: string): string => {
  if (v == null || v === '') return empty;
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v);
  return Math.round(n) === 0 ? empty : fmtMoney(n);
};
