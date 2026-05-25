/**
 * dispatchExportUtils - 派工單公文對照矩陣 Excel 匯出
 *
 * 客戶端 Excel 生成，含三個工作表：
 * 1. 公文對照矩陣 (來文/覆文配對)
 * 2. 作業紀錄 (全部紀錄依 sort_order 排序)
 * 3. 統計摘要 (鍵值對)
 *
 * 使用動態 import('exceljs') 延遲載入，減少初始 bundle 大小。
 *
 * @version 2.0.0 — 2026-05-21 從 xlsx (SheetJS) 遷至 ExcelJS（修 GHSA-4r6h-8v6p-xvw6 prototype pollution / GHSA-5pgg-2g8v-p4x9 ReDoS）
 * @date 2026-03-05
 */

import type ExcelJSNS from 'exceljs';
import type { WorkRecord } from '../types/taoyuan';
import type {
  CorrespondenceMatrixRow,
  MatrixDocItem,
} from '../components/taoyuan/workflow/chainUtils';
import { getEffectiveDoc } from '../components/taoyuan/workflow/chainUtils';
import { getCategoryLabel, statusLabel } from '../components/taoyuan/workflow';
import type { DispatchWorkStats } from '../components/taoyuan/workflow/useDispatchWorkData';

// ============================================================================
// Types
// ============================================================================

export interface CorrespondenceExportOptions {
  matrixRows: CorrespondenceMatrixRow[];
  records: WorkRecord[];
  stats: DispatchWorkStats;
  dispatchNo?: string;
  projectName?: string;
}

// ============================================================================
// Constants — ExcelJS style helpers
// ============================================================================

/** Light blue fill for incoming doc columns */
const FILL_INCOMING: ExcelJSNS.Fill = {
  type: 'pattern',
  pattern: 'solid',
  fgColor: { argb: 'FFCCE5FF' },
};

/** Light green fill for outgoing doc columns */
const FILL_OUTGOING: ExcelJSNS.Fill = {
  type: 'pattern',
  pattern: 'solid',
  fgColor: { argb: 'FFC6EFCE' },
};

/** Light gray fill for neutral columns */
const FILL_GRAY: ExcelJSNS.Fill = {
  type: 'pattern',
  pattern: 'solid',
  fgColor: { argb: 'FFF2F2F2' },
};

/** Thin border style for all four sides */
const THIN_BORDER: Partial<ExcelJSNS.Borders> = {
  top: { style: 'thin', color: { argb: 'FF000000' } },
  bottom: { style: 'thin', color: { argb: 'FF000000' } },
  left: { style: 'thin', color: { argb: 'FF000000' } },
  right: { style: 'thin', color: { argb: 'FF000000' } },
};

/** Header alignment + bold */
const HEADER_FONT: Partial<ExcelJSNS.Font> = { bold: true };
const HEADER_ALIGN: Partial<ExcelJSNS.Alignment> = {
  horizontal: 'center',
  vertical: 'middle',
};

/** Data cell alignment with wrap */
const CELL_ALIGN: Partial<ExcelJSNS.Alignment> = { vertical: 'middle', wrapText: true };

// ============================================================================
// Helper functions
// ============================================================================

/** Format date string to display format (YYYY-MM-DD) */
function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '';
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
  return '未指派';
}

/** Get effective doc number for a record */
function getRecordDocNumber(record: WorkRecord): string {
  const doc = getEffectiveDoc(record);
  return doc?.doc_number || '';
}

/** Apply data cell styling (borders + wrap) to a row range */
function styleDataRange(
  ws: ExcelJSNS.Worksheet,
  startRow: number,
  endRow: number,
  startCol: number,
  endCol: number
): void {
  for (let r = startRow; r <= endRow; r++) {
    for (let c = startCol; c <= endCol; c++) {
      const cell = ws.getCell(r, c);
      cell.border = THIN_BORDER;
      cell.alignment = CELL_ALIGN;
    }
  }
}

/** Apply header styling (bold + center + fill + border) */
function styleHeaderRange(
  ws: ExcelJSNS.Worksheet,
  row: number,
  startCol: number,
  endCol: number,
  fill: ExcelJSNS.Fill
): void {
  for (let c = startCol; c <= endCol; c++) {
    const cell = ws.getCell(row, c);
    cell.font = HEADER_FONT;
    cell.alignment = HEADER_ALIGN;
    cell.border = THIN_BORDER;
    cell.fill = fill;
  }
}

// ============================================================================
// Sheet builders
// ============================================================================

/** Build Sheet 1: Correspondence Matrix */
function buildMatrixSheet(wb: ExcelJSNS.Workbook, matrixRows: CorrespondenceMatrixRow[]): void {
  const ws = wb.addWorksheet('公文對照矩陣', {
    views: [{ state: 'frozen', xSplit: 0, ySplit: 1 }],
  });

  ws.addRow([
    '序號',
    '來文字號',
    '來文日期',
    '來文主旨',
    '來文狀態',
    '→',
    '覆文字號',
    '覆文日期',
    '覆文主旨',
    '覆文狀態',
  ]);

  matrixRows.forEach((row, idx) => {
    const incoming = row.incoming;
    const outgoing = row.outgoing;
    const arrow = incoming && outgoing ? '→' : '';
    ws.addRow([
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

  // Column widths
  [5, 20, 12, 40, 8, 3, 20, 12, 40, 8].forEach((w, idx) => {
    ws.getColumn(idx + 1).width = w;
  });

  // Header colored by section
  styleHeaderRange(ws, 1, 1, 1, FILL_GRAY); // 序號
  styleHeaderRange(ws, 1, 2, 5, FILL_INCOMING); // 來文 cols
  styleHeaderRange(ws, 1, 6, 6, FILL_GRAY); // Arrow
  styleHeaderRange(ws, 1, 7, 10, FILL_OUTGOING); // 覆文 cols

  // Data row styling
  if (ws.rowCount > 1) {
    styleDataRange(ws, 2, ws.rowCount, 1, 10);
  }
}

/** Build Sheet 2: Work Records */
function buildRecordsSheet(wb: ExcelJSNS.Workbook, records: WorkRecord[]): void {
  const ws = wb.addWorksheet('作業紀錄', {
    views: [{ state: 'frozen', xSplit: 0, ySplit: 1 }],
  });

  ws.addRow(['序號', '分類', '說明', '紀錄日期', '期限日期', '狀態', '關聯公文字號']);

  const sorted = [...records].sort((a, b) => a.sort_order - b.sort_order);
  sorted.forEach((record, idx) => {
    ws.addRow([
      idx + 1,
      getCategoryLabel(record),
      record.description || '',
      formatDate(record.record_date),
      formatDate(record.deadline_date),
      statusLabel(record.status),
      getRecordDocNumber(record),
    ]);
  });

  [5, 14, 50, 12, 12, 8, 20].forEach((w, idx) => {
    ws.getColumn(idx + 1).width = w;
  });

  styleHeaderRange(ws, 1, 1, 7, FILL_GRAY);
  if (ws.rowCount > 1) {
    styleDataRange(ws, 2, ws.rowCount, 1, 7);
  }
}

/** Build Sheet 3: Statistics Summary */
function buildStatsSheet(
  wb: ExcelJSNS.Workbook,
  stats: DispatchWorkStats,
  dispatchNo?: string,
  projectName?: string
): void {
  const ws = wb.addWorksheet('統計摘要', {
    views: [{ state: 'frozen', xSplit: 0, ySplit: 1 }],
  });

  ws.addRow(['項目', '值']);

  const kvPairs: [string, string | number][] = [
    ['派工單號', dispatchNo || ''],
    ['工程名稱', projectName || ''],
    ['匯出時間', formatNow()],
    ['作業紀錄總數', stats.total],
    ['已完成', stats.completed],
    ['進行中', stats.inProgress],
    ['來文數', stats.incomingDocs],
    ['覆文數', stats.outgoingDocs],
    ['關聯公文總數', stats.linkedDocCount],
    ['未指派公文', stats.unassignedDocCount],
    ['當前階段', stats.currentStage],
  ];
  kvPairs.forEach(pair => ws.addRow(pair));

  ws.getColumn(1).width = 16;
  ws.getColumn(2).width = 40;

  styleHeaderRange(ws, 1, 1, 2, FILL_GRAY);
  if (ws.rowCount > 1) {
    styleDataRange(ws, 2, ws.rowCount, 1, 2);
  }

  // Bold the key column (column 1)
  for (let r = 2; r <= ws.rowCount; r++) {
    ws.getCell(r, 1).font = { bold: true };
  }
}

// ============================================================================
// Main export function
// ============================================================================

/**
 * Export correspondence matrix, work records, and statistics to an Excel file.
 *
 * Generates a 3-sheet workbook and triggers a browser download.
 * Uses dynamic import('exceljs') to reduce initial bundle size.
 */
export async function exportCorrespondenceMatrix(
  options: CorrespondenceExportOptions
): Promise<void> {
  const { matrixRows, records, stats, dispatchNo, projectName } = options;

  const ExcelJS = (await import('exceljs')).default;
  const { saveAs } = await import('file-saver');

  const wb = new ExcelJS.Workbook();
  buildMatrixSheet(wb, matrixRows);
  buildRecordsSheet(wb, records);
  buildStatsSheet(wb, stats, dispatchNo, projectName);

  const parts = ['公文對照'];
  if (dispatchNo) parts.push(`_${dispatchNo}`);
  if (projectName) parts.push(`_${projectName}`);
  parts.push(`_${dateTag()}`);
  const filename = `${parts.join('')}.xlsx`;

  const buf = await wb.xlsx.writeBuffer();
  saveAs(
    new Blob([buf], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }),
    filename
  );
}
