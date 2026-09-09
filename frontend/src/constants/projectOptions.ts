/**
 * 承攬案件相關常數定義
 *
 * 集中管理專案/案件相關的選項常數
 *
 * @version 2.0.0
 * @date 2026-03-30
 */

// 案件狀態選項
export const PROJECT_STATUS_OPTIONS = [
  '待執行',
  '執行中',
  '已結案',
  '未得標',
] as const;

export type ProjectStatus = (typeof PROJECT_STATUS_OPTIONS)[number];

// 計畫類別選項 (v2.0)
export const PROJECT_CATEGORY_OPTIONS = [
  { value: '01委辦招標', label: '01委辦招標' },
  { value: '02承攬報價', label: '02承攬報價' },
] as const;

export const PROJECT_CATEGORY_VALUES = [
  '01委辦招標',
  '02承攬報價',
] as const;

export type ProjectCategory = (typeof PROJECT_CATEGORY_VALUES)[number];

// 作業性質選項 (v2.0 — 11 類)
/**
 * ⚠️ 2026-08-28：**這一份沒有任何消費者，而且值格式與其他兩處不同。不要接回來。**
 *
 * 同一個概念此刻有三處定義：
 *
 *   本檔                                value: '01地面測量'  （代碼+名稱）← 無人使用
 *   pages/contractCase/tabs/constants   value: '01'          （純代碼）
 *   DB 主檔 case_nature_codes           code='01' label='地面測量'  ← **權威**
 *
 * `contract_projects.case_nature` 裡有 51 筆「代碼+名稱」格式，是**歷史殘留**，
 * 不是現在產生的 —— 現行的兩個輸入端（PM 案件頁、承攬案件頁）都存純代碼。
 *
 * 需要作業性質選項時請用 `useCaseNatureOptions()`（讀 DB 主檔），
 * 那是唯一會隨主檔新增而更新的來源。
 */
export const CASE_NATURE_OPTIONS = [
  { value: '01地面測量', label: '01地面測量' },
  { value: '02LiDAR掃描', label: '02LiDAR掃描' },
  { value: '03UAV空拍', label: '03UAV空拍' },
  { value: '04航空測量', label: '04航空測量' },
  { value: '05安全檢測', label: '05安全檢測' },
  { value: '06建物保存', label: '06建物保存' },
  { value: '07建築線測量', label: '07建築線測量' },
  { value: '08透地雷達', label: '08透地雷達' },
  { value: '09資訊系統', label: '09資訊系統' },
  { value: '10技師簽證', label: '10技師簽證' },
  { value: '11其他類別', label: '11其他類別' },
] as const;

export const CASE_NATURE_VALUES = [
  '01地面測量', '02LiDAR掃描', '03UAV空拍', '04航空測量',
  '05安全檢測', '06建物保存', '07建築線測量', '08透地雷達',
  '09資訊系統', '10技師簽證', '11其他類別',
] as const;

export type CaseNature = (typeof CASE_NATURE_VALUES)[number];

// 協力廠商角色選項
export const VENDOR_ROLE_OPTIONS = [
  '測量業務',
  '系統業務',
  '查估業務',
  '其他類別',
] as const;

export type VendorRole = (typeof VENDOR_ROLE_OPTIONS)[number];

// 狀態顏色映射
export const PROJECT_STATUS_COLORS: Record<string, string> = {
  '待執行': 'orange',
  '執行中': 'processing',
  '已結案': 'success',
  '未得標': 'default',
};

/**
 * 計畫類別的**篩選選項**（value 是後端認的類別碼 `01`／`02`）。
 *
 * 2026-09-09 owner「篩選機制模組化」：報價單頁此前把這組選項寫在頁面裡，
 * 帳款兩頁根本沒有這個條件，而上面的 `PROJECT_CATEGORY_OPTIONS` 的 value 是帶中文的
 * `'01委辦招標'`（那是**建案表單**存進 DB 的字串，不是篩選碼）——同一個概念三種寫法。
 * 篩選一律用這一份；後端對應 `schemas/erp/vendor_financial.CaseListFilters.category`。
 */
export const CASE_CATEGORY_OPTIONS = [
  { value: '01', label: '01 委辦招標' },
  { value: '02', label: '02 承攬報價' },
] as const;
