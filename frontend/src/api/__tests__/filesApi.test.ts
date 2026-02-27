/**
 * filesApi 單元測試
 * filesApi Unit Tests
 *
 * 測試檔案管理 API 服務層方法
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/filesApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    downloadPost: vi.fn(),
    uploadWithProgress: vi.fn(),
    postBlob: vi.fn(),
  },
}));

// Mock endpoints
vi.mock('../endpoints', () => ({
  API_ENDPOINTS: {
    FILES: {
      STORAGE_INFO: '/files/storage-info',
      UPLOAD: (docId: number) => `/files/upload?document_id=${docId}`,
      DOCUMENT_ATTACHMENTS: (docId: number) => `/files/document/${docId}`,
      DOWNLOAD: (id: number) => `/files/${id}/download`,
      DELETE: (id: number) => `/files/${id}/delete`,
      VERIFY: (id: number) => `/files/verify/${id}`,
      CHECK_NETWORK: '/files/check-network',
    },
  },
}));

import { filesApi } from '../filesApi';
import { apiClient } from '../client';

// ============================================================================
// Mock 資料
// ============================================================================

const mockStorageInfo = {
  allowed_extensions: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png'],
  max_file_size_mb: 50,
  storage_type: 'network',
  storage_path: '\\\\nas\\documents',
};

const mockAttachment = {
  id: 1,
  document_id: 10,
  original_filename: '測試文件.pdf',
  stored_filename: 'abc123.pdf',
  file_size: 1024000,
  content_type: 'application/pdf',
  upload_date: '2026-01-15T00:00:00Z',
  checksum: 'sha256:abc123',
};

// ============================================================================
// filesApi.getStorageInfo 測試
// ============================================================================

describe('filesApi.getStorageInfo', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filesApi.clearCache();
  });

  it('應該呼叫 storage-info 端點並返回結果', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    const result = await filesApi.getStorageInfo();

    expect(apiClient.post).toHaveBeenCalledWith('/files/storage-info', {});
    expect(result.allowed_extensions).toContain('.pdf');
    expect(result.max_file_size_mb).toBe(50);
  });

  it('第二次呼叫應使用快取（不再發送 API 請求）', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    await filesApi.getStorageInfo();
    await filesApi.getStorageInfo();

    expect(apiClient.post).toHaveBeenCalledTimes(1);
  });

  it('forceRefresh=true 時應忽略快取重新請求', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    await filesApi.getStorageInfo();
    await filesApi.getStorageInfo(true);

    expect(apiClient.post).toHaveBeenCalledTimes(2);
  });

  it('clearCache 後應重新請求', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    await filesApi.getStorageInfo();
    filesApi.clearCache();
    await filesApi.getStorageInfo();

    expect(apiClient.post).toHaveBeenCalledTimes(2);
  });
});

// ============================================================================
// filesApi.getAllowedExtensions 測試
// ============================================================================

describe('filesApi.getAllowedExtensions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filesApi.clearCache();
  });

  it('應該從 storageInfo 中提取允許的副檔名', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    const result = await filesApi.getAllowedExtensions();

    expect(result).toEqual(mockStorageInfo.allowed_extensions);
  });
});

// ============================================================================
// filesApi.getMaxFileSizeMB 測試
// ============================================================================

describe('filesApi.getMaxFileSizeMB', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filesApi.clearCache();
  });

  it('應該從 storageInfo 中提取最大檔案大小', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    const result = await filesApi.getMaxFileSizeMB();

    expect(result).toBe(50);
  });
});

// ============================================================================
// filesApi.validateFile 測試
// ============================================================================

describe('filesApi.validateFile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filesApi.clearCache();
  });

  it('合法 PDF 檔案應通過驗證', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    // 預設 File size 很小，會通過大小檢查
    const result = await filesApi.validateFile(file);

    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it('不支援的副檔名應驗證失敗', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    const file = new File(['content'], 'test.exe', { type: 'application/octet-stream' });
    const result = await filesApi.validateFile(file);

    expect(result.valid).toBe(false);
    expect(result.error).toContain('.exe');
    expect(result.error).toContain('不支援');
  });

  it('超過大小限制的檔案應驗證失敗', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ ...mockStorageInfo, max_file_size_mb: 0.0001 });

    // 建立一個有實際大小的 File（字串內容）
    const content = 'x'.repeat(200);
    const file = new File([content], 'large.pdf', { type: 'application/pdf' });
    const result = await filesApi.validateFile(file);

    expect(result.valid).toBe(false);
    expect(result.error).toContain('超過限制');
  });
});

// ============================================================================
// filesApi.uploadFiles 測試
// ============================================================================

describe('filesApi.uploadFiles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filesApi.clearCache();
  });

  it('空檔案列表應直接返回成功', async () => {
    const result = await filesApi.uploadFiles(1, []);

    expect(result.success).toBe(true);
    expect(result.message).toBe('無檔案上傳');
    expect(result.files).toEqual([]);
    expect(apiClient.uploadWithProgress).not.toHaveBeenCalled();
  });

  it('應該呼叫 uploadWithProgress 並傳遞正確參數', async () => {
    const mockResult = {
      success: true,
      message: '上傳完成',
      files: [{ id: 1, filename: 'test.pdf' }],
      errors: [],
    };
    vi.mocked(apiClient.uploadWithProgress).mockResolvedValue(mockResult);

    const file = new File(['content'], 'test.pdf');
    const result = await filesApi.uploadFiles(10, [file]);

    expect(apiClient.uploadWithProgress).toHaveBeenCalledWith(
      '/files/upload?document_id=10',
      [file],
      'files',
      undefined
    );
    expect(result.success).toBe(true);
  });

  it('應該正確傳遞 onProgress 回調', async () => {
    const mockResult = { success: true, message: '', files: [], errors: [] };
    vi.mocked(apiClient.uploadWithProgress).mockResolvedValue(mockResult);

    const onProgress = vi.fn();
    const file = new File(['content'], 'test.pdf');
    await filesApi.uploadFiles(10, [file], { onProgress });

    expect(apiClient.uploadWithProgress).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(Array),
      'files',
      onProgress
    );
  });

  it('上傳成功時應呼叫 onSuccess 回調', async () => {
    const mockResult = { success: true, message: '完成', files: [], errors: [] };
    vi.mocked(apiClient.uploadWithProgress).mockResolvedValue(mockResult);

    const onSuccess = vi.fn();
    const file = new File(['content'], 'test.pdf');
    await filesApi.uploadFiles(10, [file], { onSuccess });

    expect(onSuccess).toHaveBeenCalledWith(mockResult);
  });

  it('上傳失敗時應呼叫 onError 回調並拋出錯誤', async () => {
    const uploadError = new Error('上傳失敗：網路中斷');
    vi.mocked(apiClient.uploadWithProgress).mockRejectedValue(uploadError);

    const onError = vi.fn();
    const file = new File(['content'], 'test.pdf');

    await expect(
      filesApi.uploadFiles(10, [file], { onError })
    ).rejects.toThrow('上傳失敗：網路中斷');

    expect(onError).toHaveBeenCalledWith(uploadError);
  });

  it('非 Error 類型的錯誤應被包裝為 Error', async () => {
    vi.mocked(apiClient.uploadWithProgress).mockRejectedValue('字串錯誤');

    const onError = vi.fn();
    const file = new File(['content'], 'test.pdf');

    await expect(
      filesApi.uploadFiles(10, [file], { onError })
    ).rejects.toThrow('上傳失敗');

    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });
});

// ============================================================================
// filesApi.getDocumentAttachments 測試
// ============================================================================

describe('filesApi.getDocumentAttachments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫正確的端點並返回附件列表', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      attachments: [mockAttachment],
    });

    const result = await filesApi.getDocumentAttachments(10);

    expect(apiClient.post).toHaveBeenCalledWith('/files/document/10', {});
    expect(result).toHaveLength(1);
    expect(result[0]?.original_filename).toBe('測試文件.pdf');
  });

  it('回應中沒有 attachments 時應返回空陣列', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({});

    const result = await filesApi.getDocumentAttachments(99);

    expect(result).toEqual([]);
  });
});

// ============================================================================
// filesApi.downloadAttachment 測試
// ============================================================================

describe('filesApi.downloadAttachment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫 downloadPost 並傳遞正確的附件 ID 和檔名', async () => {
    vi.mocked(apiClient.downloadPost).mockResolvedValue(undefined);

    await filesApi.downloadAttachment(5, '文件.pdf');

    expect(apiClient.downloadPost).toHaveBeenCalledWith(
      '/files/5/download',
      {},
      '文件.pdf'
    );
  });

  it('檔名為空字串時應使用預設值 download', async () => {
    vi.mocked(apiClient.downloadPost).mockResolvedValue(undefined);

    await filesApi.downloadAttachment(5, '');

    expect(apiClient.downloadPost).toHaveBeenCalledWith(
      '/files/5/download',
      {},
      'download'
    );
  });
});

// ============================================================================
// filesApi.getAttachmentBlob 測試
// ============================================================================

describe('filesApi.getAttachmentBlob', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫 postBlob 並返回 Blob', async () => {
    const mockBlob = new Blob(['pdf content'], { type: 'application/pdf' });
    vi.mocked(apiClient.postBlob).mockResolvedValue(mockBlob);

    const result = await filesApi.getAttachmentBlob(7);

    expect(apiClient.postBlob).toHaveBeenCalledWith('/files/7/download');
    expect(result).toBeInstanceOf(Blob);
  });
});

// ============================================================================
// filesApi.deleteAttachment 測試
// ============================================================================

describe('filesApi.deleteAttachment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫刪除端點並返回結果', async () => {
    const mockResult = { success: true, message: '刪除成功' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResult);

    const result = await filesApi.deleteAttachment(3);

    expect(apiClient.post).toHaveBeenCalledWith('/files/3/delete', {});
    expect(result.success).toBe(true);
  });
});

// ============================================================================
// filesApi.verifyAttachment 測試
// ============================================================================

describe('filesApi.verifyAttachment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫驗證端點並返回結果', async () => {
    const mockResult = {
      valid: true,
      file_exists: true,
      checksum_match: true,
      message: '檔案完整性驗證通過',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResult);

    const result = await filesApi.verifyAttachment(8);

    expect(apiClient.post).toHaveBeenCalledWith('/files/verify/8', {});
    expect((result as any).valid).toBe(true);
    expect((result as any).checksum_match).toBe(true);
  });
});

// ============================================================================
// filesApi.checkNetworkStorage 測試
// ============================================================================

describe('filesApi.checkNetworkStorage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('應該呼叫網路檢查端點並返回結果', async () => {
    const mockResult = {
      accessible: true,
      latency_ms: 15,
      storage_type: 'network',
      message: '網路儲存正常',
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResult);

    const result = await filesApi.checkNetworkStorage();

    expect(apiClient.post).toHaveBeenCalledWith('/files/check-network', {});
    expect((result as any).accessible).toBe(true);
    expect((result as any).latency_ms).toBe(15);
  });
});

// ============================================================================
// filesApi.clearCache 測試
// ============================================================================

describe('filesApi.clearCache', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filesApi.clearCache();
  });

  it('清除快取後應重新請求 storageInfo', async () => {
    vi.mocked(apiClient.post).mockResolvedValue(mockStorageInfo);

    // 第一次請求
    await filesApi.getStorageInfo();
    expect(apiClient.post).toHaveBeenCalledTimes(1);

    // 第二次使用快取
    await filesApi.getStorageInfo();
    expect(apiClient.post).toHaveBeenCalledTimes(1);

    // 清除快取後重新請求
    filesApi.clearCache();
    await filesApi.getStorageInfo();
    expect(apiClient.post).toHaveBeenCalledTimes(2);
  });
});
