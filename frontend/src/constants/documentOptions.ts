/**
 * 公文相關常數定義
 *
 * 集中管理公文相關的選項常數
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

// 公文處理狀態
export const DOC_STATUS_OPTIONS = [
  '收文完成',
  '使用者確認',
  '收文異常',
] as const;

export type DocStatus = (typeof DOC_STATUS_OPTIONS)[number];

// 公文類型選項
export const DOC_TYPE_OPTIONS = [
  { value: '函', label: '函' },
  { value: '開會通知單', label: '開會通知單' },
  { value: '會勘通知單', label: '會勘通知單' },
] as const;

export const DOC_TYPE_VALUES = ['函', '開會通知單', '會勘通知單'] as const;

export type DocType = (typeof DOC_TYPE_VALUES)[number];

// 發文形式選項
export const DELIVERY_METHOD_OPTIONS = [
  { value: '電子交換', label: '電子交換' },
  { value: '紙本郵寄', label: '紙本郵寄' },
] as const;

export const DELIVERY_METHOD_VALUES = ['電子交換', '紙本郵寄'] as const;

export type DeliveryMethod = (typeof DELIVERY_METHOD_VALUES)[number];

// 收發文類型
export const DOC_DIRECTION_OPTIONS = [
  { value: '收文', label: '收文' },
  { value: '發文', label: '發文' },
] as const;

// 狀態顏色映射
export const DOC_STATUS_COLORS: Record<string, string> = {
  '收文完成': 'success',
  '使用者確認': 'processing',
  '收文異常': 'error',
};
