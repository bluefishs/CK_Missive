/**
 * 核心業務類型定義
 * 統一整個應用程式的類型系統
 *
 * @version 3.0
 * @date 2026-01-05
 *
 * 變更記錄：
 * - v3.0: 整合 API 型別定義，與後端 Schema 對應
 * - v2.0: 初始版本
 */

// 匯出 API 業務型別（與後端 Schema 對應）
export * from './api';

// 匯出 API 回應格式（從 api/types.ts 重新匯出）
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
} from '../api/types';

// ===================== 基礎類型 =====================

/** 基礎實體介面 */
export interface BaseEntity {
  readonly id: string;
  readonly createdAt: Date;
  readonly updatedAt: Date;
}

/** API 響應類型 */
export interface ApiResponse<TData = unknown> {
  readonly success: boolean;
  readonly data?: TData;
  readonly error?: string;
  readonly message?: string;
  readonly code?: string;
}

/** 分頁參數 */
export interface PaginationParams {
  readonly page?: number;
  readonly limit?: number;
  readonly offset?: number;
}

/** 排序參數 */
export interface SortParams {
  readonly sortBy?: string;
  readonly sortOrder?: 'asc' | 'desc';
}

/** 查詢參數 */
export interface QueryParams extends PaginationParams, SortParams {
  readonly search?: string;
  readonly filters?: Record<string, unknown>;
}

/** 分頁響應 */
export interface PaginatedResponse<TData = unknown> {
  readonly data: readonly TData[];
  readonly total: number;
  readonly page: number;
  readonly limit: number;
  readonly hasNextPage: boolean;
  readonly hasPrevPage: boolean;
}

// ===================== 用戶相關類型 =====================

/** 用戶角色 */
export type UserRole = 'admin' | 'editor' | 'viewer' | 'guest';

/** 用戶狀態 */
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'pending';

/** 用戶介面 */
export interface User extends BaseEntity {
  readonly name: string;
  readonly email: string;
  readonly avatar?: string;
  readonly role: UserRole;
  readonly status: UserStatus;
  readonly lastLoginAt?: Date;
  readonly preferences?: UserPreferences;
}

/** 用戶偏好設定 */
export interface UserPreferences {
  readonly theme?: 'light' | 'dark' | 'auto';
  readonly language?: string;
  readonly notifications?: NotificationSettings;
}

/** 通知設定 */
export interface NotificationSettings {
  readonly email: boolean;
  readonly push: boolean;
  readonly sms: boolean;
}

// ===================== 文件相關類型 =====================

/** 文件狀態 */
export type DocumentStatus = 'draft' | 'review' | 'published' | 'archived' | 'deleted';

/** 文件類型 */
export type DocumentType = 'article' | 'report' | 'memo' | 'letter' | 'contract';

/** 文件優先級 */
export type DocumentPriority = 'low' | 'normal' | 'high' | 'urgent';

/** 文件介面 - 基於實際資料庫結構 */
export interface Document {
  readonly id: number;
  readonly doc_number?: string;
  readonly doc_type?: string;
  readonly subject?: string;
  readonly sender?: string;
  readonly receiver?: string;
  readonly doc_date?: string;
  readonly serial_number?: number;
  readonly status?: string;
  readonly notion_id?: string;
  readonly created_at?: string;
  readonly updated_at?: string;
  readonly priority?: number;
  readonly tags?: string;
  readonly created_by?: number;
  readonly updated_by?: number;
  readonly category?: string;
  readonly doc_class?: string;
  readonly doc_word?: string;
  readonly contract_case?: string;
  readonly receive_date?: string;
  readonly send_date?: string;
  readonly user_confirm?: boolean;
  readonly auto_serial?: number;
  readonly doc_zi?: string;          // 公文「字」部分，如「桃工用」
  readonly doc_wen_hao?: string;     // 公文「文號」部分，如「1140024090」

  // 發文形式與附件欄位
  readonly delivery_method?: string;  // 發文形式 (電子/紙本/電子+紙本)
  readonly has_attachment?: boolean;  // 是否含附件

  // 承攬案件關聯資訊
  readonly contract_project_id?: number;    // 承攬案件 ID
  readonly contract_project_name?: string;  // 承攬案件名稱
  readonly assigned_staff?: Array<{         // 負責業務同仁
    user_id: number;
    name: string;
    role: string;
  }>;

  // 兼容舊版本欄位
  readonly title?: string;
  readonly content?: string;
  readonly hasAttachments?: boolean;  // 舊版附件欄位
}

/** 文件附件 */
export interface DocumentAttachment {
  readonly id: string;
  readonly filename: string;
  readonly size: number;
  readonly mimeType: string;
  readonly url: string;
}

/** 文件元數據 */
export interface DocumentMetadata {
  readonly wordCount?: number;
  readonly readingTime?: number;
  readonly language?: string;
  readonly category?: string;
  readonly priority?: DocumentPriority;
}

/** 文件篩選器 - 基於實際資料庫結構 */
export interface DocumentFilter {
  readonly search?: string;
  readonly doc_type?: string;
  readonly status?: string;
  readonly sender?: string;
  readonly receiver?: string;
  readonly doc_number?: string;
  readonly doc_date?: string;
  readonly doc_date_from?: string;
  readonly doc_date_to?: string;
  readonly year?: string;
  readonly receive_date_from?: string;
  readonly receive_date_to?: string;
  readonly send_date_from?: string;
  readonly send_date_to?: string;
  readonly category?: string;
  readonly tags?: string;
  readonly contract_case?: string;
  readonly priority?: number;
  readonly sortBy?: string;
  readonly sortOrder?: string;
  
  // 兼容舊版本欄位
  readonly type?: DocumentType;
  readonly creator?: string;
  readonly assignee?: string;
  readonly date_from?: string;
  readonly date_to?: string;
  readonly dateFrom?: string;
  readonly dateTo?: string;
}

/** 文件創建請求 */
export interface CreateDocumentRequest {
  readonly title: string;
  readonly content: string;
  readonly doc_type: DocumentType;
  readonly priority?: DocumentPriority;
  readonly category?: string;
  readonly assignee?: string;
  readonly due_date?: string;
  readonly tags?: readonly string[];
  readonly metadata?: Partial<DocumentMetadata>;
}

/** 文件更新請求 */
export interface UpdateDocumentRequest {
  readonly title?: string;
  readonly content?: string;
  readonly status?: DocumentStatus;
  readonly priority?: DocumentPriority;
  readonly category?: string;
  readonly assignee?: string;
  readonly due_date?: string;
  readonly tags?: readonly string[];
  readonly metadata?: Partial<DocumentMetadata>;
}

// ===================== Store 相關類型 =====================

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
    readonly hasNextPage: boolean;
    readonly hasPrevPage: boolean;
  };
}

/** Store 動作介面 */
export interface BaseStoreActions<TData, TCreateData = Partial<TData>, TUpdateData = Partial<TData>> {
  // 查詢動作
  readonly fetch: (params?: QueryParams) => Promise<void>;
  readonly fetchById: (id: string) => Promise<TData | null>;
  readonly search: (query: string) => Promise<void>;
  
  // 修改動作
  readonly create: (data: TCreateData) => Promise<void>;
  readonly update: (id: string, data: TUpdateData) => Promise<void>;
  readonly delete: (id: string) => Promise<void>;
  
  // 狀態管理
  readonly setLoading: (loading: boolean) => void;
  readonly setError: (error: string | null) => void;
  readonly clearError: () => void;
  readonly reset: () => void;
}

// ===================== 表單相關類型 =====================

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

// ===================== 元件 Props 類型 =====================

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

// ===================== 錯誤處理類型 =====================

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

// ===================== 工具類型 =====================

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

/** ID 類型 */
export type ID = string;

/** 時間戳類型 */
export type Timestamp = Date;

// ===================== 環境變數類型 =====================

/** 環境變數配置 */
export interface EnvironmentConfig {
  readonly NODE_ENV: 'development' | 'production' | 'test';
  readonly API_BASE_URL: string;
  readonly API_TIMEOUT: number;
  readonly ENABLE_DEV_TOOLS: boolean;
}

// 確保此檔案被視為模組
export {};