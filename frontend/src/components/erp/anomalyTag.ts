/** 金流異常標籤的顏色與文字 —— 列表欄、手機卡片、詳情面板共用同一份（不各自決定「已判讀」長什麼樣） */
import type { FinanceAnomaly } from '../../types/erp';

export const anomalyTagColor = (a: FinanceAnomaly): string =>
  a.acknowledged ? 'default' : a.severity === 'red' ? 'red' : 'gold';

export const anomalyTagText = (a: FinanceAnomaly): string =>
  a.acknowledged ? `${a.label}（已判讀）` : a.label;
