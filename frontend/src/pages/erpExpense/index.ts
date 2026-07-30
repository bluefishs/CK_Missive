// 2026-07-30 收斂：移除 4 個「出生即孤兒」Modal（自 2026-04-04 建立起從未被任何頁面 import）。
//   OCRModal / QRScanModal      → 能力為 SmartScanModal + ExpenseScanPanel 的嚴格子集
//   MofInvoiceModal             → 建立頁已內建「財政部發票」輸入法
//   ExpenseCreateModal          → 已有完整建立頁，且違反規約「CRUD=navigate、禁 Modal 編輯」
// 保留並已掛載：SmartScanModal（批次連續掃描，建立頁沒有的能力）→ 核銷清單頁「批次掃描」
export { default as SmartScanModal } from './SmartScanModal';
export { default as ExpenseImportModal } from './ExpenseImportModal';
export { default as ExpenseScanPanel } from './ExpenseScanPanel';
export { compressImage } from './imageUtils';
export { default as InvoiceSubTable } from './InvoiceSubTable';
export type { ExpenseGroup } from './InvoiceSubTable';
