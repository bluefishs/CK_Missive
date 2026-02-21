/**
 * 共用驗證器 - 與後端 validators.py 保持一致
 *
 * 提供統一的資料驗證規則，確保前後端使用相同的驗證邏輯。
 *
 * @version 1.0.0
 * @date 2026-01-21
 * @see backend/app/services/base/validators.py
 */

import { logger } from '../services/logger';

// ============================================================
// 公文相關驗證器
// ============================================================

/**
 * 有效的公文類型白名單
 * @sync backend/app/services/base/validators.py:DocumentValidators.VALID_DOC_TYPES
 */
export const VALID_DOC_TYPES = [
  '函',
  '開會通知單',
  '會勘通知單',
  '書函',
  '公告',
  '令',
  '通知',
] as const;

export type DocType = (typeof VALID_DOC_TYPES)[number];

/**
 * 有效的公文類別
 * @sync backend/app/services/base/validators.py:DocumentValidators.VALID_CATEGORIES
 */
export const VALID_CATEGORIES = ['收文', '發文'] as const;

export type DocCategory = (typeof VALID_CATEGORIES)[number];

/**
 * 有效的公文狀態
 * @sync backend/app/services/base/validators.py:DocumentValidators.VALID_STATUSES
 */
export const VALID_STATUSES = [
  'active',
  '待處理',
  '處理中',
  '已完成',
  '已歸檔',
] as const;

export type DocStatus = (typeof VALID_STATUSES)[number];

/**
 * 公文驗證器
 */
export const DocumentValidators = {
  VALID_DOC_TYPES,
  VALID_CATEGORIES,
  VALID_STATUSES,

  /**
   * 驗證公文類型
   * @param value 公文類型值
   * @param autoFix 是否自動修正無效值為預設值
   * @returns 驗證後的公文類型
   */
  validateDocType(value: string | null | undefined, autoFix = true): string {
    if (!value) {
      return autoFix ? '函' : '';
    }

    const trimmed = String(value).trim();
    if ((VALID_DOC_TYPES as readonly string[]).includes(trimmed)) {
      return trimmed;
    }

    if (autoFix) {
      return '函';
    }

    throw new Error(`無效的公文類型: ${value}，有效值: ${VALID_DOC_TYPES.join(', ')}`);
  },

  /**
   * 驗證公文類別
   * @param value 類別值
   * @returns 驗證後的類別
   */
  validateCategory(value: string | null | undefined): string {
    if (!value) {
      throw new Error('類別不可為空');
    }

    const trimmed = String(value).trim();
    if (!(VALID_CATEGORIES as readonly string[]).includes(trimmed)) {
      throw new Error(`無效的類別: ${value}，有效值: ${VALID_CATEGORIES.join(', ')}`);
    }

    return trimmed;
  },

  /**
   * 驗證狀態
   * @param value 狀態值
   * @param defaultValue 預設值
   * @returns 驗證後的狀態
   */
  validateStatus(value: string | null | undefined, defaultValue = 'active'): string {
    if (!value) {
      return defaultValue;
    }

    const trimmed = String(value).trim();
    if ((VALID_STATUSES as readonly string[]).includes(trimmed)) {
      return trimmed;
    }

    return defaultValue;
  },

  /**
   * 檢查是否為有效的公文類型
   */
  isValidDocType(value: string): value is DocType {
    return (VALID_DOC_TYPES as readonly string[]).includes(value);
  },

  /**
   * 檢查是否為有效的類別
   */
  isValidCategory(value: string): value is DocCategory {
    return (VALID_CATEGORIES as readonly string[]).includes(value);
  },

  /**
   * 檢查是否為有效的狀態
   */
  isValidStatus(value: string): value is DocStatus {
    return (VALID_STATUSES as readonly string[]).includes(value);
  },
};

// ============================================================
// 字串清理工具
// ============================================================

/**
 * 無效字串值列表
 */
const INVALID_VALUES = ['none', 'null', 'undefined', 'nan', ''];

/**
 * 字串清理工具
 */
export const StringCleaners = {
  INVALID_VALUES,

  /**
   * 清理字串值
   * 避免 null/undefined 被轉為字串，並去除首尾空白。
   * @param value 任意值
   * @returns 清理後的字串或 null
   */
  cleanString(value: unknown): string | null {
    if (value === null || value === undefined) {
      return null;
    }

    const text = String(value).trim();

    if (INVALID_VALUES.includes(text.toLowerCase())) {
      return null;
    }

    return text;
  },

  /**
   * 清理機關名稱
   * 移除代碼後綴，例如 "桃園市政府(10002)" -> "桃園市政府"
   * @param name 機關名稱
   * @returns 清理後的機關名稱
   */
  cleanAgencyName(name: string | null | undefined): string | null {
    if (!name) {
      return null;
    }

    let cleaned = this.cleanString(name);
    if (!cleaned) {
      return null;
    }

    // 移除括號內的代碼
    cleaned = cleaned.replace(/\s*\([^)]*\)\s*$/, '');
    // 移除開頭的數字代碼
    cleaned = cleaned.replace(/^\d+\s*/, '');

    return cleaned.trim() || null;
  },

  /**
   * 清理並截斷字串
   * @param value 原始值
   * @param maxLength 最大長度
   * @returns 清理並截斷後的字串
   */
  cleanAndTruncate(value: unknown, maxLength: number): string | null {
    const cleaned = this.cleanString(value);
    if (!cleaned) {
      return null;
    }

    if (cleaned.length <= maxLength) {
      return cleaned;
    }

    return cleaned.substring(0, maxLength - 3) + '...';
  },
};

// ============================================================
// 機關名稱解析器
// ============================================================

/**
 * 機關解析結果
 */
export interface ParsedAgency {
  code: string | null;
  name: string;
}

/**
 * 機關名稱解析器
 *
 * 支援格式：
 * - "機關名稱" -> [(null, "機關名稱")]
 * - "代碼 (機關名稱)" -> [("代碼", "機關名稱")]
 * - "代碼 機關名稱" -> [("代碼", "機關名稱")]
 * - "代碼1 (名稱1) | 代碼2 (名稱2)" -> 多個機關
 * - "代碼\\n(機關名稱)" -> 換行格式
 */
export const AgencyNameParser = {
  /**
   * 解析機關文字，提取機關代碼和名稱
   * @param text 原始機關文字
   * @returns 解析結果陣列
   */
  parse(text: string | null | undefined): ParsedAgency[] {
    if (!text || !text.trim()) {
      return [];
    }

    const results: ParsedAgency[] = [];
    // 處理多個受文者（以 | 分隔）
    const parts = text.split('|');

    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) {
        continue;
      }

      const parsed = this._parseSingle(trimmed);
      if (parsed) {
        results.push(parsed);
      }
    }

    return results;
  },

  /**
   * 解析單一機關文字
   */
  _parseSingle(part: string): ParsedAgency | null {
    // 模式1: "代碼 (機關名稱)" 或 "代碼\n(機關名稱)"
    const pattern1 = /^([A-Z0-9]+)\s*[\n(（](.+?)[)）]?\s*$/i;
    const match1 = part.match(pattern1);
    if (match1 && match1[1] && match1[2]) {
      return { code: match1[1].toUpperCase(), name: match1[2].trim() };
    }

    // 模式2: "代碼 機關名稱"（代碼與名稱以空白分隔）
    const pattern2 = /^([A-Z0-9]{5,15})\s+(.+)$/i;
    const match2 = part.match(pattern2);
    if (match2 && match2[1] && match2[2]) {
      return { code: match2[1].toUpperCase(), name: match2[2].trim() };
    }

    // 模式3: 純名稱（無代碼）
    return { code: null, name: part.trim() };
  },

  /**
   * 從機關文字中提取機關名稱列表
   * @param text 原始機關文字
   * @returns 機關名稱列表
   */
  extractNames(text: string | null | undefined): string[] {
    const parsed = this.parse(text);
    return parsed.map((p) => p.name).filter(Boolean);
  },

  /**
   * 從機關文字中提取機關代碼列表
   * @param text 原始機關文字
   * @returns 機關代碼列表（不含 null）
   */
  extractCodes(text: string | null | undefined): string[] {
    const parsed = this.parse(text);
    return parsed.map((p) => p.code).filter((code): code is string => code !== null);
  },

  /**
   * 清理機關名稱，移除代碼後綴
   */
  cleanName(name: string | null | undefined): string | null {
    return StringCleaners.cleanAgencyName(name);
  },
};

// ============================================================
// 日期解析工具
// ============================================================

/**
 * 支援的日期格式
 */
const DATE_FORMATS = [
  'yyyy-MM-dd',
  'yyyy/MM/dd',
  'yyyy.MM.dd',
  'yyyy-MM-dd HH:mm:ss',
  'yyyy/MM/dd HH:mm:ss',
];

/**
 * 日期解析工具
 */
export const DateParsers = {
  DATE_FORMATS,

  /**
   * 解析日期值
   * 支援多種格式：西元日期、民國日期。
   * @param value 日期值（字串、Date）
   * @returns 解析後的 Date 物件或 null
   */
  parseDate(value: unknown): Date | null {
    if (!value) {
      return null;
    }

    // 如果已經是 Date 物件
    if (value instanceof Date) {
      return isNaN(value.getTime()) ? null : value;
    }

    // 字串解析
    const valueStr = String(value).trim();
    if (!valueStr || ['none', 'null', ''].includes(valueStr.toLowerCase())) {
      return null;
    }

    // 嘗試標準 ISO 日期格式
    const isoDate = new Date(valueStr);
    if (!isNaN(isoDate.getTime())) {
      return isoDate;
    }

    // 嘗試解析民國日期
    return this._parseRocDate(valueStr);
  },

  /**
   * 解析民國日期格式
   */
  _parseRocDate(valueStr: string): Date | null {
    // 格式：中華民國114年1月8日 或 民國114年1月8日
    const rocPatterns = [
      /中華民國(\d{2,3})年(\d{1,2})月(\d{1,2})日/,
      /民國(\d{2,3})年(\d{1,2})月(\d{1,2})日/,
      /(\d{2,3})年(\d{1,2})月(\d{1,2})日/,
    ];

    for (const pattern of rocPatterns) {
      const match = valueStr.match(pattern);
      if (match && match[1] && match[2] && match[3]) {
        try {
          const year = parseInt(match[1], 10) + 1911;
          const month = parseInt(match[2], 10) - 1; // JavaScript months are 0-indexed
          const day = parseInt(match[3], 10);
          const date = new Date(year, month, day);
          if (!isNaN(date.getTime())) {
            return date;
          }
        } catch {
          continue;
        }
      }
    }

    return null;
  },

  /**
   * 將 Date 轉換為民國日期字串
   * @param date Date 物件
   * @returns 民國日期字串（如：114年1月21日）
   */
  toRocDateString(date: Date | null | undefined): string {
    if (!date) {
      return '';
    }

    const year = date.getFullYear() - 1911;
    const month = date.getMonth() + 1;
    const day = date.getDate();

    return `${year}年${month}月${day}日`;
  },

  /**
   * 將 Date 轉換為完整民國日期字串
   * @param date Date 物件
   * @returns 民國日期字串（如：中華民國114年1月21日）
   */
  toFullRocDateString(date: Date | null | undefined): string {
    if (!date) {
      return '';
    }

    return `中華民國${this.toRocDateString(date)}`;
  },
};

// ============================================================
// 表單驗證規則
// ============================================================

/**
 * 常用的 Ant Design Form 驗證規則
 */
export const FormRules = {
  /**
   * 必填欄位
   */
  required: (message = '此欄位為必填') => ({
    required: true,
    message,
  }),

  /**
   * 最大長度
   */
  maxLength: (max: number, message?: string) => ({
    max,
    message: message || `長度不可超過 ${max} 字元`,
  }),

  /**
   * 最小長度
   */
  minLength: (min: number, message?: string) => ({
    min,
    message: message || `長度不可少於 ${min} 字元`,
  }),

  /**
   * Email 格式
   */
  email: (message = '請輸入有效的電子郵件') => ({
    type: 'email' as const,
    message,
  }),

  /**
   * 統一編號格式（8碼數字）
   */
  taxId: (message = '請輸入有效的統一編號（8位數字）') => ({
    pattern: /^\d{8}$/,
    message,
  }),

  /**
   * 電話號碼格式
   */
  phone: (message = '請輸入有效的電話號碼') => ({
    pattern: /^[\d\-()+\s]{7,20}$/,
    message,
  }),

  /**
   * 公文類型驗證
   */
  docType: () => ({
    validator: (_: unknown, value: string) => {
      if (!value || DocumentValidators.isValidDocType(value)) {
        return Promise.resolve();
      }
      return Promise.reject(
        new Error(`無效的公文類型，有效值: ${VALID_DOC_TYPES.join(', ')}`)
      );
    },
  }),

  /**
   * 公文類別驗證
   */
  docCategory: () => ({
    validator: (_: unknown, value: string) => {
      if (!value || DocumentValidators.isValidCategory(value)) {
        return Promise.resolve();
      }
      return Promise.reject(
        new Error(`無效的類別，有效值: ${VALID_CATEGORIES.join(', ')}`)
      );
    },
  }),
};

// ============================================================
// API 回應驗證機制
// ============================================================

/**
 * 有效的關聯類型
 * @sync backend/app/schemas/taoyuan_dispatch.py:LinkTypeEnum
 */
export const VALID_LINK_TYPES = ['agency_incoming', 'company_outgoing'] as const;

export type LinkTypeValue = (typeof VALID_LINK_TYPES)[number];

/**
 * API 回應驗證結果
 */
export interface ValidationResult<T> {
  /** 驗證是否成功 */
  isValid: boolean;
  /** 驗證後的資料 */
  data: T | null;
  /** 錯誤訊息列表 */
  errors: string[];
  /** 警告訊息列表 (資料可用但有潛在問題) */
  warnings: string[];
}

/**
 * 基礎關聯驗證結果
 */
export interface BaseLinkValidation {
  link_id: number;
  link_type?: LinkTypeValue;
  created_at?: string;
}

/**
 * 派工單關聯驗證結果
 */
export interface DispatchLinkValidation extends BaseLinkValidation {
  dispatch_order_id: number;
  dispatch_no: string;
}

/**
 * 工程關聯驗證結果
 */
export interface ProjectLinkValidation extends BaseLinkValidation {
  project_id: number;
  project_name: string;
}

/**
 * API 回應驗證器
 *
 * 提供執行階段的 API 回應驗證，確保關聯資料的完整性
 */
export const ApiResponseValidators = {
  /**
   * 驗證是否為有效的正整數 ID
   * @param value 要驗證的值
   * @param fieldName 欄位名稱（用於錯誤訊息）
   */
  isValidId(value: unknown, _fieldName = 'ID'): value is number {
    if (value === undefined || value === null) {
      return false;
    }
    const num = typeof value === 'number' ? value : Number(value);
    return Number.isInteger(num) && num > 0;
  },

  /**
   * 驗證是否為有效的關聯類型
   */
  isValidLinkType(value: unknown): value is LinkTypeValue {
    return typeof value === 'string' && (VALID_LINK_TYPES as readonly string[]).includes(value);
  },

  /**
   * 驗證基礎關聯資料
   * @param data 原始 API 回應資料
   * @returns 驗證結果
   */
  validateBaseLink(data: unknown): ValidationResult<BaseLinkValidation> {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!data || typeof data !== 'object') {
      return { isValid: false, data: null, errors: ['無效的關聯資料格式'], warnings };
    }

    const obj = data as Record<string, unknown>;

    // 必要欄位：link_id
    if (!this.isValidId(obj.link_id, 'link_id')) {
      errors.push(`link_id 無效或缺失: ${JSON.stringify(obj.link_id)}`);
    }

    // 可選欄位：link_type
    if (obj.link_type !== undefined && obj.link_type !== null && !this.isValidLinkType(obj.link_type)) {
      warnings.push(`link_type 值不在預期範圍內: ${obj.link_type}`);
    }

    if (errors.length > 0) {
      return { isValid: false, data: null, errors, warnings };
    }

    return {
      isValid: true,
      data: {
        link_id: obj.link_id as number,
        link_type: this.isValidLinkType(obj.link_type) ? obj.link_type : undefined,
        created_at: typeof obj.created_at === 'string' ? obj.created_at : undefined,
      },
      errors,
      warnings,
    };
  },

  /**
   * 驗證派工單關聯資料
   * @param data 原始 API 回應資料
   * @returns 驗證結果
   */
  validateDispatchLink(data: unknown): ValidationResult<DispatchLinkValidation> {
    const baseResult = this.validateBaseLink(data);
    const errors = [...baseResult.errors];
    const warnings = [...baseResult.warnings];

    if (!data || typeof data !== 'object') {
      return { isValid: false, data: null, errors, warnings };
    }

    const obj = data as Record<string, unknown>;

    // 必要欄位：dispatch_order_id
    if (!this.isValidId(obj.dispatch_order_id, 'dispatch_order_id')) {
      errors.push(`dispatch_order_id 無效或缺失: ${JSON.stringify(obj.dispatch_order_id)}`);
    }

    // 必要欄位：dispatch_no
    if (typeof obj.dispatch_no !== 'string' || !obj.dispatch_no.trim()) {
      warnings.push(`dispatch_no 缺失或為空`);
    }

    if (errors.length > 0) {
      return { isValid: false, data: null, errors, warnings };
    }

    return {
      isValid: true,
      data: {
        link_id: obj.link_id as number,
        link_type: this.isValidLinkType(obj.link_type) ? obj.link_type : undefined,
        created_at: typeof obj.created_at === 'string' ? obj.created_at : undefined,
        dispatch_order_id: obj.dispatch_order_id as number,
        dispatch_no: (obj.dispatch_no as string) || '',
      },
      errors,
      warnings,
    };
  },

  /**
   * 驗證工程關聯資料
   * @param data 原始 API 回應資料
   * @returns 驗證結果
   */
  validateProjectLink(data: unknown): ValidationResult<ProjectLinkValidation> {
    const baseResult = this.validateBaseLink(data);
    const errors = [...baseResult.errors];
    const warnings = [...baseResult.warnings];

    if (!data || typeof data !== 'object') {
      return { isValid: false, data: null, errors, warnings };
    }

    const obj = data as Record<string, unknown>;

    // 必要欄位：project_id
    if (!this.isValidId(obj.project_id, 'project_id')) {
      errors.push(`project_id 無效或缺失: ${JSON.stringify(obj.project_id)}`);
    }

    // 必要欄位：project_name
    if (typeof obj.project_name !== 'string' || !obj.project_name.trim()) {
      warnings.push(`project_name 缺失或為空`);
    }

    if (errors.length > 0) {
      return { isValid: false, data: null, errors, warnings };
    }

    return {
      isValid: true,
      data: {
        link_id: obj.link_id as number,
        link_type: this.isValidLinkType(obj.link_type) ? obj.link_type : undefined,
        created_at: typeof obj.created_at === 'string' ? obj.created_at : undefined,
        project_id: obj.project_id as number,
        project_name: (obj.project_name as string) || '',
      },
      errors,
      warnings,
    };
  },

  /**
   * 批次驗證派工單關聯陣列
   * @param dataArray 關聯資料陣列
   * @returns 驗證通過的資料陣列和錯誤摘要
   */
  validateDispatchLinkArray(dataArray: unknown): {
    validData: DispatchLinkValidation[];
    invalidCount: number;
    errors: string[];
  } {
    if (!Array.isArray(dataArray)) {
      return { validData: [], invalidCount: 0, errors: ['資料不是陣列格式'] };
    }

    const validData: DispatchLinkValidation[] = [];
    const errors: string[] = [];
    let invalidCount = 0;

    dataArray.forEach((item, index) => {
      const result = this.validateDispatchLink(item);
      if (result.isValid && result.data) {
        validData.push(result.data);
      } else {
        invalidCount++;
        errors.push(`[${index}]: ${result.errors.join(', ')}`);
      }
    });

    return { validData, invalidCount, errors };
  },

  /**
   * 批次驗證工程關聯陣列
   * @param dataArray 關聯資料陣列
   * @returns 驗證通過的資料陣列和錯誤摘要
   */
  validateProjectLinkArray(dataArray: unknown): {
    validData: ProjectLinkValidation[];
    invalidCount: number;
    errors: string[];
  } {
    if (!Array.isArray(dataArray)) {
      return { validData: [], invalidCount: 0, errors: ['資料不是陣列格式'] };
    }

    const validData: ProjectLinkValidation[] = [];
    const errors: string[] = [];
    let invalidCount = 0;

    dataArray.forEach((item, index) => {
      const result = this.validateProjectLink(item);
      if (result.isValid && result.data) {
        validData.push(result.data);
      } else {
        invalidCount++;
        errors.push(`[${index}]: ${result.errors.join(', ')}`);
      }
    });

    return { validData, invalidCount, errors };
  },

  /**
   * 安全取得關聯 ID
   * 用於 unlink 操作前的防禦性檢查
   * @param data 關聯資料物件
   * @param idField 要取得的 ID 欄位名稱
   * @returns ID 值或 null
   */
  safeGetLinkId<T extends Record<string, unknown>>(
    data: T | undefined | null,
    idField: keyof T = 'link_id' as keyof T
  ): number | null {
    if (!data) {
      logger.warn('[ApiResponseValidators] safeGetLinkId: 資料為空');
      return null;
    }

    const value = data[idField];
    if (!this.isValidId(value, String(idField))) {
      logger.warn(`[ApiResponseValidators] safeGetLinkId: ${String(idField)} 無效`, { value, data });
      return null;
    }

    return value as number;
  },
};

// ============================================================
// 匯出統一介面
// ============================================================

export default {
  DocumentValidators,
  StringCleaners,
  AgencyNameParser,
  DateParsers,
  FormRules,
  ApiResponseValidators,
};
