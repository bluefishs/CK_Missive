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
