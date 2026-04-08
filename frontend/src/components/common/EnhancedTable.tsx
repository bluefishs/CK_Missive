/**
 * EnhancedTable — Ant Design Table 自動套用排序/篩選/Tooltip
 *
 * 取代直接 import { Table } from 'antd'，自動：
 * 1. enhanceColumns: 排序 (日期/數字/文字) + 篩選 (狀態/類型)
 * 2. 移除固定 width 的文字欄，改用自動伸縮 + ellipsis tooltip
 * 3. scroll.x 預設 'max-content' 確保小螢幕可橫向滾動
 * 4. showTotal 分頁顯示總筆數
 *
 * 用法 (與 Ant Design Table 完全相容):
 *   import { EnhancedTable } from '../components/common/EnhancedTable';
 *   <EnhancedTable columns={columns} dataSource={data} />
 *
 * @version 1.0.0
 */
import { useMemo } from 'react';
import { Table } from 'antd';
import type { TableProps, ColumnsType, ColumnType } from 'antd/es/table';
import { enhanceColumns } from '../../utils/tableEnhancer';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type R = Record<string, any>;

/** 自動處理欄位：移除純文字欄的固定 width + 加 ellipsis tooltip */
function autoResponsiveColumns<T = R>(columns: ColumnsType<T>): ColumnsType<T> {
  return columns.map((col) => {
    const c = col as ColumnType<T>;
    const key = String(c.dataIndex || c.key || '');
    const out = { ...c };

    // 有 render 的欄位不動 (可能有特殊渲染如 Tag/Button)
    // 但純文字欄 (title/name/subject/description) 移除固定 width + 加 ellipsis
    const textKeys = ['title', 'name', 'subject', 'description', 'case_name', 'project_name', 'notes', 'address'];
    if (textKeys.some(k => key.includes(k)) && out.width && !out.ellipsis) {
      delete out.width;
      out.ellipsis = { showTitle: true };
    }

    return out;
  });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function EnhancedTable<T extends R = any>(props: TableProps<T>) {
  const { columns, dataSource, pagination, scroll, ...rest } = props;

  const enhanced = useMemo(() => {
    if (!columns) return columns;
    const responsive = autoResponsiveColumns(columns);
    return enhanceColumns(responsive, dataSource as T[]);
  }, [columns, dataSource]);

  const defaultPagination = pagination === false ? false : {
    showSizeChanger: true,
    showTotal: (total: number) => `共 ${total} 筆`,
    ...(typeof pagination === 'object' ? pagination : {}),
  };

  return (
    <Table<T>
      columns={enhanced}
      dataSource={dataSource}
      pagination={defaultPagination}
      scroll={{ x: 'max-content', ...scroll }}
      {...rest}
    />
  );
}

export default EnhancedTable;
