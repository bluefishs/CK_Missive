/**
 * 附件相關共用工具函數
 *
 * @version 1.0.0
 * @date 2026-01-27
 */

import type { ReactNode } from 'react';
import {
  PaperClipOutlined,
  FilePdfOutlined,
  FileImageOutlined,
  FileExcelOutlined,
  FileWordOutlined,
  FilePptOutlined,
  FileZipOutlined,
  FileTextOutlined,
  FileOutlined,
} from '@ant-design/icons';
import React from 'react';

// ============================================================================
// 常數定義
// ============================================================================

/** 可預覽的 MIME 類型 */
export const PREVIEWABLE_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/bmp',
  'image/webp',
  'application/pdf',
  'text/plain',
  'text/csv',
  'text/html',
];

/** 可預覽的副檔名 */
export const PREVIEWABLE_EXTENSIONS = [
  'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'txt', 'csv', 'html',
];

/** 預設允許的副檔名 */
export const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp',
  '.zip', '.rar', '.7z',
  '.txt', '.csv',
];

/** 預設最大檔案大小 (50MB) */
export const DEFAULT_MAX_FILE_SIZE_MB = 50;

// ============================================================================
// 工具函數
// ============================================================================

/**
 * 判斷檔案是否可預覽
 */
export const isPreviewable = (contentType?: string, filename?: string): boolean => {
  // 檢查 MIME 類型
  if (contentType) {
    if (contentType.startsWith('image/') ||
        contentType === 'application/pdf' ||
        contentType.startsWith('text/')) {
      return true;
    }
  }

  // 檢查副檔名
  if (filename) {
    const ext = filename.toLowerCase().split('.').pop();
    return PREVIEWABLE_EXTENSIONS.includes(ext || '');
  }

  return false;
};

/**
 * 格式化檔案大小
 */
export const formatFileSize = (bytes: number | undefined): string => {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
};

/**
 * 取得檔案副檔名
 */
export const getFileExtension = (filename: string): string => {
  return (filename.split('.').pop() || '').toLowerCase();
};

/**
 * 取得檔案圖示顏色配置
 */
interface FileIconConfig {
  icon: ReactNode;
  color: string;
}

export const getFileIconConfig = (
  contentType?: string,
  filename?: string
): FileIconConfig => {
  const ext = filename ? getFileExtension(filename) : '';

  // 圖片
  if (contentType?.startsWith('image/') ||
      ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) {
    return {
      icon: React.createElement(FileImageOutlined),
      color: '#52c41a',
    };
  }

  // PDF
  if (contentType === 'application/pdf' || ext === 'pdf') {
    return {
      icon: React.createElement(FilePdfOutlined),
      color: '#ff4d4f',
    };
  }

  // Word
  if (contentType?.includes('word') || ['doc', 'docx'].includes(ext)) {
    return {
      icon: React.createElement(FileWordOutlined),
      color: '#1890ff',
    };
  }

  // Excel
  if (contentType?.includes('excel') || contentType?.includes('spreadsheet') ||
      ['xls', 'xlsx', 'csv'].includes(ext)) {
    return {
      icon: React.createElement(FileExcelOutlined),
      color: '#52c41a',
    };
  }

  // PowerPoint
  if (contentType?.includes('powerpoint') || contentType?.includes('presentation') ||
      ['ppt', 'pptx'].includes(ext)) {
    return {
      icon: React.createElement(FilePptOutlined),
      color: '#fa8c16',
    };
  }

  // 壓縮檔
  if (contentType?.includes('zip') || contentType?.includes('rar') ||
      ['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
    return {
      icon: React.createElement(FileZipOutlined),
      color: '#722ed1',
    };
  }

  // 文字檔
  if (contentType?.startsWith('text/') || ['txt', 'log', 'md'].includes(ext)) {
    return {
      icon: React.createElement(FileTextOutlined),
      color: '#666',
    };
  }

  // 預設
  return {
    icon: React.createElement(PaperClipOutlined),
    color: '#1890ff',
  };
};

/**
 * 驗證檔案
 */
export interface FileValidationResult {
  valid: boolean;
  error?: string;
}

export interface FileValidationOptions {
  allowedExtensions?: string[];
  maxFileSizeMB?: number;
}

export const validateFile = (
  file: File,
  options: FileValidationOptions = {}
): FileValidationResult => {
  const {
    allowedExtensions = DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB = DEFAULT_MAX_FILE_SIZE_MB,
  } = options;

  const fileName = file.name.toLowerCase();
  const ext = '.' + getFileExtension(fileName);

  // 檢查副檔名
  if (!allowedExtensions.includes(ext)) {
    return {
      valid: false,
      error: `不支援 ${ext} 檔案格式`,
    };
  }

  // 檢查檔案大小
  const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
  if (file.size > maxSizeBytes) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    return {
      valid: false,
      error: `檔案大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`,
    };
  }

  return { valid: true };
};

/**
 * 建立預覽 URL 並自動釋放
 */
export const createPreviewUrl = (blob: Blob, autoRevokeMs = 10000): string => {
  const url = window.URL.createObjectURL(blob);
  if (autoRevokeMs > 0) {
    setTimeout(() => window.URL.revokeObjectURL(url), autoRevokeMs);
  }
  return url;
};

/**
 * 下載 Blob 檔案
 */
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};
