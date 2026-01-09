/**
 * 檔案管理 API 服務
 *
 * 統一的檔案上傳、下載、管理 API
 * 遵循 POST-only 資安機制
 *
 * @version 1.0
 * @date 2026-01-06
 */

import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';

// ============================================================================
// 型別定義
// ============================================================================

/** 檔案附件介面（與後端 DocumentAttachment 對應） */
export interface FileAttachment {
  id: number;
  filename: string;
  original_filename?: string;
  file_size: number;
  content_type?: string;
  storage_type?: 'local' | 'network' | 'nas';
  checksum?: string;
  uploaded_at?: string;
  uploaded_by?: number;
  created_at?: string;
}

/** 上傳結果 */
export interface UploadResult {
  success: boolean;
  message: string;
  files: Array<{
    id: number | null;
    filename: string;
    original_name: string;
    size: number;
    content_type: string;
    checksum: string;
    storage_path: string;
    uploaded_by: string | null;
  }>;
  errors?: string[];
}

/** 上傳進度回調 */
export interface UploadProgressCallback {
  onProgress?: (percent: number, loaded: number, total: number) => void;
  onSuccess?: (result: UploadResult) => void;
  onError?: (error: Error) => void;
}

/** 儲存資訊 */
export interface StorageInfo {
  success: boolean;
  storage_path: string;
  storage_type: 'local' | 'network' | 'nas';
  is_network_path: boolean;
  network_ip?: string;
  is_local_ip?: boolean;
  total_files: number;
  total_size_mb: number;
  allowed_extensions: string[];
  max_file_size_mb: number;
  disk_info?: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    usage_percent: number;
  };
}

/** 網路檢查結果 */
export interface NetworkCheckResult {
  success: boolean;
  storage_path: string;
  storage_type: string;
  is_network_path: boolean;
  network_ip?: string;
  is_local_ip?: boolean;
  healthy: boolean;
  checks: {
    path_exists: boolean;
    writable: boolean;
    write_error?: string;
    network_reachable?: boolean;
    connected_port?: number;
    network_error?: string;
  };
}

/** 檔案驗證結果 */
export interface FileVerifyResult {
  success: boolean;
  file_id: number;
  status: 'valid' | 'corrupted' | 'file_missing' | 'read_error' | 'no_checksum';
  is_valid?: boolean;
  stored_checksum?: string;
  current_checksum?: string;
  message: string;
}

/** 刪除結果 */
export interface DeleteResult {
  success: boolean;
  message: string;
  deleted_by?: string;
}

/** 附件列表回應 */
export interface AttachmentListResponse {
  success: boolean;
  document_id: number;
  total: number;
  attachments: FileAttachment[];
}

// ============================================================================
// 快取的儲存設定
// ============================================================================

let cachedStorageInfo: StorageInfo | null = null;
let storageInfoLoadedAt: number = 0;
const STORAGE_INFO_CACHE_TTL = 5 * 60 * 1000; // 5 分鐘快取

// ============================================================================
// API 方法
// ============================================================================

/**
 * 檔案 API 服務
 */
export const filesApi = {
  /**
   * 取得儲存系統資訊（含快取）
   *
   * @param forceRefresh 強制刷新快取
   * @returns 儲存資訊
   */
  async getStorageInfo(forceRefresh = false): Promise<StorageInfo> {
    const now = Date.now();

    // 檢查快取是否有效
    if (
      !forceRefresh &&
      cachedStorageInfo &&
      now - storageInfoLoadedAt < STORAGE_INFO_CACHE_TTL
    ) {
      return cachedStorageInfo;
    }

    // 從後端取得最新設定
    const info = await apiClient.post<StorageInfo>(API_ENDPOINTS.FILES.STORAGE_INFO, {});
    cachedStorageInfo = info;
    storageInfoLoadedAt = now;

    return info;
  },

  /**
   * 取得允許的副檔名列表
   *
   * @returns 副檔名陣列 (如 ['.pdf', '.doc', ...])
   */
  async getAllowedExtensions(): Promise<string[]> {
    const info = await this.getStorageInfo();
    return info.allowed_extensions;
  },

  /**
   * 取得檔案大小限制 (MB)
   *
   * @returns 最大檔案大小 (MB)
   */
  async getMaxFileSizeMB(): Promise<number> {
    const info = await this.getStorageInfo();
    return info.max_file_size_mb;
  },

  /**
   * 驗證檔案是否符合上傳規則
   *
   * @param file 要驗證的檔案
   * @returns 驗證結果
   */
  async validateFile(
    file: File
  ): Promise<{ valid: boolean; error?: string }> {
    const info = await this.getStorageInfo();

    // 檢查副檔名
    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');

    if (!info.allowed_extensions.includes(ext)) {
      return {
        valid: false,
        error: `不支援 ${ext} 檔案格式。允許的格式: ${info.allowed_extensions.slice(0, 5).join(', ')} 等`,
      };
    }

    // 檢查檔案大小
    const maxSizeBytes = info.max_file_size_mb * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `檔案 "${file.name}" 大小 ${sizeMB}MB 超過限制 (最大 ${info.max_file_size_mb}MB)`,
      };
    }

    return { valid: true };
  },

  /**
   * 上傳檔案（含進度追蹤）
   *
   * 使用 apiClient.uploadWithProgress 統一上傳邏輯
   *
   * @param documentId 公文 ID
   * @param files 要上傳的檔案列表
   * @param callbacks 進度回調函數
   * @returns Promise<UploadResult>
   */
  async uploadFiles(
    documentId: number,
    files: File[],
    callbacks?: UploadProgressCallback
  ): Promise<UploadResult> {
    if (files.length === 0) {
      return { success: true, message: '無檔案上傳', files: [], errors: [] };
    }

    try {
      const result = await apiClient.uploadWithProgress<UploadResult>(
        API_ENDPOINTS.FILES.UPLOAD(documentId),
        files,
        'files',
        callbacks?.onProgress
      );

      callbacks?.onSuccess?.(result);
      return result;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('上傳失敗');
      callbacks?.onError?.(err);
      throw err;
    }
  },

  /**
   * 取得文件附件列表
   *
   * @param documentId 公文 ID
   * @returns 附件列表
   */
  async getDocumentAttachments(
    documentId: number
  ): Promise<FileAttachment[]> {
    const response = await apiClient.post<AttachmentListResponse>(
      API_ENDPOINTS.FILES.DOCUMENT_ATTACHMENTS(documentId),
      {}
    );
    return response.attachments || [];
  },

  /**
   * 下載附件
   *
   * @param attachmentId 附件 ID
   * @param filename 下載檔名
   */
  async downloadAttachment(
    attachmentId: number,
    filename: string
  ): Promise<void> {
    await apiClient.downloadPost(
      API_ENDPOINTS.FILES.DOWNLOAD(attachmentId),
      {},
      filename || 'download'
    );
  },

  /**
   * 取得附件 Blob（用於預覽）
   *
   * @param attachmentId 附件 ID
   * @returns Blob 資料
   */
  async getAttachmentBlob(attachmentId: number): Promise<Blob> {
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || ''}/api/files/${attachmentId}/download`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }
    );

    if (!response.ok) {
      throw new Error('取得附件失敗');
    }

    return await response.blob();
  },

  /**
   * 刪除附件
   *
   * @param attachmentId 附件 ID
   * @returns 刪除結果
   */
  async deleteAttachment(attachmentId: number): Promise<DeleteResult> {
    return await apiClient.post<DeleteResult>(
      API_ENDPOINTS.FILES.DELETE(attachmentId),
      {}
    );
  },

  /**
   * 驗證檔案完整性
   *
   * @param attachmentId 附件 ID
   * @returns 驗證結果
   */
  async verifyAttachment(attachmentId: number): Promise<FileVerifyResult> {
    return await apiClient.post<FileVerifyResult>(
      API_ENDPOINTS.FILES.VERIFY(attachmentId),
      {}
    );
  },

  /**
   * 檢查網路儲存連線狀態
   *
   * @returns 網路檢查結果
   */
  async checkNetworkStorage(): Promise<NetworkCheckResult> {
    return await apiClient.post<NetworkCheckResult>(
      API_ENDPOINTS.FILES.CHECK_NETWORK,
      {}
    );
  },

  /**
   * 清除儲存資訊快取
   */
  clearCache(): void {
    cachedStorageInfo = null;
    storageInfoLoadedAt = 0;
  },
};

// 預設匯出
export default filesApi;
