/**
 * DocumentOperations 工具函數
 *
 * 從 DocumentOperations.tsx 提取的共用工具函數與常數
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import type { DocumentAttachment } from '../../../types/api';
import type { CriticalChange, CriticalFieldKey, FileValidationResult, OperationMode } from './types';
import { CRITICAL_FIELDS } from './types';

// ============================================================================
// 常數定義
// ============================================================================

/** 預設允許的檔案副檔名 */
export const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
  '.zip', '.rar', '.7z', '.txt', '.csv', '.xml', '.json',
  '.dwg', '.dxf', '.shp', '.kml', '.kmz',
];

/** 預設最大檔案大小 (MB) */
export const DEFAULT_MAX_FILE_SIZE_MB = 50;

/** 最小進度條顯示時間 (ms) - 確保用戶能看到進度 */
export const MIN_PROGRESS_DISPLAY_MS = 800;

// ============================================================================
// 關鍵欄位變更檢測
// ============================================================================

/**
 * 檢測關鍵欄位變更
 *
 * @param original - 原始文件資料
 * @param updated - 更新後的文件資料
 * @returns 變更項目陣列
 */
export const detectCriticalChanges = <T extends Record<string, unknown>>(
  original: T | null,
  updated: Partial<T>
): CriticalChange[] => {
  if (!original) return [];

  const changes: CriticalChange[] = [];

  (Object.keys(CRITICAL_FIELDS) as CriticalFieldKey[]).forEach((field) => {
    const oldVal = String(original[field] || '');
    const newVal = String(updated[field as keyof T] || '');

    if (oldVal !== newVal && updated[field as keyof T] !== undefined) {
      changes.push({
        field,
        label: CRITICAL_FIELDS[field].label,
        icon: CRITICAL_FIELDS[field].icon,
        oldValue: oldVal || '(空白)',
        newValue: newVal || '(空白)',
      });
    }
  });

  return changes;
};

// ============================================================================
// 檔案驗證
// ============================================================================

/**
 * 建立檔案驗證函數
 *
 * @param allowedExtensions - 允許的副檔名陣列
 * @param maxFileSizeMB - 最大檔案大小 (MB)
 * @returns 檔案驗證函數
 */
export const createFileValidator = (
  allowedExtensions: string[],
  maxFileSizeMB: number
): ((file: File) => FileValidationResult) => {
  return (file: File): FileValidationResult => {
    // 檢查檔案大小
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > maxFileSizeMB) {
      return {
        valid: false,
        error: `檔案 "${file.name}" 大小 (${fileSizeMB.toFixed(2)} MB) 超過限制 (${maxFileSizeMB} MB)`,
      };
    }

    // 檢查副檔名
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      return {
        valid: false,
        error: `檔案類型 "${ext}" 不支援，允許的類型：${allowedExtensions.join(', ')}`,
      };
    }

    return { valid: true };
  };
};

/**
 * 檢查是否為重複檔案
 *
 * @param filename - 要檢查的檔名
 * @param existingAttachments - 現有附件列表
 * @returns 重複的附件或 undefined
 */
export const checkDuplicateFile = (
  filename: string,
  existingAttachments: DocumentAttachment[]
): DocumentAttachment | undefined => {
  return existingAttachments.find(
    (att) =>
      (att.original_filename || att.filename)?.toLowerCase() === filename.toLowerCase()
  );
};

// ============================================================================
// Assignee 處理
// ============================================================================

/**
 * 解析 assignee 欄位（字串轉陣列）
 *
 * 支援以下格式：
 * - 字串（逗號分隔）: "張三, 李四, 王五"
 * - 陣列: ["張三", "李四", "王五"]
 *
 * @param rawAssignee - 原始 assignee 值
 * @returns 業務同仁名稱陣列
 */
export const parseAssignee = (rawAssignee: unknown): string[] => {
  if (!rawAssignee) return [];

  if (Array.isArray(rawAssignee)) {
    return rawAssignee.filter((item): item is string => typeof item === 'string');
  }

  if (typeof rawAssignee === 'string') {
    return rawAssignee
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }

  return [];
};

/**
 * 格式化 assignee 陣列為字串
 *
 * @param assignee - 業務同仁名稱陣列
 * @returns 逗號分隔的字串
 */
export const formatAssignee = (assignee: string[]): string => {
  return assignee.filter(Boolean).join(', ');
};

// ============================================================================
// 操作模式文字
// ============================================================================

/** 操作模式對應的按鈕文字 */
const OPERATION_TEXT: Record<OperationMode, string> = {
  view: '關閉',
  edit: '儲存',
  create: '建立',
  copy: '建立副本',
};

/** 操作模式對應的 Modal 標題 */
const MODAL_TITLE_TEXT: Record<OperationMode, string> = {
  view: '檢視公文',
  edit: '編輯公文',
  create: '新增公文',
  copy: '複製公文',
};

/**
 * 取得操作按鈕文字
 *
 * @param operation - 操作模式
 * @returns 按鈕文字
 */
export const getOperationText = (operation: OperationMode | null): string => {
  if (!operation) return '確定';
  return OPERATION_TEXT[operation] || '確定';
};

/**
 * 取得 Modal 標題文字
 *
 * @param operation - 操作模式
 * @returns Modal 標題
 */
export const getModalTitleText = (operation: OperationMode | null): string => {
  if (!operation) return '公文';
  return MODAL_TITLE_TEXT[operation] || '公文';
};

// ============================================================================
// 日期處理
// ============================================================================

/**
 * 格式化日期為 YYYY-MM-DD 字串
 *
 * @param date - Day.js 物件或日期字串
 * @returns 格式化的日期字串或 null
 */
export const formatDateToString = (date: unknown): string | null => {
  if (!date) return null;

  // 如果是 dayjs 物件
  if (typeof date === 'object' && date !== null && 'format' in date) {
    return (date as { format: (fmt: string) => string }).format('YYYY-MM-DD');
  }

  // 如果是字串，直接返回
  if (typeof date === 'string') {
    return date;
  }

  return null;
};

// ============================================================================
// 檔案大小格式化
// ============================================================================

/**
 * 格式化檔案大小
 *
 * @param bytes - 檔案大小（bytes）
 * @returns 格式化的字串 (e.g., "1.5 MB")
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// ============================================================================
// 錯誤處理
// ============================================================================

/**
 * 從 unknown 錯誤中提取錯誤訊息
 *
 * @param error - 未知錯誤
 * @param defaultMessage - 預設錯誤訊息
 * @returns 錯誤訊息字串
 */
export const getErrorMessage = (error: unknown, defaultMessage = '操作失敗'): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return defaultMessage;
};
