/**
 * 派工單公文對照矩陣 Excel 匯出工具測試
 * Dispatch Export Utils Tests
 *
 * 由於 helper 函數 (formatDate, dateTag, getItemStatus, formatNow)
 * 為模組內部函數，透過 exported exportCorrespondenceMatrix 間接驗證。
 *
 * v2.0 (2026-05-21) — 從 xlsx (SheetJS) 遷至 ExcelJS（CVE GHSA-4r6h-8v6p-xvw6 / GHSA-5pgg-2g8v-p4x9）
 * 測試策略：跑真 ExcelJS，spy Workbook prototype 攔截 addWorksheet / addRow 的呼叫；mock file-saver 攔截 filename。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---- Capture saveAs ---------------------------------------------------------
const { saveAs_spy } = vi.hoisted(() => ({
  saveAs_spy: vi.fn(),
}));

vi.mock('file-saver', () => ({
  saveAs: saveAs_spy,
  default: { saveAs: saveAs_spy },
}));

// ---- Capture ExcelJS workbook structure -------------------------------------
// 用真 ExcelJS 跑，但 spy Worksheet.addRow 攔截每 sheet 加入的資料列。
import ExcelJS from 'exceljs';

const sheetCaptures: Array<{ name: string; rows: unknown[][] }> = [];

const originalAddWorksheet = ExcelJS.Workbook.prototype.addWorksheet;
vi.spyOn(ExcelJS.Workbook.prototype, 'addWorksheet').mockImplementation(function (
  this: ExcelJS.Workbook,
  name?: string,
  options?: Partial<ExcelJS.AddWorksheetOptions>
) {
  // 呼叫原本實作建立 worksheet
  const ws = originalAddWorksheet.call(this, name, options);
  const capture = { name: name || `Sheet${sheetCaptures.length + 1}`, rows: [] as unknown[][] };
  sheetCaptures.push(capture);

  // 攔截 addRow 把資料收進 capture
  const origAddRow = ws.addRow.bind(ws);
  ws.addRow = function (values: unknown) {
    if (Array.isArray(values)) capture.rows.push(values);
    return origAddRow(values as never);
  } as typeof ws.addRow;
  return ws;
});

// ---- Mock chainUtils + chainConstants ----------------------------------------
vi.mock('../../components/taoyuan/workflow/chainUtils', () => ({
  getEffectiveDoc: vi.fn((record: Record<string, unknown>) => record.document || null),
}));

vi.mock('../../components/taoyuan/workflow/chainConstants', () => ({
  getCategoryLabel: vi.fn((record: Record<string, unknown>) => record.work_category || '未分類'),
}));

import { exportCorrespondenceMatrix } from '../dispatchExportUtils';
import type { CorrespondenceExportOptions } from '../dispatchExportUtils';
import type { DispatchWorkStats } from '../../components/taoyuan/workflow/useDispatchWorkData';

// ============================================================================
// Test data factories
// ============================================================================

function createMockStats(overrides: Partial<DispatchWorkStats> = {}): DispatchWorkStats {
  return {
    total: 10,
    completed: 5,
    inProgress: 3,
    overdue: 1,
    onHold: 1,
    incomingDocs: 4,
    outgoingDocs: 3,
    linkedDocCount: 7,
    unassignedDocCount: 2,
    currentStage: '作業中',
    ...overrides,
  };
}

function createMinimalOptions(
  overrides: Partial<CorrespondenceExportOptions> = {}
): CorrespondenceExportOptions {
  return {
    matrixRows: [],
    records: [],
    stats: createMockStats(),
    ...overrides,
  };
}

function findSheet(name: string) {
  return sheetCaptures.find(s => s.name === name);
}

// ============================================================================
// exportCorrespondenceMatrix - workbook structure
// ============================================================================

describe('exportCorrespondenceMatrix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sheetCaptures.length = 0;
  });

  it('應建立包含 3 個工作表的 workbook', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    expect(sheetCaptures).toHaveLength(3);
  });

  it('工作表名稱應為公文對照矩陣、作業紀錄、統計摘要', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const sheetNames = sheetCaptures.map(s => s.name);
    expect(sheetNames).toEqual(['公文對照矩陣', '作業紀錄', '統計摘要']);
  });

  it('應呼叫 file-saver.saveAs 觸發下載', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    expect(saveAs_spy).toHaveBeenCalledOnce();
    const call = saveAs_spy.mock.calls[0]!;
    expect(call[0]).toBeInstanceOf(Blob); // blob
    expect(typeof call[1]).toBe('string'); // filename
  });

  it('Blob MIME type 應為 xlsx', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const blob = saveAs_spy.mock.calls[0]![0] as Blob;
    expect(blob.type).toBe('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  });
});

// ============================================================================
// Filename generation (dateTag integration)
// ============================================================================

describe('exportCorrespondenceMatrix - 檔名產生', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sheetCaptures.length = 0;
  });

  it('無派工單號和工程名稱時，檔名應包含日期標籤', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const filename = saveAs_spy.mock.calls[0]![1] as string;
    expect(filename).toMatch(/^公文對照_\d{8}\.xlsx$/);
  });

  it('有派工單號時，檔名應包含派工單號', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions({ dispatchNo: '001' }));
    const filename = saveAs_spy.mock.calls[0]![1] as string;
    expect(filename).toContain('_001');
  });

  it('有工程名稱時，檔名應包含工程名稱', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions({ projectName: '測試工程' }));
    const filename = saveAs_spy.mock.calls[0]![1] as string;
    expect(filename).toContain('_測試工程');
  });

  it('同時有派工單號和工程名稱時，檔名應包含兩者', async () => {
    await exportCorrespondenceMatrix(
      createMinimalOptions({ dispatchNo: '002', projectName: '範例' })
    );
    const filename = saveAs_spy.mock.calls[0]![1] as string;
    expect(filename).toContain('_002');
    expect(filename).toContain('_範例');
    expect(filename).toMatch(/\.xlsx$/);
  });
});

// ============================================================================
// Sheet 1: Matrix sheet data
// ============================================================================

describe('exportCorrespondenceMatrix - 矩陣工作表資料', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sheetCaptures.length = 0;
  });

  it('矩陣表頭應包含 10 欄', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const matrix = findSheet('公文對照矩陣');
    expect(matrix).toBeDefined();
    const headers = matrix!.rows[0]!;
    expect(headers).toHaveLength(10);
    expect(headers[0]).toBe('序號');
    expect(headers[1]).toBe('來文字號');
    expect(headers[5]).toBe('→');
    expect(headers[6]).toBe('覆文字號');
  });

  it('空矩陣應只有表頭列', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows: [] }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows).toHaveLength(1);
  });

  it('有配對資料時應產生正確的序號', async () => {
    const matrixRows = [
      {
        incoming: {
          docId: 1,
          docNumber: 'IN-001',
          docDate: '2026-01-15T00:00:00',
          subject: '來文主旨',
          isUnassigned: false,
          record: { id: 1 } as never,
        },
        outgoing: {
          docId: 2,
          docNumber: 'OUT-001',
          docDate: '2026-01-20',
          subject: '覆文主旨',
          isUnassigned: false,
          record: { id: 2 } as never,
        },
      },
      {
        incoming: { docId: 3, docNumber: 'IN-002', isUnassigned: true },
        outgoing: undefined,
      },
    ];
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows).toHaveLength(3); // 1 header + 2 data rows
    expect(matrix!.rows[1]![0]).toBe(1);
    expect(matrix!.rows[2]![0]).toBe(2);
  });

  it('來文日期應截取前 10 字元 (formatDate)', async () => {
    const matrixRows = [
      {
        incoming: {
          docId: 1,
          docNumber: 'IN-001',
          docDate: '2026-03-15T08:30:00.000Z',
          subject: '測試',
          isUnassigned: false,
        },
        outgoing: undefined,
      },
    ];
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows[1]![2]).toBe('2026-03-15');
  });

  it('已指派紀錄的狀態應顯示「已指派」(getItemStatus)', async () => {
    const matrixRows = [
      {
        incoming: {
          docId: 1,
          docNumber: 'IN-001',
          subject: '測試',
          isUnassigned: false,
          record: { id: 1 } as never,
        },
        outgoing: undefined,
      },
    ];
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows[1]![4]).toBe('已指派');
  });

  it('未指派公文的狀態應顯示「未指派」(getItemStatus)', async () => {
    const matrixRows = [
      {
        incoming: { docId: 1, docNumber: 'IN-001', subject: '測試', isUnassigned: true },
        outgoing: undefined,
      },
    ];
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows[1]![4]).toBe('未指派');
  });

  it('有來文和覆文配對時，箭頭欄應為 unicode 箭頭', async () => {
    const matrixRows = [
      {
        incoming: { docId: 1, docNumber: 'IN', isUnassigned: false },
        outgoing: { docId: 2, docNumber: 'OUT', isUnassigned: false },
      },
    ];
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows[1]![5]).toBe('→');
  });

  it('只有來文無覆文時，箭頭欄應為空', async () => {
    const matrixRows = [
      {
        incoming: { docId: 1, docNumber: 'IN', isUnassigned: false },
        outgoing: undefined,
      },
    ];
    await exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));
    const matrix = findSheet('公文對照矩陣');
    expect(matrix!.rows[1]![5]).toBe('');
  });
});

// ============================================================================
// Sheet 2: Records sheet data
// ============================================================================

describe('exportCorrespondenceMatrix - 作業紀錄工作表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sheetCaptures.length = 0;
  });

  it('紀錄表頭應包含 7 欄', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const records = findSheet('作業紀錄');
    expect(records!.rows[0]).toHaveLength(7);
    expect(records!.rows[0]![0]).toBe('序號');
    expect(records!.rows[0]![1]).toBe('分類');
    expect(records!.rows[0]![6]).toBe('關聯公文字號');
  });

  it('紀錄應按 sort_order 排序', async () => {
    const recordsInput = [
      {
        id: 1,
        sort_order: 3,
        status: 'pending',
        record_date: '2026-01-03',
        description: 'C',
        milestone_type: 'general',
        dispatch_order_id: 1,
      },
      {
        id: 2,
        sort_order: 1,
        status: 'completed',
        record_date: '2026-01-01',
        description: 'A',
        milestone_type: 'general',
        dispatch_order_id: 1,
      },
      {
        id: 3,
        sort_order: 2,
        status: 'in_progress',
        record_date: '2026-01-02',
        description: 'B',
        milestone_type: 'general',
        dispatch_order_id: 1,
      },
    ] as never[];
    await exportCorrespondenceMatrix(createMinimalOptions({ records: recordsInput }));
    const records = findSheet('作業紀錄');
    expect(records!.rows[1]![0]).toBe(1);
    expect(records!.rows[2]![0]).toBe(2);
    expect(records!.rows[3]![0]).toBe(3);
  });

  it('狀態應翻譯為中文', async () => {
    const recordsInput = [
      {
        id: 1,
        sort_order: 1,
        status: 'completed',
        record_date: '2026-01-01',
        description: '完成項目',
        milestone_type: 'general',
        dispatch_order_id: 1,
      },
    ] as never[];
    await exportCorrespondenceMatrix(createMinimalOptions({ records: recordsInput }));
    const records = findSheet('作業紀錄');
    expect(records!.rows[1]![5]).toBe('已完成');
  });

  it('未知狀態應保留原始值', async () => {
    const recordsInput = [
      {
        id: 1,
        sort_order: 1,
        status: 'unknown_status',
        record_date: '2026-01-01',
        description: '',
        milestone_type: 'general',
        dispatch_order_id: 1,
      },
    ] as never[];
    await exportCorrespondenceMatrix(createMinimalOptions({ records: recordsInput }));
    const records = findSheet('作業紀錄');
    expect(records!.rows[1]![5]).toBe('unknown_status');
  });
});

// ============================================================================
// Sheet 3: Stats sheet data
// ============================================================================

describe('exportCorrespondenceMatrix - 統計摘要工作表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sheetCaptures.length = 0;
  });

  it('統計表頭應為「項目」和「值」', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const stats = findSheet('統計摘要');
    expect(stats!.rows[0]).toEqual(['項目', '值']);
  });

  it('應包含 12 個統計項目', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const stats = findSheet('統計摘要');
    expect(stats!.rows).toHaveLength(12); // 1 header + 11 data rows (逾期已隱藏)
  });

  it('派工單號應出現在統計項目中', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions({ dispatchNo: 'D-100' }));
    const stats = findSheet('統計摘要');
    const dispatchRow = stats!.rows.find(row => row[0] === '派工單號');
    expect(dispatchRow).toBeDefined();
    expect(dispatchRow![1]).toBe('D-100');
  });

  it('工程名稱應出現在統計項目中', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions({ projectName: '測試工程ABC' }));
    const stats = findSheet('統計摘要');
    const projectRow = stats!.rows.find(row => row[0] === '工程名稱');
    expect(projectRow).toBeDefined();
    expect(projectRow![1]).toBe('測試工程ABC');
  });

  it('統計數值應正確對應', async () => {
    const statsInput = createMockStats({ total: 20, completed: 8, inProgress: 7 });
    await exportCorrespondenceMatrix(createMinimalOptions({ stats: statsInput }));
    const stats = findSheet('統計摘要');
    const findValue = (key: string) => stats!.rows.find(row => row[0] === key)?.[1];
    expect(findValue('作業紀錄總數')).toBe(20);
    expect(findValue('已完成')).toBe(8);
    expect(findValue('進行中')).toBe(7);
  });

  it('匯出時間應為 YYYY-MM-DD HH:mm:ss 格式 (formatNow)', async () => {
    await exportCorrespondenceMatrix(createMinimalOptions());
    const stats = findSheet('統計摘要');
    const exportTimeRow = stats!.rows.find(row => row[0] === '匯出時間');
    expect(exportTimeRow).toBeDefined();
    expect(exportTimeRow![1]).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });

  it('當前階段應正確顯示', async () => {
    const statsInput = createMockStats({ currentStage: '查估階段' });
    await exportCorrespondenceMatrix(createMinimalOptions({ stats: statsInput }));
    const stats = findSheet('統計摘要');
    const stageRow = stats!.rows.find(row => row[0] === '當前階段');
    expect(stageRow![1]).toBe('查估階段');
  });
});
