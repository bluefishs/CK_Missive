/**
 * 公文詳情頁面常數定義
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

/** 文件類型選項（收文用） */
export const DOC_TYPE_OPTIONS = [
  { value: '函', label: '函', color: 'blue' },
  { value: '開會通知單', label: '開會通知單', color: 'green' },
  { value: '會勘通知單', label: '會勘通知單', color: 'orange' },
];

/** 發文形式選項（電子交換/紙本郵寄） */
export const DELIVERY_METHOD_OPTIONS = [
  { value: '電子交換', label: '電子交換', color: 'green' },
  { value: '紙本郵寄', label: '紙本郵寄', color: 'orange' },
];

/** 處理狀態選項 */
export const STATUS_OPTIONS = [
  { value: '收文完成', label: '收文完成', color: 'processing' },
  { value: '使用者確認', label: '使用者確認', color: 'success' },
  { value: '收文異常', label: '收文異常', color: 'error' },
];

/** 優先等級選項 */
export const PRIORITY_OPTIONS = [
  { value: 1, label: '1 - 最高', color: 'blue' },
  { value: 2, label: '2 - 高', color: 'green' },
  { value: 3, label: '3 - 普通', color: 'orange' },
  { value: 4, label: '4 - 低', color: 'red' },
  { value: 5, label: '5 - 最低', color: 'purple' },
];

/** 預設檔案驗證常數 */
export const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
  '.zip', '.rar', '.7z', '.txt', '.csv', '.xml', '.json',
  '.dwg', '.dxf', '.shp', '.kml', '.kmz',
];
export const DEFAULT_MAX_FILE_SIZE_MB = 50;

/** 桃園派工作業類別 (匹配後端 WORK_TYPES) */
export const TAOYUAN_WORK_TYPES_LIST = [
  '#0.專案行政作業',
  '00.專案會議',
  '01.地上物查估作業',
  '02.土地協議市價查估作業',
  '03.土地徵收市價查估作業',
  '04.相關計畫書製作',
  '05.測量作業',
  '06.樁位測釘作業',
  '07.辦理教育訓練',
  '08.作業提繳事項',
];
