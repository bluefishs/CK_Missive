/**
 * 桃園查估派工系統共用選項常數
 *
 * 統一管理案件類型、查估單位、行政區等下拉選項
 * 確保 UI 與 Excel 匯入的一致性
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

/**
 * 案件類型選項
 * 來源: Excel「1.轄管工程清單」實際資料
 */
export const CASE_TYPE_OPTIONS = [
  { value: '瓶頸', label: '瓶頸' },
  { value: '一般', label: '一般' },
  { value: '一般專簽', label: '一般專簽' },
  { value: '步道', label: '步道' },
  { value: '專簽', label: '專簽' },
  { value: '專報', label: '專報' },
  { value: '溝渠', label: '溝渠' },
  { value: '公園', label: '公園' },
  { value: '水圳', label: '水圳' },
] as const;

/**
 * 查估單位選項
 * 來源: Excel「1.轄管工程清單」實際資料
 */
export const SURVEY_UNIT_OPTIONS = [
  { value: '昇揚估價', label: '昇揚估價' },
  { value: '全國估價', label: '全國估價' },
] as const;

/**
 * 行政區選項 (桃園市 13 區)
 */
export const DISTRICT_OPTIONS = [
  { value: '桃園區', label: '桃園區' },
  { value: '中壢區', label: '中壢區' },
  { value: '平鎮區', label: '平鎮區' },
  { value: '八德區', label: '八德區' },
  { value: '楊梅區', label: '楊梅區' },
  { value: '蘆竹區', label: '蘆竹區' },
  { value: '大溪區', label: '大溪區' },
  { value: '龍潭區', label: '龍潭區' },
  { value: '龜山區', label: '龜山區' },
  { value: '大園區', label: '大園區' },
  { value: '觀音區', label: '觀音區' },
  { value: '新屋區', label: '新屋區' },
  { value: '復興區', label: '復興區' },
] as const;

/**
 * 作業類別選項
 * 來源: 後端 TAOYUAN_WORK_TYPES
 */
export const WORK_TYPE_OPTIONS = [
  { value: '#0.專案行政作業', label: '#0.專案行政作業' },
  { value: '00.專案會議', label: '00.專案會議' },
  { value: '01.地上物查估作業', label: '01.地上物查估作業' },
  { value: '02.土地協議市價查估作業', label: '02.土地協議市價查估作業' },
  { value: '03.土地徵收市價查估作業', label: '03.土地徵收市價查估作業' },
  { value: '04.相關計畫書製作', label: '04.相關計畫書製作' },
  { value: '05.測量作業', label: '05.測量作業' },
  { value: '06.樁位測釘作業', label: '06.樁位測釘作業' },
  { value: '07.辦理教育訓練', label: '07.辦理教育訓練' },
  { value: '08.作業提繳事項', label: '08.作業提繳事項' },
] as const;

/**
 * 進度狀態選項
 */
export const PROGRESS_STATUS_OPTIONS = [
  { value: '未開始', label: '未開始', color: 'default' },
  { value: '進行中', label: '進行中', color: 'processing' },
  { value: '待審核', label: '待審核', color: 'warning' },
  { value: '已完成', label: '已完成', color: 'success' },
] as const;

/**
 * 驗收狀態選項
 */
export const ACCEPTANCE_STATUS_OPTIONS = [
  { value: '未驗收', label: '未驗收', color: 'default' },
  { value: '已驗收', label: '已驗收', color: 'success' },
] as const;

// 固定的承攬案件 (115 年度桃園查估派工)
export const TAOYUAN_CONTRACT = {
  PROJECT_ID: 21, // 對應資料庫 contract_projects.id = 21
  CODE: 'CK2025_01_03_001',
  NAME: '115年度桃園市興辦公共設施用地取得所需土地市價及地上物查估、測量作業暨開瓶資料製作委託專業服務(開口契約)',
} as const;
