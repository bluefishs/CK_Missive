/** 金流異常標籤的顏色與文字 —— 列表欄、手機卡片、詳情面板共用同一份（不各自決定「已判讀」長什麼樣） */
import type { FinanceAnomaly } from '../../types/erp';

export const anomalyTagColor = (a: FinanceAnomaly): string =>
  // 2026-09-09 owner：「異常狀態應更明顯呈現如紅色標注或圖示註記，才有實質告知或預警機制」。
  // 此前 yellow 級用 gold（淡黃），在手機截圖上與一般標籤幾乎分不出來。
  // red ＝數字互相矛盾 ⇒ 紅；yellow ＝需要人判斷 ⇒ 橘（antd `volcano`），兩級都是警示色，
  // 只有「已判讀」才退回灰。
  a.acknowledged ? 'default' : a.severity === 'red' ? 'red' : 'volcano';

/** 標籤前綴圖示：文字本身就帶警示，不依賴顏色（色弱／灰階列印也看得出來）。 */
export const anomalyTagIcon = (a: FinanceAnomaly): string =>
  a.acknowledged ? '✓' : a.severity === 'red' ? '⛔' : '⚠';

export const anomalyTagText = (a: FinanceAnomaly): string =>
  a.acknowledged ? `${a.label}（已判讀）` : `${anomalyTagIcon(a)} ${a.label}`;
