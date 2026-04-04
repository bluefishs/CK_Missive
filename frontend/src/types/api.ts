/**
 * API 業務型別定義 — Barrel Re-export
 *
 * 與後端 Pydantic Schema 對應，確保前後端型別一致。
 *
 * 原始 1338 行已拆分至領域型別檔：
 * - document.ts       — 公文、附件、篩選、統計
 * - taoyuan.ts        — 工程、派工、契金、關聯、總控
 * - admin-system.ts   — 證照、備份、儀表板、MFA
 * - deployment.ts     — 部署型別
 * - api-user.ts       — 使用者、權限、管理員
 * - api-entity.ts     — 廠商、機關
 * - api-project.ts    — 專案、承攬案件、人員/廠商關聯
 * - api-calendar.ts   — 行事曆事件、Google Calendar
 * - api-knowledge.ts  — 知識庫瀏覽器、實體配對
 * - pm.ts             — PM 專案管理
 * - erp.ts            — ERP 財務管理
 *
 * 此檔案保留公文類別常數/工具型別/分頁型別/下拉選項，
 * 並 re-export 所有領域型別，確保現有匯入者無需修改。
 *
 * @version 3.0.0
 * @refactored 2026-04-02
 */

// ============================================================================
// Re-export 領域型別（向後相容 — 所有 import { X } from 'types/api' 仍有效）
// ============================================================================

export * from './document';
export * from './taoyuan';
export * from './admin-system';
export * from './deployment';
export * from './api-user';
export * from './api-entity';
export * from './api-project';
export * from './api-calendar';
export * from './api-knowledge';
// Re-export PM/ERP for backward compatibility (many files import from 'types/api')
export * from './pm';
export * from './erp';

// ============================================================================
// 公文類別 (Document Category) 常數與判斷函數
// ============================================================================

/**
 * 公文類別常數
 * 用於統一處理資料庫可能存在的中英文混用問題
 */
export const DOCUMENT_CATEGORY = {
  /** 收文 */
  RECEIVE: 'receive',
  /** 發文 */
  SEND: 'send',
  /** 收文（中文） */
  RECEIVE_CN: '收文',
  /** 發文（中文） */
  SEND_CN: '發文',
} as const;

/** 公文類別型別 */
export type DocumentCategoryType = 'receive' | 'send' | '收文' | '發文';

/**
 * 判斷是否為收文
 * @param category 公文類別（可能是中文或英文）
 */
export const isReceiveDocument = (category?: string | null): boolean =>
  category === DOCUMENT_CATEGORY.RECEIVE || category === DOCUMENT_CATEGORY.RECEIVE_CN;

/**
 * 判斷是否為發文
 * @param category 公文類別（可能是中文或英文）
 */
export const isSendDocument = (category?: string | null): boolean =>
  category === DOCUMENT_CATEGORY.SEND || category === DOCUMENT_CATEGORY.SEND_CN;

/**
 * 取得標準化的公文類別（轉為英文）
 * @param category 公文類別
 */
export const normalizeDocumentCategory = (category?: string | null): 'receive' | 'send' | null => {
  if (isReceiveDocument(category)) return 'receive';
  if (isSendDocument(category)) return 'send';
  return null;
};

// ============================================================================
// 通用工具型別
// ============================================================================

/** 將所有屬性設為可選 */
export type PartialEntity<T> = {
  [P in keyof T]?: T[P];
};

/** ID 型別 */
export type EntityId = number;

/** 時間戳欄位 */
export interface Timestamps {
  created_at: string;
  updated_at: string;
}

// ============================================================================
// 通用分頁型別
// ============================================================================

/** 分頁元資料 */
export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ============================================================================
// 公文相關輔助型別
// ============================================================================

/** 下拉選項 */
export interface DropdownOption {
  value: string;
  label: string;
  id?: number;
  year?: number;
  category?: string;
}
