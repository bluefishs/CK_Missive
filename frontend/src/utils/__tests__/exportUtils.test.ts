/**
 * 公文匯出工具函數測試
 * Export Utils Tests
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';

// Mock dependencies before importing the module under test
vi.mock('../../api/client', () => ({
  apiClient: {
    downloadPost: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    DOCUMENTS: {
      EXPORT_EXCEL: '/documents-enhanced/export/excel',
    },
  },
}));

vi.mock('../logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    log: vi.fn(),
  },
}));

import { exportDocumentsToExcel, exportDocumentsByType } from '../exportUtils';
import { apiClient } from '../../api/client';
import { logger } from '../logger';
import type { DocumentFilter } from '../../types/document';

// ============================================================================
// Helper: build mock document
// ============================================================================

function mockDoc(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    doc_number: 'TEST-001',
    subject: '測試公文',
    doc_type: '收文',
    receive_date: '2026-01-01',
    send_date: null,
    sender: '測試機關',
    receiver: null,
    ...overrides,
  } as never;
}

// ============================================================================
// exportDocumentsToExcel
// ============================================================================

describe('exportDocumentsToExcel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('匯出全部時不應傳送 document_ids', async () => {
    const docs = [mockDoc({ id: 1 }), mockDoc({ id: 2 })];
    await exportDocumentsToExcel(docs, '測試', undefined, true);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const requestBody = call[1];
    expect(requestBody.document_ids).toBeUndefined();
  });

  it('批次匯出時應傳送 document_ids', async () => {
    const docs = [mockDoc({ id: 10 }), mockDoc({ id: 20 })];
    await exportDocumentsToExcel(docs, '測試', undefined, false);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const requestBody = call[1];
    expect(requestBody.document_ids).toEqual([10, 20]);
  });

  it('應正確傳遞 doc_type 篩選條件為 category', async () => {
    const filters: DocumentFilter = { doc_type: '收文' };
    await exportDocumentsToExcel([], '測試', filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    expect(call[1].category).toBe('收文');
  });

  it('category 欄位應覆蓋 doc_type', async () => {
    const filters: DocumentFilter = { doc_type: '收文', category: '發文' };
    await exportDocumentsToExcel([], '測試', filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    expect(call[1].category).toBe('發文');
  });

  it('應正確傳遞 year 篩選條件', async () => {
    const filters: DocumentFilter = { year: 2026 };
    await exportDocumentsToExcel([], '測試', filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    expect(call[1].year).toBe(2026);
  });

  it('應正確傳遞 keyword 篩選條件', async () => {
    const filters: DocumentFilter = { keyword: '測試關鍵字' };
    await exportDocumentsToExcel([], '測試', filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    expect(call[1].keyword).toBe('測試關鍵字');
  });

  it('search 欄位應作為 keyword 傳遞', async () => {
    const filters: DocumentFilter = { search: '搜尋詞' };
    await exportDocumentsToExcel([], '測試', filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    expect(call[1].keyword).toBe('搜尋詞');
  });

  it('應正確傳遞 contract_case, sender, receiver 篩選條件', async () => {
    const filters: DocumentFilter = {
      contract_case: '案件A',
      sender: '機關B',
      receiver: '單位C',
    };
    await exportDocumentsToExcel([], '測試', filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    expect(call[1].contract_case).toBe('案件A');
    expect(call[1].sender).toBe('機關B');
    expect(call[1].receiver).toBe('單位C');
  });

  it('檔案名稱應以 .xlsx 結尾', async () => {
    await exportDocumentsToExcel([], '我的檔案');

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toBe('我的檔案.xlsx');
  });

  it('不應重複加上 .xlsx 副檔名', async () => {
    await exportDocumentsToExcel([], '報表.xlsx');

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toBe('報表.xlsx');
    expect(filename).not.toBe('報表.xlsx.xlsx');
  });

  it('無指定檔名時應自動產生帶日期的檔名', async () => {
    await exportDocumentsToExcel([]);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toMatch(/乾坤測繪公文紀錄_\d{8}_\d{4}\.xlsx$/);
  });

  it('收文篩選時檔名前綴應為「收文記錄」', async () => {
    const filters: DocumentFilter = { doc_type: '收文' };
    await exportDocumentsToExcel([], undefined, filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toMatch(/^收文記錄_/);
  });

  it('發文篩選時檔名前綴應為「發文記錄」', async () => {
    const filters: DocumentFilter = { doc_type: '發文' };
    await exportDocumentsToExcel([], undefined, filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toMatch(/^發文記錄_/);
  });

  it('年度篩選時檔名應包含年度', async () => {
    const filters: DocumentFilter = { year: 2026 };
    await exportDocumentsToExcel([], undefined, filters);

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toMatch(/^2026年度公文清單_/);
  });

  it('API 失敗時應拋出錯誤並記錄', async () => {
    const error = new Error('下載失敗');
    (apiClient.downloadPost as Mock).mockRejectedValueOnce(error);

    await expect(exportDocumentsToExcel([])).rejects.toThrow('下載失敗');
    expect(logger.error).toHaveBeenCalledWith('匯出 Excel 失敗:', error);
  });

  it('成功匯出時應記錄 debug 訊息', async () => {
    const docs = [mockDoc({ id: 1 })];
    await exportDocumentsToExcel(docs, '測試');

    expect(logger.debug).toHaveBeenCalledWith(
      expect.stringContaining('已成功請求匯出 1 筆文件')
    );
  });
});

// ============================================================================
// exportDocumentsByType
// ============================================================================

describe('exportDocumentsByType', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('type=received 時應篩選收文類公文', async () => {
    const docs = [
      mockDoc({ id: 1, doc_type: '收文' }),
      mockDoc({ id: 2, doc_type: '發文', receive_date: null }),
    ];
    await exportDocumentsByType(docs, 'received');

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const body = call[1];
    // 收文 doc_type='收文' 一定會被選到
    expect(body.document_ids).toContain(1);
  });

  it('type=sent 時應篩選發文類公文', async () => {
    const docs = [
      mockDoc({ id: 1, doc_type: '發文', send_date: '2026-01-01' }),
      mockDoc({ id: 2, doc_type: '收文' }),
    ];
    await exportDocumentsByType(docs, 'sent');

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const body = call[1];
    expect(body.document_ids).toContain(1);
  });

  it('type=all 時應包含全部公文', async () => {
    const docs = [mockDoc({ id: 1 }), mockDoc({ id: 2 }), mockDoc({ id: 3 })];
    await exportDocumentsByType(docs, 'all');

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const body = call[1];
    expect(body.document_ids).toHaveLength(3);
  });

  it('檔名應包含日期格式 YYYYMMDD', async () => {
    await exportDocumentsByType([mockDoc()], 'all');

    const call = (apiClient.downloadPost as Mock).mock.calls[0];
    const filename = call[2] as string;
    expect(filename).toMatch(/公文總彙整_\d{8}\.xlsx$/);
  });
});
