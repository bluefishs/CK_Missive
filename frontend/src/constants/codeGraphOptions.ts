/**
 * Code Graph / Code Wiki 共用常數
 *
 * SSOT：KnowledgeGraphPage 與 CodeGraphManagementPage 共用。
 */

/** Code Wiki 實體類型選項 */
export const CODE_WIKI_TYPE_OPTIONS = [
  { label: 'Python 模組', value: 'py_module' },
  { label: 'Python 類別', value: 'py_class' },
  { label: 'Python 函數', value: 'py_function' },
  { label: '資料表', value: 'db_table' },
  { label: 'TS 模組', value: 'ts_module' },
  { label: 'React 元件', value: 'ts_component' },
  { label: 'React Hook', value: 'ts_hook' },
] as const;

/** Code Wiki 關聯類型篩選選項 */
export const CODE_RELATION_OPTIONS = [
  { label: '定義類別', value: 'defines_class' },
  { label: '定義函數', value: 'defines_function' },
  { label: '方法', value: 'has_method' },
  { label: '匯入', value: 'imports' },
  { label: '繼承', value: 'inherits' },
  { label: 'FK 引用', value: 'references_table' },
  { label: '使用', value: 'uses' },
  { label: '欄位', value: 'has_column' },
  { label: '全部', value: 'code_graph' },
] as const;

/** 實體類型 → 中文標籤對照 */
export const CODE_TYPE_LABELS: Record<string, string> = {
  py_module: 'Python 模組',
  py_class: 'Python 類別',
  py_function: 'Python 函數',
  db_table: '資料表',
  ts_module: 'TS 模組',
  ts_component: 'React 元件',
  ts_hook: 'React Hook',
};
