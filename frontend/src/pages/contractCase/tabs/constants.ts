/**
 * ContractCaseDetailPage Tab 元件共用常數
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

// 計畫類別選項
export const CATEGORY_OPTIONS = [
  { value: '01', label: '01委辦招標', color: 'blue' },
  { value: '02', label: '02承攬報價', color: 'green' },
];

// 作業性質選項
export const CASE_NATURE_OPTIONS = [
  { value: '01', label: '01地面測量', color: 'cyan' },
  { value: '02', label: '02LiDAR掃描', color: 'blue' },
  { value: '03', label: '03UAV空拍', color: 'geekblue' },
  { value: '04', label: '04航空測量', color: 'purple' },
  { value: '05', label: '05安全檢測', color: 'red' },
  { value: '06', label: '06建物保存', color: 'volcano' },
  { value: '07', label: '07建築線測量', color: 'orange' },
  { value: '08', label: '08透地雷達', color: 'gold' },
  { value: '09', label: '09資訊系統', color: 'lime' },
  { value: '10', label: '10技師簽證', color: 'green' },
  { value: '11', label: '11其他類別', color: 'default' },
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
