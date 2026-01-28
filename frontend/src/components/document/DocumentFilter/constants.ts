/**
 * DocumentFilter 常數定義
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import type { DropdownOption } from './types';

/** 狀態篩選選項 (保留用於未來功能) */
export const STATUS_OPTIONS: DropdownOption[] = [
  { value: '', label: '全部狀態' },
  { value: '收文完成', label: '收文完成 (40)' },
  { value: '使用者確認', label: '使用者確認 (26)' },
  { value: '收文異常', label: '收文異常 (1)' },
];

/** 公文類型篩選選項 */
export const DOC_TYPE_OPTIONS: DropdownOption[] = [
  { value: '', label: '全部類型' },
  { value: '函', label: '函' },
  { value: '開會通知單', label: '開會通知單' },
  { value: '會勘通知單', label: '會勘通知單' },
];

/** 發文形式篩選選項 */
export const DELIVERY_METHOD_OPTIONS: DropdownOption[] = [
  { value: '', label: '全部形式' },
  { value: '電子交換', label: '電子交換' },
  { value: '紙本郵寄', label: '紙本郵寄' },
];
