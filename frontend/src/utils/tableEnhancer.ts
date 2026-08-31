/**
 * 表格欄位強化工具 — 自動為 Ant Design Table 欄位加入排序和篩選
 *
 * 使用:
 *   import { enhanceColumns } from '../utils/tableEnhancer';
 *   <Table columns={enhanceColumns(columns, data)} ... />
 *
 * @version 1.0.0
 * @created 2026-03-28
 */

import type { ColumnsType, ColumnType } from 'antd/es/table';

const STATUS_KEYS = ['status', 'severity', 'type', 'category', 'owasp', 'scan_type', 'event_type', 'link_type', 'role', 'doc_type', 'work_type'];
const DATE_KEYS = ['date', 'created_at', 'updated_at', 'resolved_at', 'completed_at', 'deadline'];
const NUMBER_KEYS = ['count', 'amount', 'score', 'total', 'progress', 'id', 'overdue_days'];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type R = Record<string, any>;

function get(obj: unknown, key: string): unknown {
  return (obj as R)?.[key];
}

/**
 * 剝掉「只看得到當前這一頁」的欄位功能 —— 給伺服器分頁的表格用。
 *
 * 2026-08-31 建立。前端的比較器與 `onFilter` 只走過 `dataSource`，
 * 而伺服器分頁時那是本頁的 10 筆，分頁器顯示的卻是全部 72 筆。
 * 失效的三種形狀（owner 當日各回報一次，沒有一種會報錯）：
 *
 *   ① 篩選後整頁空白       ② 下拉只列得出本頁有的那一個值
 *   ③ 「依金額排序」只排了這 10 筆 —— **它給你一個看起來合理的錯答案**
 *
 * 保留 `sorter: true`／`filterMultiple` 這類**伺服器端**標記：
 * 它們代表「排序交給後端做」，本來就是對的。只剝函式型的。
 *
 * ⚠️ 搜尋框（`getColumnSearchProps`）要連 `filterDropdown` 一起剝：
 * 只拿掉 `onFilter` 會留下一個打了字沒有反應的輸入框 —— 比錯答案更難察覺。
 */
export function stripClientOnlyColumnFeatures<T = R>(
  columns: ColumnsType<T>,
): ColumnsType<T> {
  return columns.map((col) => {
    const c = col as ColumnType<T>;
    const out: ColumnType<T> = { ...c };
    let touched = false;

    if (typeof out.sorter === 'function') {
      delete out.sorter;
      delete out.sortDirections;
      delete out.defaultSortOrder;
      touched = true;
    }
    if (out.onFilter) {
      delete out.onFilter;
      delete out.filters;
      delete out.filterDropdown;
      delete out.filterIcon;
      delete out.filteredValue;
      delete out.defaultFilteredValue;
      touched = true;
    }
    return touched ? out : col;
  });
}

export function enhanceColumns<T = R>(
  columns: ColumnsType<T>,
  data?: T[],
): ColumnsType<T> {
  return columns.map((col) => {
    const c = col as ColumnType<T>;
    const key = String(c.dataIndex || c.key || '');
    if (!key || c.sorter || c.filters) return col;

    const out: ColumnType<T> = { ...c };

    // 排序
    if (DATE_KEYS.some(k => key.includes(k))) {
      out.sorter = (a, b) => String(get(a, key) || '').localeCompare(String(get(b, key) || ''));
      out.sortDirections = ['descend', 'ascend'];
    } else if (NUMBER_KEYS.some(k => key.includes(k))) {
      out.sorter = (a, b) => (Number(get(a, key)) || 0) - (Number(get(b, key)) || 0);
    } else if (!key.includes('snippet') && !key.includes('description')) {
      out.sorter = (a, b) => String(get(a, key) || '').localeCompare(String(get(b, key) || ''));
    }

    // 篩選（狀態/類型欄位）
    if (STATUS_KEYS.some(k => key.includes(k)) && data?.length) {
      const values = [...new Set(data.map(d => get(d, key)).filter(Boolean))].map(String);
      if (values.length > 0 && values.length <= 20) {
        out.filters = values.map(v => ({ text: v, value: v }));
        out.onFilter = (value, record) => get(record, key) === value;
      }
    }

    return out;
  });
}
