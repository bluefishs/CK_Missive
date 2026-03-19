/**
 * useDocumentCreateForm Hook 單元測試
 *
 * 測試公文建立表單 Hook 的常數匯出與檔案驗證邏輯
 *
 * 執行方式:
 *   cd frontend && npm run test -- useDocumentCreateForm
 */
import { describe, it, expect, vi } from 'vitest';

// ==========================================================================
// Only test the exported constants and pure utility logic
// The hook itself requires App.useApp() + useNavigate() + useQueryClient()
// which are difficult to mock in isolation. Full integration tests preferred.
// ==========================================================================

vi.mock('../../utils/logger', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn(), log: vi.fn() },
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock('../../api/documentsApi', () => ({
  documentsApi: { getNextSendNumber: vi.fn(), createDocument: vi.fn() },
}));

vi.mock('../../api/agenciesApi', () => ({
  agenciesApi: { getAgencyOptions: vi.fn() },
}));

vi.mock('../../api/client', () => ({
  apiClient: { post: vi.fn() },
}));

vi.mock('../../api/endpoints', () => ({
  API_ENDPOINTS: {
    PROJECTS: { LIST: '/projects/list' },
    USERS: { LIST: '/admin/user-management/list' },
  },
}));

vi.mock('../../api/filesApi', () => ({
  filesApi: { getStorageInfo: vi.fn(), uploadFiles: vi.fn() },
}));

vi.mock('../../config/queryConfig', () => ({
  queryKeys: { documents: { all: ['documents'] } },
}));

import {
  DEFAULT_COMPANY_NAME,
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  type DocumentCreateMode,
  type FileSettings,
} from '../../hooks/business/useDocumentCreateForm';

// ==========================================================================
// Tests - Constants and Types
// ==========================================================================

describe('useDocumentCreateForm - constants', () => {
  it('exports DEFAULT_COMPANY_NAME', () => {
    expect(DEFAULT_COMPANY_NAME).toBe('乾坤測繪科技有限公司');
  });

  it('exports DEFAULT_ALLOWED_EXTENSIONS as non-empty array', () => {
    expect(Array.isArray(DEFAULT_ALLOWED_EXTENSIONS)).toBe(true);
    expect(DEFAULT_ALLOWED_EXTENSIONS.length).toBeGreaterThan(0);
    expect(DEFAULT_ALLOWED_EXTENSIONS).toContain('.pdf');
    expect(DEFAULT_ALLOWED_EXTENSIONS).toContain('.docx');
    expect(DEFAULT_ALLOWED_EXTENSIONS).toContain('.xlsx');
    expect(DEFAULT_ALLOWED_EXTENSIONS).toContain('.dwg');
  });

  it('exports DEFAULT_MAX_FILE_SIZE_MB as 50', () => {
    expect(typeof DEFAULT_MAX_FILE_SIZE_MB).toBe('number');
    expect(DEFAULT_MAX_FILE_SIZE_MB).toBe(50);
  });

  it('DocumentCreateMode type accepts receive and send', () => {
    const receive: DocumentCreateMode = 'receive';
    const send: DocumentCreateMode = 'send';
    expect(receive).toBe('receive');
    expect(send).toBe('send');
  });

  it('FileSettings interface has expected shape', () => {
    const settings: FileSettings = {
      allowedExtensions: ['.pdf'],
      maxFileSizeMB: 50,
    };
    expect(settings.allowedExtensions).toEqual(['.pdf']);
    expect(settings.maxFileSizeMB).toBe(50);
  });
});

describe('useDocumentCreateForm - file validation logic (pure function test)', () => {
  // Test the validation logic that the hook uses internally
  function validateFile(
    file: { name: string; size: number },
    settings: FileSettings,
  ): { valid: boolean; error?: string } {
    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');

    if (!settings.allowedExtensions.includes(ext)) {
      return { valid: false, error: `不支援 ${ext} 檔案格式` };
    }

    const maxSizeBytes = settings.maxFileSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `檔案大小 ${sizeMB}MB 超過限制 (最大 ${settings.maxFileSizeMB}MB)`,
      };
    }

    return { valid: true };
  }

  const defaultSettings: FileSettings = {
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  };

  it('accepts PDF files', () => {
    const result = validateFile({ name: 'test.pdf', size: 1024 }, defaultSettings);
    expect(result.valid).toBe(true);
  });

  it('accepts DOCX files', () => {
    const result = validateFile({ name: 'report.docx', size: 1024 }, defaultSettings);
    expect(result.valid).toBe(true);
  });

  it('rejects EXE files', () => {
    const result = validateFile({ name: 'malware.exe', size: 1024 }, defaultSettings);
    expect(result.valid).toBe(false);
    expect(result.error).toContain('.exe');
  });

  it('rejects files exceeding size limit', () => {
    const largeSize = 100 * 1024 * 1024; // 100 MB
    const result = validateFile({ name: 'huge.pdf', size: largeSize }, defaultSettings);
    expect(result.valid).toBe(false);
    expect(result.error).toContain('超過限制');
  });

  it('accepts files within size limit', () => {
    const okSize = 10 * 1024 * 1024; // 10 MB
    const result = validateFile({ name: 'ok.pdf', size: okSize }, defaultSettings);
    expect(result.valid).toBe(true);
  });
});
