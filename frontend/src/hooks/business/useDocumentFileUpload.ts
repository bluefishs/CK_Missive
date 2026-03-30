/**
 * 公文附件上傳 Hook
 *
 * 從 useDocumentCreateForm 拆分，負責檔案驗證與上傳邏輯
 *
 * @version 1.0.0
 * @date 2026-03-29
 */

import { useState, useCallback } from 'react';
import { App } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { filesApi } from '../../api/filesApi';
import {
  DEFAULT_ALLOWED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  type FileSettings,
} from './useDocumentCreateForm';

export interface UseDocumentFileUploadResult {
  fileList: UploadFile[];
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  clearUploadErrors: () => void;
  validateFile: (file: File) => { valid: boolean; error?: string };
  uploadFiles: (documentId: number, files: UploadFile[]) => Promise<void>;
}

export function useDocumentFileUpload(
  fileSettings: FileSettings = {
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  }
): UseDocumentFileUploadResult {
  const { message } = App.useApp();

  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  const clearUploadErrors = useCallback(() => {
    setUploadErrors([]);
  }, []);

  const validateFile = useCallback(
    (file: File): { valid: boolean; error?: string } => {
      const { allowedExtensions, maxFileSizeMB } = fileSettings;
      const fileName = file.name.toLowerCase();
      const ext = '.' + (fileName.split('.').pop() || '');

      if (!allowedExtensions.includes(ext)) {
        return { valid: false, error: `不支援 ${ext} 檔案格式` };
      }

      const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
      if (file.size > maxSizeBytes) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        return {
          valid: false,
          error: `檔案大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`,
        };
      }

      return { valid: true };
    },
    [fileSettings]
  );

  const uploadFiles = useCallback(
    async (documentId: number, files: UploadFile[]): Promise<void> => {
      if (files.length === 0) return;

      const fileObjects: File[] = files
        .map((f) => f.originFileObj as File | undefined)
        .filter((f): f is File => f !== undefined);

      if (fileObjects.length === 0) return;

      setUploading(true);
      setUploadProgress(0);
      setUploadErrors([]);

      try {
        const result = await filesApi.uploadFiles(documentId, fileObjects, {
          onProgress: (percent) => setUploadProgress(percent),
        });

        if (result.errors && result.errors.length > 0) {
          setUploadErrors(result.errors);
        }

        const successCount = result.files?.length || 0;
        const errorCount = result.errors?.length || 0;

        if (successCount > 0 && errorCount === 0) {
          message.success(`附件上傳成功（共 ${successCount} 個檔案）`);
        } else if (successCount > 0 && errorCount > 0) {
          message.warning(
            `部分附件上傳成功（成功 ${successCount} 個，失敗 ${errorCount} 個）`
          );
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : '上傳失敗';
        message.error(`附件上傳失敗: ${errorMsg}`);
        throw error;
      } finally {
        setUploading(false);
      }
    },
    [message]
  );

  return {
    fileList,
    setFileList,
    uploading,
    uploadProgress,
    uploadErrors,
    clearUploadErrors,
    validateFile,
    uploadFiles,
  };
}
