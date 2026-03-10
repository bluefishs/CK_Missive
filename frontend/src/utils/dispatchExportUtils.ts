/**
 * dispatchExportUtils - 派工單公文對照矩陣 Excel 匯出
 *
 * 客戶端 Excel 生成，含三個工作表：
 * 1. 公文對照矩陣 (來文/覆文配對)
 * 2. 作業紀錄 (全部紀錄依 sort_order 排序)
 * 3. 統計摘要 (鍵值對)
 *
 * 使用動態 import('xlsx') 延遲載入，減少初始 bundle 大小。
 *
 * @version 1.1.0
 * @date 2026-03-05
 */

import type { WorkRecord } from '../types/taoyuan';
import type { CorrespondenceMatrixRow, MatrixDocItem } from '../components/taoyuan/workflow/chainUtils';
import { getEffectiveDoc } from '../components/taoyuan/workflow/chainUtils';
import { getCategoryLabel, statusLabel } from '../components/taoyuan/workflow';
import type { DispatchWorkStats } from '../components/taoyuan/workflow/useDispatchWorkData';

// ============================================================================
// Types
// ============================================================================

type XLSXModule = typeof import('xlsx');
type WorkSheet = import('xlsx').WorkSheet;

export interface CorrespondenceExportOptions {
  matrixRows: CorrespondenceMatrixRow[];
  records: WorkRecord[];
  stats: DispatchWorkStats;
  dispatchNo?: string;
  projectName?: string;
}

/**
 * Local cell style types for xlsx cell `.s` property.
 * The xlsx 0.18.5 typings define `CellObject.s` as `any`, so we define
 * our own style interfaces to keep the code self-documenting.
 */
interface XlsxFill {
  patternType: string;
  fgColor: { rgb: string };
}

interface XlsxBorderEdge {
  style: string;
  color: { rgb: string };
}

interface XlsxBorder {
  top?: XlsxBorderEdge;
  bottom?: XlsxBorderEdge;
  left?: XlsxBorderEdge;
  right?: XlsxBorderEdge;
}

interface XlsxFont {
  bold?: boolean;
}

interface XlsxAlignment {
  horizontal?: string;
  vertical?: string;
  wrapText?: boolean;
}

interface XlsxCellStyle {
  fill?: XlsxFill;
  border?: XlsxBorder;
  font?: XlsxFont;
  alignment?: XlsxAlignment;
}

// ============================================================================
// Constants
// ============================================================================

/** Light blue fill for incoming doc columns */
const FILL_INCOMING: XlsxFill = {
  patternType: 'solid',
  fgColor: { rgb: 'CCE5FF' },
};

/** Light green fill for outgoing doc columns */
const FILL_OUTGOING: XlsxFill = {
  patternType: 'solid',
  fgColor: { rgb: 'C6EFCE' },
};

/** Light gray fill for neutral columns */
const FILL_GRAY: XlsxFill = {
  patternType: 'solid',
  fgColor: { rgb: 'F2F2F2' },
};

/** Thin border style for all four sides */
const THIN_BORDER: XlsxBorder = {
  top: { style: 'thin', color: { rgb: '000000' } },
  bottom: { style: 'thin', color: { rgb: '000000' } },
  left: { style: 'thin', color: { rgb: '000000' } },
  right: { style: 'thin', color: { rgb: '000000' } },
};

/** Bold + centered header style (base) */
const HEADER_BASE: XlsxCellStyle = {
  font: { bold: true },
  alignment: { horizontal: 'center', vertical: 'center' },
  border: THIN_BORDER,
};

/** Data cell style */
const CELL_BASE: XlsxCellStyle = {
  border: THIN_BORDER,
  alignment: { vertical: 'center', wrapText: true },
};

// ============================================================================
// Helper functions
// ============================================================================

/** Format date string to display format (YYYY-MM-DD) */
function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '';
  // Already in YYYY-MM-DD or ISO format - take first 10 chars
  return dateStr.slice(0, 10);
}

/** Format current datetime for display */
function formatNow(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
    `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  );
}

/** Generate YYYYMMDD date string for filename */
function dateTag(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
}

/** Get status text for a matrix doc item */
function getItemStatus(item?: MatrixDocItem): string {
  if (!item) return '';
  if (item.record) return '已指派';
  if (item.isUnassigned) return '未指派';
  return '';
}

/** Get the associated doc number string for a work record */
function getRecordDocNumber(record: WorkRecord): string {
  const doc = getEffectiveDoc(record);
  return doc?.doc_number || '';
}

/** Apply style to a range of cells in a worksheet */
function applyStyleToRange(
  xlsx: XLSXModule,
  ws: WorkSheet,
  startRow: number,
  startCol: number,
  endRow: number,
  endCol: number,
  style: XlsxCellStyle,
): void {
  for (let r = startRow; r <= endRow; r++) {
    for (let c = startCol; c <= endCol; c++) {
      const addr = xlsx.utils.encode_cell({ r, c });
      if (!ws[addr]) {
        ws[addr] = { t: 's', v: '' };
      }
      ws[addr].s = { ...(ws[addr].s || {}), ...style };
    }
  }
}

/** Apply header style with specific fill to a range of columns on a given row */
function applyHeaderStyle(
  xlsx: XLSXModule,
  ws: WorkSheet,
  row: number,
  colStart: number,
  colEnd: number,
  fill: XlsxFill,
): void {
  for (let c = colStart; c <= colEnd; c++) {
    const addr = xlsx.utils.encode_cell({ r: row, c });
    if (!ws[addr]) {
      ws[addr] = { t: 's', v: '' };
    }
    ws[addr].s = {
      ...HEADER_BASE,
      fill,
    };
  }
}

// ============================================================================
// Sheet builders
// ============================================================================

/**
 * Build Sheet 1: Correspondence Matrix
 */
function buildMatrixSheet(xlsx: XLSXModule, matrixRows: CorrespondenceMatrixRow[]): WorkSheet {
  const headers = [
    '序號',
    '來文字號', '來文日期', '來文主旨', '來文狀態',
    '\u2192',
    '覆文字號', '覆文日期', '覆文主旨', '覆文狀態',
  ];

  const data: (string | number)[][] = [headers];

  matrixRows.forEach((row, idx) => {
    const incoming = row.incoming;
    const outgoing = row.outgoing;
    const arrow = incoming && outgoing ? '\u2192' : '';

    data.push([
      idx + 1,
      incoming?.docNumber || '',
      formatDate(incoming?.docDate),
      incoming?.subject || '',
      getItemStatus(incoming),
      arrow,
      outgoing?.docNumber || '',
      formatDate(outgoing?.docDate),
      outgoing?.subject || '',
      getItemStatus(outgoing),
    ]);
  });

  const ws = xlsx.utils.aoa_to_sheet(data);

  // Column widths
  ws['!cols'] = [
    { wch: 5 },   // 序號
    { wch: 20 },  // 來文字號
    { wch: 12 },  // 來文日期
    { wch: 40 },  // 來文主旨
    { wch: 8 },   // 來文狀態
    { wch: 3 },   // →
    { wch: 20 },  // 覆文字號
    { wch: 12 },  // 覆文日期
    { wch: 40 },  // 覆文主旨
    { wch: 8 },   // 覆文狀態
  ];

  // Freeze first row
  ws['!freeze'] = { xSplit: 0, ySplit: 1 };

  // --- Styling ---
  const totalRows = data.length;

  // Header row: 序號 (gray), 來文 cols 1-4 (blue), arrow (gray), 覆文 cols 6-9 (green)
  applyHeaderStyle(xlsx, ws, 0, 0, 0, FILL_GRAY);      // 序號
  applyHeaderStyle(xlsx, ws, 0, 1, 4, FILL_INCOMING);   // 來文 columns
  applyHeaderStyle(xlsx, ws, 0, 5, 5, FILL_GRAY);       // Arrow
  applyHeaderStyle(xlsx, ws, 0, 6, 9, FILL_OUTGOING);   // 覆文 columns

  // Data rows: thin borders + wrap text
  if (totalRows > 1) {
    applyStyleToRange(xlsx, ws, 1, 0, totalRows - 1, 9, CELL_BASE);
  }

  return ws;
}

/**
 * Build Sheet 2: Work Records
 */
function buildRecordsSheet(xlsx: XLSXModule, records: WorkRecord[]): WorkSheet {
  const headers = ['序號', '分類', '說明', '紀錄日期', '期限日期', '狀態', '關聯公文字號'];

  const sorted = [...records].sort((a, b) => a.sort_order - b.sort_order);

  const data: (string | number)[][] = [headers];

  sorted.forEach((record, idx) => {
    data.push([
      idx + 1,
      getCategoryLabel(record),
      record.description || '',
      formatDate(record.record_date),
      formatDate(record.deadline_date),
      statusLabel(record.status),
      getRecordDocNumber(record),
    ]);
  });

  const ws = xlsx.utils.aoa_to_sheet(data);

  // Column widths
  ws['!cols'] = [
    { wch: 5 },   // 序號
    { wch: 14 },  // 分類
    { wch: 50 },  // 說明
    { wch: 12 },  // 紀錄日期
    { wch: 12 },  // 期限日期
    { wch: 8 },   // 狀態
    { wch: 20 },  // 關聯公文字號
  ];

  // Freeze first row
  ws['!freeze'] = { xSplit: 0, ySplit: 1 };

  // Header style: all gray
  applyHeaderStyle(xlsx, ws, 0, 0, 6, FILL_GRAY);

  // Data rows: thin borders
  const totalRows = data.length;
  if (totalRows > 1) {
    applyStyleToRange(xlsx, ws, 1, 0, totalRows - 1, 6, CELL_BASE);
  }

  return ws;
}

/**
 * Build Sheet 3: Statistics Summary
 */
function buildStatsSheet(
  xlsx: XLSXModule,
  stats: DispatchWorkStats,
  dispatchNo?: string,
  projectName?: string,
): WorkSheet {
  const kvPairs: [string, string | number][] = [
    ['派工單號', dispatchNo || ''],
    ['工程名稱', projectName || ''],
    ['匯出時間', formatNow()],
    ['作業紀錄總數', stats.total],
    ['已完成', stats.completed],
    ['進行中', stats.inProgress],
    // ['逾期', stats.overdue],  // 暫隱藏：目前無逾期檢測邏輯
    ['來文數', stats.incomingDocs],
    ['覆文數', stats.outgoingDocs],
    ['關聯公文總數', stats.linkedDocCount],
    ['未指派公文', stats.unassignedDocCount],
    ['當前階段', stats.currentStage],
  ];

  const headers = ['項目', '值'];
  const data: (string | number)[][] = [headers, ...kvPairs];

  const ws = xlsx.utils.aoa_to_sheet(data);

  // Column widths
  ws['!cols'] = [
    { wch: 16 },  // 項目
    { wch: 40 },  // 值
  ];

  // Freeze first row
  ws['!freeze'] = { xSplit: 0, ySplit: 1 };

  // Header style
  applyHeaderStyle(xlsx, ws, 0, 0, 1, FILL_GRAY);

  // Data rows
  const totalRows = data.length;
  if (totalRows > 1) {
    applyStyleToRange(xlsx, ws, 1, 0, totalRows - 1, 1, CELL_BASE);
  }

  // Bold the key column (column 0)
  for (let r = 1; r < totalRows; r++) {
    const addr = xlsx.utils.encode_cell({ r, c: 0 });
    if (ws[addr]) {
      ws[addr].s = {
        ...(ws[addr].s || {}),
        font: { bold: true },
      };
    }
  }

  return ws;
}

// ============================================================================
// Main export function
// ============================================================================

/**
 * Export correspondence matrix, work records, and statistics to an Excel file.
 *
 * Generates a 3-sheet workbook and triggers a browser download.
 * Uses dynamic import('xlsx') to reduce initial bundle size.
 */
export async function exportCorrespondenceMatrix(options: CorrespondenceExportOptions): Promise<void> {
  const { matrixRows, records, stats, dispatchNo, projectName } = options;

  const XLSX = await import('xlsx');

  // Build workbook with 3 sheets
  const wb = XLSX.utils.book_new();

  const wsMatrix = buildMatrixSheet(XLSX, matrixRows);
  XLSX.utils.book_append_sheet(wb, wsMatrix, '公文對照矩陣');

  const wsRecords = buildRecordsSheet(XLSX, records);
  XLSX.utils.book_append_sheet(wb, wsRecords, '作業紀錄');

  const wsStats = buildStatsSheet(XLSX, stats, dispatchNo, projectName);
  XLSX.utils.book_append_sheet(wb, wsStats, '統計摘要');

  // Generate filename
  const parts = ['公文對照'];
  if (dispatchNo) parts.push(`_${dispatchNo}`);
  if (projectName) parts.push(`_${projectName}`);
  parts.push(`_${dateTag()}`);
  const filename = `${parts.join('')}.xlsx`;

  // Write and trigger download via blob URL + anchor click
  const wbOut = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob([wbOut], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
