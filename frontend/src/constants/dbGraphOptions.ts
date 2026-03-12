/**
 * Database Graph 常數
 *
 * 資料庫圖譜的節點類型、關聯類型、顏色等定義。
 */

/** 資料庫圖譜節點類型選項 */
export const DB_NODE_TYPE_OPTIONS = [
  { label: '資料表', value: 'db_table' },
] as const;

/** 資料庫圖譜關聯類型篩選選項 */
export const DB_RELATION_OPTIONS = [
  { label: 'FK 引用', value: 'references_table' },
  { label: '欄位', value: 'has_column' },
  { label: '索引', value: 'has_index' },
] as const;

/** 節點類型 → 顏色 */
export const DB_NODE_COLORS: Record<string, string> = {
  db_table: '#fa8c16',
};

/** 節點類型 → 中文標籤 */
export const DB_TYPE_LABELS: Record<string, string> = {
  db_table: '資料表',
};
