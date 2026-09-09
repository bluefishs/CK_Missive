/** CaseFilterBar 的選項單一定義（拆出元件檔以符合 react-refresh 規則）。 */
export const CURRENT_CASE_YEAR = new Date().getFullYear();

/** 年度選項：全部年度（0）＋ 近五年。表頭漏斗（buildServerFilters）也從這裡拿。 */
export const caseYearOptions = (): Array<{ value: number; label: string }> => [
  { value: 0, label: '全部年度' },
  ...Array.from({ length: 5 }, (_, i) => ({ value: CURRENT_CASE_YEAR - i, label: `${CURRENT_CASE_YEAR - i} 年` })),
];

export const ANOMALY_FILTER_OPTIONS = [
  { value: 'open', label: '異常｜待判讀' },
  { value: 'all', label: '異常｜全部' },
];
