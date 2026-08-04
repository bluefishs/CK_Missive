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
import { useResponsive } from '../../hooks';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type R = Record<string, any>;

/**
 * 欄位可標記 `hideOnMobile: true`，在窄螢幕不顯示（2026-08-02）。
 *
 * 為何是 opt-in 而不是自動判斷：自動挑欄位藏很容易把該頁最關鍵的資訊藏掉，
 * 而「哪一欄在手機上可以不看」是各頁的業務判斷，不是通用規則。
 */
export type ResponsiveColumn<T> = ColumnType<T> & { hideOnMobile?: boolean };

/**
 * 自動處理欄位：移除純文字欄的固定 width + 加 ellipsis tooltip。
 *
 * ⚠️ 命名說明（2026-08-02）：這個函式**不看螢幕寬度**——它做的是「文字欄不要被
 * 固定寬度撐開」，與視窗大小無關。名字裡的 responsive 一度讓人以為 RWD 已經處理好了，
 * 實際上 `scroll.x='max-content'` 是讓表格橫向捲出去（實測 ERP 列表在 390px 下
 * 外溢 608~1109px，公文列表僅 158px）。真正的窄螢幕收斂在下方 `hideOnMobile`。
 */
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
  const { isMobile } = useResponsive();

  const enhanced = useMemo(() => {
    if (!columns) return columns;
    // 窄螢幕先濾掉標記 hideOnMobile 的欄位，再做其餘加工
    let visible = isMobile
      ? columns.filter((c) => !(c as ResponsiveColumn<T>).hideOnMobile)
      : columns;
    // 窄螢幕另需拿掉固定 width：否則各欄 width 加總仍會把 <table> 撐到遠超視窗
    // （2026-08-02 實測：/erp/quotations 隱藏欄位後只剩 4 欄，<table> 仍是 1000px，
    //   因為剩下的欄位各自帶著桌面版的固定寬度，配上 scroll.x='max-content' 就展開了）
    if (isMobile) {
      visible = visible.map((c) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { width: _unusedWidth, ...rest } = c as ColumnType<T>;
        return { ...rest, ellipsis: (c as ColumnType<T>).ellipsis ?? { showTitle: true } };
      });
    }
    const responsive = autoResponsiveColumns(visible);
    // 窄螢幕不自動加排序/篩選（2026-08-04）。
    // 實測 /contract-cases/:id 承辦同仁分頁：隱藏次要欄位後表格雖然不外溢了，
    // 但每欄的排序箭頭＋篩選漏斗在 390px 下把欄寬吃掉 → 標題變成「角..」「聯絡...」、
    // 姓名被截成兩個字 —— **從「要橫向捲」換成「看不懂」，不算修好**。
    // 這些是滑鼠導向的輔助功能，在手機上的成本遠高於價值；需要排序時可轉桌面。
    return isMobile ? responsive : enhanceColumns(responsive, dataSource as T[]);
  }, [columns, dataSource, isMobile]);

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
      // 桌面沿用 max-content（欄多時可橫向捲）；窄螢幕改為讓表格適應容器寬度，
      // 否則「可以橫向捲」實際體感就是每一列都要左右滑才看得完。
      // tableLayout='fixed' 是必要的：移除 scroll.x 後 AntD 會退回 auto layout，
      // 長內容（如公文標題）會把欄位撐開 —— 實測 /documents 因此從 158px 惡化到 778px。
      scroll={isMobile ? { ...scroll, x: undefined } : { x: 'max-content', ...scroll }}
      {...rest}
      tableLayout={isMobile ? 'fixed' : rest.tableLayout}
      // 窄螢幕一律 small（2026-08-04）：AntD middle 的儲存格左右內距各 16px，
      // 4 欄就吃掉 128px —— 在 390px 下實測讓「姓名」被截成兩個字。
      // small 是 8px，同樣 4 欄多出 64px 給內容。放在 rest 之後才蓋得掉呼叫端傳的 size
      //（同 tableLayout 的教訓：寫在展開之前等於沒寫）。
      size={isMobile ? 'small' : rest.size}
    />
  );
}

export default EnhancedTable;
