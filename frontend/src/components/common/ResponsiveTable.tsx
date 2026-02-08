/**
 * ResponsiveTable - 響應式表格高階元件
 *
 * 封裝 Ant Design Table，自動根據 useResponsive() 設定:
 * - scroll.x: 依螢幕尺寸自動調整水平捲動寬度
 * - mobileHiddenColumns: 行動版隱藏指定欄位
 * - size: 行動版自動切換為 small
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import React from 'react';
import { Table } from 'antd';
import type { TableProps } from 'antd';
import type { ColumnType, ColumnsType } from 'antd/es/table';
import { useResponsive } from '../../hooks/utility/useResponsive';

/**
 * 從欄位定義中取得用於比對的 dataIndex 值
 */
function getColumnDataIndex<T>(col: ColumnType<T>): string | undefined {
  const dataIndex = col.dataIndex;
  if (typeof dataIndex === 'string') {
    return dataIndex;
  }
  if (Array.isArray(dataIndex)) {
    return dataIndex.join('.');
  }
  return undefined;
}

export interface ResponsiveTableProps<T> extends TableProps<T> {
  /** 行動版隱藏的欄位 dataIndex 列表 */
  mobileHiddenColumns?: string[];
}

function ResponsiveTableInner<T extends object>(
  {
    mobileHiddenColumns = [],
    columns = [],
    scroll,
    size,
    ...props
  }: ResponsiveTableProps<T>,
) {
  const { isMobile, responsive } = useResponsive();

  const filteredColumns: ColumnsType<T> = isMobile && mobileHiddenColumns.length > 0
    ? (columns as ColumnType<T>[]).filter(
        (col) => {
          const dataIndex = getColumnDataIndex(col);
          if (!dataIndex) return true;
          return !mobileHiddenColumns.includes(dataIndex);
        },
      )
    : columns;

  const scrollX = responsive({ xs: 500, sm: 700, md: 900, lg: 1200 });

  return (
    <Table<T>
      columns={filteredColumns}
      scroll={{ x: scroll?.x ?? scrollX, ...scroll }}
      size={size ?? (isMobile ? 'small' : 'middle')}
      {...props}
    />
  );
}

/**
 * ResponsiveTable 元件
 *
 * 接受所有 Ant Design Table props，額外提供:
 * - mobileHiddenColumns: 行動版 (< 768px) 隱藏的欄位 dataIndex 列表
 *
 * @example
 * ```tsx
 * <ResponsiveTable
 *   columns={columns}
 *   dataSource={data}
 *   mobileHiddenColumns={['created_at', 'category', 'status']}
 * />
 * ```
 */
export const ResponsiveTable = ResponsiveTableInner as <T extends object>(
  props: ResponsiveTableProps<T>,
) => React.ReactElement;

export default ResponsiveTable;
