/**
 * ContractCaseDetailPage Tab 元件共用常數
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

// 案件類別選項
export const CATEGORY_OPTIONS = [
  { value: '01', label: '01委辦案件', color: 'blue' },
  { value: '02', label: '02協力計畫', color: 'green' },
  { value: '03', label: '03小額採購', color: 'orange' },
  { value: '04', label: '04其他類別', color: 'default' },
];

// 案件性質選項
export const CASE_NATURE_OPTIONS = [
  { value: '01', label: '01測量案', color: 'cyan' },
  { value: '02', label: '02資訊案', color: 'purple' },
  { value: '03', label: '03複合案', color: 'gold' },
];

// 執行狀態選項 (使用中文值對應資料庫)
export const STATUS_OPTIONS = [
  { value: '待執行', label: '待執行', color: 'warning' },
  { value: '執行中', label: '執行中', color: 'processing' },
  { value: '已結案', label: '已結案', color: 'success' },
  { value: '未得標', label: '未得標', color: 'error' },
];

// 承辦同仁角色選項 (與 StaffPage ROLE_OPTIONS 一致)
export const STAFF_ROLE_OPTIONS = [
  { value: '計畫主持', label: '計畫主持', color: 'red' },
  { value: '計畫協同', label: '計畫協同', color: 'orange' },
  { value: '專案PM', label: '專案PM', color: 'blue' },
  { value: '職安主管', label: '職安主管', color: 'green' },
];

// 協力廠商角色選項
export const VENDOR_ROLE_OPTIONS = [
  { value: '測量業務', label: '測量業務', color: 'blue' },
  { value: '系統業務', label: '系統業務', color: 'green' },
  { value: '查估業務', label: '查估業務', color: 'orange' },
  { value: '其他類別', label: '其他類別', color: 'default' },
];
