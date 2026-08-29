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
  // ⚠️ 2026-08-29：本元件原本全程只看 `isMobile`（< 768px）——
  // 而 `isMobile = !screens.md`，AntD 的 md 斷點就是 768，
  // **恰好 768px 時 isMobile 為 false** ⇒ 平板（768–991）走桌面分支，
  // 拿到下方 `responsive({ md: 900 })` 或呼叫端為桌面挑的固定 scroll.x
  // （DispatchOrdersTab 傳 1530、ProjectsTab 傳 1100），在 768px 視窗下
  // 等於**強制**橫向捲動。實測 768px：/taoyuan/dispatch 外溢 580px、
  // /documents 586px、/contract-cases 581px、/staff 554px。
  //
  // EnhancedTable 早在 2026-08-15 就把判準改成 `isMobile || isTablet`（< 992px），
  // 但**沒有擴散到本元件** —— 兩個共用表格包裝各自一套窄螢幕行為，
  // 而 23 個檔用的是沒修的這一個。這是本 repo 反覆記過的
  // 「正確做法存在卻沒擴散」，配套稽核見 `responsive_table_narrow_audit.py`。
  const { isMobile, isTablet, responsive } = useResponsive();
  const isNarrow = isMobile || isTablet;

  let filteredColumns: ColumnsType<T> = isNarrow && mobileHiddenColumns.length > 0
    ? (columns as ColumnType<T>[]).filter(
        (col) => {
          const dataIndex = getColumnDataIndex(col);
          if (!dataIndex) return true;
          return !mobileHiddenColumns.includes(dataIndex);
        },
      )
    : columns;

  // 窄螢幕拿掉固定 width，讓表格適應容器（與 EnhancedTable 同一套行為）。
  // 2026-08-02：本元件原本在 xs 仍給 scroll.x=500，等於**強制**表格比 390px 視窗寬，
  // 實測 /contract-cases 外溢 633px、/taoyuan/dispatch 734px —— 設定本身就在製造橫向捲動。
  if (isNarrow) {
    filteredColumns = (filteredColumns as ColumnType<T>[]).map((c) => {
      const { width: _unusedWidth, ...rest } = c;  // eslint-disable-line @typescript-eslint/no-unused-vars
      return { ...rest, ellipsis: c.ellipsis ?? { showTitle: true } };
    });
  }

  // ⚠️ md: 900 只在**桌面分支**才會被用到了（isNarrow 已涵蓋 md）。
  // 保留它是為了 lg 以上；`md` 這一格現在是不可達的死值，刻意留著標示斷點意圖。
  const scrollX = responsive({ sm: 700, md: 900, lg: 1200 });

  return (
    <Table<T>
      columns={filteredColumns}
      // 窄螢幕刻意忽略呼叫端傳入的 scroll.x —— 那是為桌面挑的固定寬度
      // （實測 DispatchOrdersTab 傳 x:1530、ProjectsTab 傳 x:1100，在 390px 下等於強制橫向捲）
      scroll={isNarrow ? { ...scroll, x: undefined } : { x: scroll?.x ?? scrollX, ...scroll }}
      size={size ?? (isNarrow ? 'small' : 'middle')}
      {...props}
      // ⚠️ tableLayout 必須寫在 `{...props}` **之後** —— 展開運算子裡的
      // tableLayout（即使值是 undefined）會覆蓋寫在前面的那一行，寫了等於沒寫。
      tableLayout={isNarrow ? 'fixed' : props.tableLayout}
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
