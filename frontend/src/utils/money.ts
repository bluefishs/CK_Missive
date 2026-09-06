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