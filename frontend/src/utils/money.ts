/** 金額顯示：null／空 → 「—」；其餘千分位（2026-09-05，手機卡片與列表共用） */
export const fmtMoney = (v: unknown): string => {
  if (v == null || v === '') return '—';
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString() : String(v);
};
