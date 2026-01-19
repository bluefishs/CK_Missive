/**
 * 核心業務類型定義
 * 統一整個應用程式的類型系統
 *
 * @version 4.0
 * @date 2026-01-06
 *
 * 變更記錄：
 * - v4.0: 統一型別定義，移除重複，與後端 Schema 對應
 * - v3.0: 整合 API 型別定義
 * - v2.0: 初始版本
 */

// ============================================================================
// 匯出 API 業務型別（與後端 Schema 對應）- 單一真實來源
// ============================================================================
export * from './api';

// ============================================================================
// 匯出 API 回應格式（從 api/types.ts）
// ============================================================================
export type {
  ErrorCode,
  ErrorDetail,
  ApiError,
  ErrorResponse,
  SuccessResponse,
  PaginationParams,
  PaginationMeta,
  PaginatedResponse,
  SortOrder,
  SortParams,
  BaseQueryParams,
  DeleteResponse,
  BatchOperationResponse,
  SelectOption,
  LegacyListResponse,
  ApiResponse,
  isErrorResponse,
  isSuccessResponse,
  isPaginatedResponse,
  isLegacyListResponse,
  normalizePaginatedResponse,
} from '../api/types';

// ============================================================================
// 基礎類型 - 與資料庫對應 (ID 使用 number)
// ============================================================================

/** 基礎實體介面 - ID 為 number (與資料庫對應) */
export interface BaseEntity {
  readonly id: number;
  readonly created_at: string;
  readonly updated_at: string;
}

/** API 響應類型 (通用) */
export interface GenericApiResponse<TData = unknown> {
  readonly success: boolean;
  readonly data?: TData;
  readonly error?: string;
  readonly message?: string;
  readonly code?: string;
}

/** 查詢參數 (通用) */
export interface QueryParams {
  readonly page?: number;
  readonly limit?: number;
  readonly offset?: number;
  readonly search?: string;
  readonly sort_by?: string;
  readonly sort_order?: 'asc' | 'desc';
  readonly filters?: Record<string, unknown>;
}

// ============================================================================
// Store 相關類型
// ============================================================================

/** 基礎 Store 狀態 */
export interface BaseStoreState<TData> {
  readonly data: readonly TData[];
  readonly loading: boolean;
  readonly error: string | null;
  readonly initialized: boolean;
}

/** 分頁 Store 狀態 */
export interface PaginatedStoreState<TData> extends BaseStoreState<TData> {
  readonly pagination: {
    readonly total: number;
    readonly page: number;
    readonly limit: number;
    readonly has_next: boolean;
    readonly has_prev: boolean;
  };
}

/** Store 動作介面 */
export interface BaseStoreActions<TData, TCreateData = Partial<TData>, TUpdateData = Partial<TData>> {
  // 查詢動作
  readonly fetch: (params?: QueryParams) => Promise<void>;
  readonly fetchById: (id: number) => Promise<TData | null>;
  readonly search: (query: string) => Promise<void>;

  // 修改動作
  readonly create: (data: TCreateData) => Promise<void>;
  readonly update: (id: number, data: TUpdateData) => Promise<void>;
  readonly delete: (id: number) => Promise<void>;

  // 狀態管理
  readonly setLoading: (loading: boolean) => void;
  readonly setError: (error: string | null) => void;
  readonly clearError: () => void;
  readonly reset: () => void;
}

// ============================================================================
// 表單相關類型
// ============================================================================

/** 表單欄位類型 */
export type FormFieldType =
  | 'text'
  | 'email'
  | 'password'
  | 'number'
  | 'tel'
  | 'url'
  | 'textarea'
  | 'select'
  | 'multiselect'
  | 'checkbox'
  | 'radio'
  | 'date'
  | 'datetime'
  | 'file'
  | 'rich-text';

/** 表單驗證規則 */
export interface ValidationRule {
  readonly required?: boolean;
  readonly minLength?: number;
  readonly maxLength?: number;
  readonly min?: number;
  readonly max?: number;
  readonly pattern?: RegExp;
  readonly custom?: (value: unknown) => string | undefined;
}

/** 表單欄位定義 */
export interface FormField<TValue = unknown> {
  readonly name: string;
  readonly label: string;
  readonly type: FormFieldType;
  readonly placeholder?: string;
  readonly defaultValue?: TValue;
  readonly options?: readonly FormOption[];
  readonly validation?: ValidationRule;
  readonly disabled?: boolean;
  readonly description?: string;
}

/** 表單選項 */
export interface FormOption {
  readonly label: string;
  readonly value: string | number | boolean;
  readonly disabled?: boolean;
}

/** 表單狀態 */
export interface FormState<TData = Record<string, unknown>> {
  readonly values: TData;
  readonly errors: Record<keyof TData, string>;
  readonly touched: Record<keyof TData, boolean>;
  readonly isValid: boolean;
  readonly isSubmitting: boolean;
  readonly isDirty: boolean;
}

// ============================================================================
// 元件 Props 類型
// ============================================================================

/** 基礎元件 Props */
export interface BaseComponentProps {
  readonly className?: string;
  readonly style?: React.CSSProperties;
  readonly testId?: string;
}

/** 可點擊元件 Props */
export interface ClickableProps {
  readonly onClick?: (event: React.MouseEvent) => void;
  readonly disabled?: boolean;
}

/** 載入狀態 Props */
export interface LoadingProps {
  readonly loading?: boolean;
  readonly loadingText?: string;
}

// ============================================================================
// 錯誤處理類型
// ============================================================================

/** 應用程式錯誤類型 */
export type AppErrorType =
  | 'validation'
  | 'authentication'
  | 'authorization'
  | 'network'
  | 'server'
  | 'client'
  | 'unknown';

/** 應用程式錯誤介面 */
export interface AppError {
  readonly type: AppErrorType;
  readonly code: string;
  readonly message: string;
  readonly details?: unknown;
  readonly timestamp: Date;
}

// ============================================================================
// 工具類型
// ============================================================================

/** 使所有屬性可選 */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/** 使所有屬性必需 */
export type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;

/** 深度只讀 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends (infer U)[]
    ? readonly DeepReadonly<U>[]
    : T[P] extends readonly (infer U)[]
    ? readonly DeepReadonly<U>[]
    : T[P] extends object
    ? DeepReadonly<T[P]>
    : T[P];
};

/** ID 類型 - 使用 number (與資料庫對應) */
export type EntityId = number;

/** 時間戳類型 */
export type Timestamp = string;  // ISO 8601 格式字串

// ============================================================================
// 環境變數類型
// ============================================================================

/** 環境變數配置 */
export interface EnvironmentConfig {
  readonly NODE_ENV: 'development' | 'production' | 'test';
  readonly API_BASE_URL: string;
  readonly API_TIMEOUT: number;
  readonly ENABLE_DEV_TOOLS: boolean;
}

// ============================================================================
// 向後相容別名 (逐步淘汰)
// ============================================================================

/** @deprecated 使用 OfficialDocument */
export type { OfficialDocument as Document } from './api';

// 型別別名 (為向後相容保留)
export type { DocType as DocumentType } from './api';
export type { DocStatus as DocumentStatus } from './api';
export type { DocumentFilter } from './api';
export type { DocumentAttachment } from './api';
export type { DocumentPriority } from './api';

/** 建立公文請求 - 別名 */
export type { DocumentCreate as CreateDocumentRequest } from './api';

/** 更新公文請求 - 別名 */
export type { DocumentUpdate as UpdateDocumentRequest } from './api';

// 承攬案件型別 - 統一匯出
export type {
  ContractCase,
  ContractCaseFilter,
  ContractCaseListParams,
  ContractCaseListResponse,
  ViewMode,
  BoardItem,
} from './api';
export {
  ContractCaseType,
  ContractCaseStatus,
  CONTRACT_CASE_TYPE_LABELS,
  CONTRACT_CASE_TYPE_COLORS,
  CONTRACT_CASE_STATUS_LABELS,
  CONTRACT_CASE_STATUS_COLORS,
} from './api';

// 使用者管理型別 - 統一匯出
export type {
  Permission,
  UserPermissions,
  UserFormData,
  UserPagination,
} from './api';

// 確保此檔案被視為模組
export {};
