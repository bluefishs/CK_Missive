/**
 * 派工單公文對照矩陣 Excel 匯出工具測試
 * Dispatch Export Utils Tests
 *
 * 由於 helper 函數 (formatDate, dateTag, getItemStatus, formatNow)
 * 為模組內部函數，透過 exported exportCorrespondenceMatrix 間接驗證。
 * Mock xlsx 的 aoa_to_sheet 以攔截傳入的資料陣列進行斷言。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Use vi.hoisted to define spies that can be referenced in vi.mock factories
const {
  aoa_to_sheet_spy,
  book_new_spy,
  book_append_sheet_spy,
  write_spy,
  encode_cell_spy,
} = vi.hoisted(() => ({
  aoa_to_sheet_spy: vi.fn().mockReturnValue({}),
  book_new_spy: vi.fn().mockReturnValue({ SheetNames: [], Sheets: {} }),
  book_append_sheet_spy: vi.fn(),
  write_spy: vi.fn().mockReturnValue(new ArrayBuffer(8)),
  encode_cell_spy: vi.fn().mockReturnValue('A1'),
}));

vi.mock('xlsx', () => ({
  utils: {
    aoa_to_sheet: aoa_to_sheet_spy,
    book_new: book_new_spy,
    book_append_sheet: book_append_sheet_spy,
    encode_cell: encode_cell_spy,
  },
  write: write_spy,
}));

// Mock chainUtils and chainConstants to avoid deep dependency chain
vi.mock('../../components/taoyuan/workflow/chainUtils', () => ({
  getEffectiveDoc: vi.fn((record: Record<string, unknown>) => record.document || null),
}));

vi.mock('../../components/taoyuan/workflow/chainConstants', () => ({
  getCategoryLabel: vi.fn((record: Record<string, unknown>) => record.work_category || '未分類'),
}));

// Mock browser APIs
const mockAnchor = {
  href: '',
  download: '',
  click: vi.fn(),
  remove: vi.fn(),
};

vi.stubGlobal('URL', {
  createObjectURL: vi.fn().mockReturnValue('blob:mock-url'),
  revokeObjectURL: vi.fn(),
});

vi.stubGlobal('Blob', vi.fn().mockImplementation(() => ({})));

const originalCreateElement = document.createElement.bind(document);
vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
  if (tag === 'a') return mockAnchor as unknown as HTMLAnchorElement;
  return originalCreateElement(tag);
});

vi.spyOn(document.body, 'appendChild').mockImplementation(
  (node: Node) => node,
);

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

function createMinimalOptions(overrides: Partial<CorrespondenceExportOptions> = {}): CorrespondenceExportOptions {
  return {
    matrixRows: [],
    records: [],
    stats: createMockStats(),
    ...overrides,
  };
}

// ============================================================================
// exportCorrespondenceMatrix - workbook structure
// ============================================================================

describe('exportCorrespondenceMatrix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aoa_to_sheet_spy.mockReturnValue({});
  });

  it('應建立包含 3 個工作表的 workbook', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    expect(book_new_spy).toHaveBeenCalledOnce();
    expect(book_append_sheet_spy).toHaveBeenCalledTimes(3);
  });

  it('工作表名稱應為公文對照矩陣、作業紀錄、統計摘要', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    const sheetNames = book_append_sheet_spy.mock.calls.map(
      (call: unknown[]) => call[2],
    );
    expect(sheetNames).toEqual(['公文對照矩陣', '作業紀錄', '統計摘要']);
  });

  it('應呼叫 XLSX.write 產生 xlsx 格式', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    expect(write_spy).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ bookType: 'xlsx', type: 'array' }),
    );
  });

  it('應建立 Blob 並觸發下載', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    expect(Blob).toHaveBeenCalledOnce();
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(mockAnchor.click).toHaveBeenCalledOnce();
    expect(mockAnchor.remove).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});

// ============================================================================
// Filename generation (dateTag integration)
// ============================================================================

describe('exportCorrespondenceMatrix - 檔名產生', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aoa_to_sheet_spy.mockReturnValue({});
  });

  it('無派工單號和工程名稱時，檔名應包含日期標籤', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    const filename = mockAnchor.download;
    // 格式: 公文對照_YYYYMMDD.xlsx
    expect(filename).toMatch(/^公文對照_\d{8}\.xlsx$/);
  });

  it('有派工單號時，檔名應包含派工單號', () => {
    exportCorrespondenceMatrix(
      createMinimalOptions({ dispatchNo: '001' }),
    );

    expect(mockAnchor.download).toContain('_001');
  });

  it('有工程名稱時，檔名應包含工程名稱', () => {
    exportCorrespondenceMatrix(
      createMinimalOptions({ projectName: '測試工程' }),
    );

    expect(mockAnchor.download).toContain('_測試工程');
  });

  it('同時有派工單號和工程名稱時，檔名應包含兩者', () => {
    exportCorrespondenceMatrix(
      createMinimalOptions({ dispatchNo: '002', projectName: '範例' }),
    );

    const filename = mockAnchor.download;
    expect(filename).toContain('_002');
    expect(filename).toContain('_範例');
    expect(filename).toMatch(/\.xlsx$/);
  });
});

// ============================================================================
// Sheet 1: Matrix sheet data (formatDate, getItemStatus integration)
// ============================================================================

describe('exportCorrespondenceMatrix - 矩陣工作表資料', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aoa_to_sheet_spy.mockReturnValue({});
  });

  it('矩陣表頭應包含 10 欄', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    // First call to aoa_to_sheet is for the matrix sheet
    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as string[][];
    const headers = matrixData[0]!;
    expect(headers).toHaveLength(10);
    expect(headers[0]).toBe('序號');
    expect(headers[1]).toBe('來文字號');
    expect(headers[5]).toBe('\u2192');
    expect(headers[6]).toBe('覆文字號');
  });

  it('空矩陣應只有表頭列', () => {
    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows: [] }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    expect(matrixData).toHaveLength(1);
  });

  it('有配對資料時應產生正確的序號', () => {
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
        incoming: {
          docId: 3,
          docNumber: 'IN-002',
          isUnassigned: true,
        },
        outgoing: undefined,
      },
    ];

    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    // Header + 2 data rows
    expect(matrixData).toHaveLength(3);
    // Row 1: sequence number
    expect(matrixData[1]![0]).toBe(1);
    expect(matrixData[2]![0]).toBe(2);
  });

  it('來文日期應截取前 10 字元 (formatDate)', () => {
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

    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    // Column 2 = 來文日期
    expect(matrixData[1]![2]).toBe('2026-03-15');
  });

  it('已指派紀錄的狀態應顯示「已指派」(getItemStatus)', () => {
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

    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    // Column 4 = 來文狀態
    expect(matrixData[1]![4]).toBe('已指派');
  });

  it('未指派公文的狀態應顯示「未指派」(getItemStatus)', () => {
    const matrixRows = [
      {
        incoming: {
          docId: 1,
          docNumber: 'IN-001',
          subject: '測試',
          isUnassigned: true,
        },
        outgoing: undefined,
      },
    ];

    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    expect(matrixData[1]![4]).toBe('未指派');
  });

  it('有來文和覆文配對時，箭頭欄應為 unicode 箭頭', () => {
    const matrixRows = [
      {
        incoming: { docId: 1, docNumber: 'IN', isUnassigned: false },
        outgoing: { docId: 2, docNumber: 'OUT', isUnassigned: false },
      },
    ];

    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    expect(matrixData[1]![5]).toBe('\u2192');
  });

  it('只有來文無覆文時，箭頭欄應為空', () => {
    const matrixRows = [
      {
        incoming: { docId: 1, docNumber: 'IN', isUnassigned: false },
        outgoing: undefined,
      },
    ];

    exportCorrespondenceMatrix(createMinimalOptions({ matrixRows }));

    const matrixData = aoa_to_sheet_spy.mock.calls[0][0] as unknown[][];
    expect(matrixData[1]![5]).toBe('');
  });
});

// ============================================================================
// Sheet 2: Records sheet data
// ============================================================================

describe('exportCorrespondenceMatrix - 作業紀錄工作表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aoa_to_sheet_spy.mockReturnValue({});
  });

  it('紀錄表頭應包含 7 欄', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    // Second call to aoa_to_sheet is for the records sheet
    const recordsData = aoa_to_sheet_spy.mock.calls[1][0] as string[][];
    expect(recordsData[0]).toHaveLength(7);
    expect(recordsData[0]![0]).toBe('序號');
    expect(recordsData[0]![1]).toBe('分類');
    expect(recordsData[0]![6]).toBe('關聯公文字號');
  });

  it('紀錄應按 sort_order 排序', () => {
    const records = [
      { id: 1, sort_order: 3, status: 'pending', record_date: '2026-01-03', description: 'C', milestone_type: 'general', dispatch_order_id: 1 },
      { id: 2, sort_order: 1, status: 'completed', record_date: '2026-01-01', description: 'A', milestone_type: 'general', dispatch_order_id: 1 },
      { id: 3, sort_order: 2, status: 'in_progress', record_date: '2026-01-02', description: 'B', milestone_type: 'general', dispatch_order_id: 1 },
    ] as never[];

    exportCorrespondenceMatrix(createMinimalOptions({ records }));

    const recordsData = aoa_to_sheet_spy.mock.calls[1][0] as unknown[][];
    // 排序後序號: 1=sort_order 1, 2=sort_order 2, 3=sort_order 3
    expect(recordsData[1]![0]).toBe(1); // sort_order 1
    expect(recordsData[2]![0]).toBe(2); // sort_order 2
    expect(recordsData[3]![0]).toBe(3); // sort_order 3
  });

  it('狀態應翻譯為中文', () => {
    const records = [
      { id: 1, sort_order: 1, status: 'completed', record_date: '2026-01-01', description: '完成項目', milestone_type: 'general', dispatch_order_id: 1 },
    ] as never[];

    exportCorrespondenceMatrix(createMinimalOptions({ records }));

    const recordsData = aoa_to_sheet_spy.mock.calls[1][0] as unknown[][];
    expect(recordsData[1]![5]).toBe('已完成');
  });

  it('未知狀態應保留原始值', () => {
    const records = [
      { id: 1, sort_order: 1, status: 'unknown_status', record_date: '2026-01-01', description: '', milestone_type: 'general', dispatch_order_id: 1 },
    ] as never[];

    exportCorrespondenceMatrix(createMinimalOptions({ records }));

    const recordsData = aoa_to_sheet_spy.mock.calls[1][0] as unknown[][];
    expect(recordsData[1]![5]).toBe('unknown_status');
  });
});

// ============================================================================
// Sheet 3: Stats sheet data
// ============================================================================

describe('exportCorrespondenceMatrix - 統計摘要工作表', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aoa_to_sheet_spy.mockReturnValue({});
  });

  it('統計表頭應為「項目」和「值」', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    // Third call to aoa_to_sheet is for the stats sheet
    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as string[][];
    expect(statsData[0]).toEqual(['項目', '值']);
  });

  it('應包含 12 個統計項目', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as unknown[][];
    // Header + 12 data rows
    expect(statsData).toHaveLength(13);
  });

  it('派工單號應出現在統計項目中', () => {
    exportCorrespondenceMatrix(
      createMinimalOptions({ dispatchNo: 'D-100' }),
    );

    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as unknown[][];
    const dispatchRow = statsData.find((row) => row[0] === '派工單號');
    expect(dispatchRow).toBeDefined();
    expect(dispatchRow![1]).toBe('D-100');
  });

  it('工程名稱應出現在統計項目中', () => {
    exportCorrespondenceMatrix(
      createMinimalOptions({ projectName: '測試工程ABC' }),
    );

    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as unknown[][];
    const projectRow = statsData.find((row) => row[0] === '工程名稱');
    expect(projectRow).toBeDefined();
    expect(projectRow![1]).toBe('測試工程ABC');
  });

  it('統計數值應正確對應', () => {
    const stats = createMockStats({
      total: 20,
      completed: 8,
      inProgress: 7,
      overdue: 3,
    });

    exportCorrespondenceMatrix(createMinimalOptions({ stats }));

    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as unknown[][];
    const findValue = (key: string) =>
      statsData.find((row) => row[0] === key)?.[1];

    expect(findValue('作業紀錄總數')).toBe(20);
    expect(findValue('已完成')).toBe(8);
    expect(findValue('進行中')).toBe(7);
    expect(findValue('逾期')).toBe(3);
  });

  it('匯出時間應為 YYYY-MM-DD HH:mm:ss 格式 (formatNow)', () => {
    exportCorrespondenceMatrix(createMinimalOptions());

    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as unknown[][];
    const exportTimeRow = statsData.find((row) => row[0] === '匯出時間');
    expect(exportTimeRow).toBeDefined();
    const exportTime = exportTimeRow![1] as string;
    // formatNow 格式: YYYY-MM-DD HH:mm:ss
    expect(exportTime).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });

  it('當前階段應正確顯示', () => {
    const stats = createMockStats({ currentStage: '查估階段' });
    exportCorrespondenceMatrix(createMinimalOptions({ stats }));

    const statsData = aoa_to_sheet_spy.mock.calls[2][0] as unknown[][];
    const stageRow = statsData.find((row) => row[0] === '當前階段');
    expect(stageRow![1]).toBe('查估階段');
  });
});
