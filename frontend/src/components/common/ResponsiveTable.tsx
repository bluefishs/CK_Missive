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
import { MobileCardList } from './MobileCardList';
import type { PaginationProps } from 'antd';
import { Table } from 'antd';
import type { TableProps } from 'antd';
import type { ColumnType, ColumnsType } from 'antd/es/table';
import { useResponsive } from '../../hooks/utility/useResponsive';
import { stripClientOnlyColumnFeatures } from '../../utils/tableEnhancer';

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
  // ⚠️ 2026-08-29：原本只認 dataIndex ⇒ **純渲染欄（只有 key、沒有 dataIndex）
  // 永遠藏不掉**。DispatchOrdersTab 的「關聯公文／關聯工程／附件」正是這種，
  // 於是 768px 下 13 欄擠在 496px（每欄 38px）而 mobileHiddenColumns 使不上力。
  // 設定寫了卻不生效，和沒寫是同一個結果 —— 而它不會報錯。
  if (typeof col.key === 'string') {
    return col.key;
  }
  return undefined;
}

export interface ResponsiveTableProps<T> extends TableProps<T> {
  /** 行動版隱藏的欄位 dataIndex 列表 */
  mobileHiddenColumns?: string[];
  /** 2026-09-05 RWD：手機（< 768px）改畫卡片 */
  mobileCard?: (record: T, index: number) => React.ReactNode;
  /**
   * 分頁在伺服器端 —— 本元件只拿得到當前這一頁，因此**不得**在前端做排序／篩選。
   *
   * 平常不必傳：`pagination.total` 大於本頁筆數時會自動判定。
   * 只有把分頁器放在表格外面（`pagination={false}` ＋ 另一個 `<Pagination>`）
   * 的頁面要明講 —— 那種寫法從元件內部看不出來（/contract-cases 就是）。
   */
  serverPaged?: boolean;
}

function ResponsiveTableInner<T extends object>(
  {
    mobileHiddenColumns = [],
    mobileCard,
    columns = [],
    scroll,
    size,
    serverPaged,
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
  // 2026-09-05：窄螢幕保留欄寬、橫向捲動（同 EnhancedTable），不再擠壓
  if (isNarrow) {
    filteredColumns = (filteredColumns as ColumnType<T>[]).map((c) => ({ ...c, ellipsis: c.ellipsis ?? { showTitle: true } }));
  }

  // 伺服器分頁 ⇒ 剝掉只作用於當前這一頁的排序／篩選／欄位搜尋（2026-08-31）。
  // 自動判準用執行時的事實：`pagination.total` 是伺服器的總筆數，
  // 大於本頁筆數就代表這裡看不到全部。外掛分頁器的頁面則靠 `serverPaged` 明講。
  const autoServerPaged =
    !!props.pagination &&
    typeof props.pagination === 'object' &&
    typeof props.pagination.total === 'number' &&
    props.pagination.total > (props.dataSource?.length ?? 0);
  if (serverPaged ?? autoServerPaged) {
    filteredColumns = stripClientOnlyColumnFeatures(filteredColumns);
  }

  // ⚠️ md: 900 只在**桌面分支**才會被用到了（isNarrow 已涵蓋 md）。
  // 保留它是為了 lg 以上；`md` 這一格現在是不可達的死值，刻意留著標示斷點意圖。
  const scrollX = responsive({ sm: 700, md: 900, lg: 1200 });

  if (isMobile && mobileCard) {
    return (
      <MobileCardList<T>
        dataSource={props.dataSource}
        rowKey={typeof props.rowKey === 'function' ? (r: T) => (props.rowKey as (r: T) => React.Key)(r) : (props.rowKey as string | undefined) ?? 'id'}
        renderCard={mobileCard}
        pagination={props.pagination === false ? false : (props.pagination as PaginationProps | undefined)}
        loading={typeof props.loading === 'boolean' ? props.loading : undefined}
      />
    );
  }

  return (
    <Table<T>
      columns={filteredColumns}
      // 窄螢幕刻意忽略呼叫端傳入的 scroll.x —— 那是為桌面挑的固定寬度
      // （實測 DispatchOrdersTab 傳 x:1530、ProjectsTab 傳 x:1100，在 390px 下等於強制橫向捲）
      scroll={isNarrow ? { ...scroll, x: 'max-content' } : { x: scroll?.x ?? scrollX, ...scroll }}
      size={size ?? (isNarrow ? 'small' : 'middle')}
      {...props}
      // ⚠️ tableLayout 必須寫在 `{...props}` **之後** —— 展開運算子裡的
      // tableLayout（即使值是 undefined）會覆蓋寫在前面的那一行，寫了等於沒寫。
      tableLayout={isNarrow ? 'auto' : props.tableLayout}
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
