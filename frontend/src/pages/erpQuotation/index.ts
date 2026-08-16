// 2026-08-02：InvoicesTab / BillingsTab / VendorPayablesTab 已移除。
// 它們自建立起就沒有任何頁面使用（只在本檔 re-export），
// 報價單詳情頁實際渲染的是雙向的 AccountRecordTab；填報已改為獨立路由頁。
export { default as ProfitTrendTab } from './ProfitTrendTab';
export { QuotationItemsTab } from './QuotationItemsTab';
