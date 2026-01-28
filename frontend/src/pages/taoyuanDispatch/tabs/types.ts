/**
 * TaoyuanDispatchDetailPage Tab 元件型別定義
 *
 * @version 1.1.0
 * @date 2026-01-26
 */

import type { FormInstance } from 'antd';
import type {
  DispatchOrder,
  DispatchDocumentLink,
  DispatchAttachment,
  OfficialDocument,
  LinkType,
  ContractPayment,
  ContractPaymentCreate,
} from '../../../types/api';
import type { UploadFile } from 'antd/es/upload';
import type { UseMutationResult } from '@tanstack/react-query';

// ============================================================================
// 公文關聯 Tab Props 型別定義
// ============================================================================

/** 公文關聯 Tab Props */
export interface DispatchDocumentsTabProps {
  /** 派工單資料 */
  dispatch: DispatchOrder | undefined;
  /** 是否可編輯 */
  canEdit: boolean;
  /** 是否載入中 */
  isLoading: boolean;

  // 公文搜尋相關
  /** 公文搜尋關鍵字 */
  docSearchKeyword: string;
  /** 設定公文搜尋關鍵字 */
  setDocSearchKeyword: (keyword: string) => void;
  /** 可選公文列表（搜尋結果） */
  availableDocs: OfficialDocument[];
  /** 是否正在搜尋公文 */
  searchingDocs: boolean;

  // 選取狀態
  /** 選取的公文 ID */
  selectedDocId: number | undefined;
  /** 設定選取的公文 ID */
  setSelectedDocId: (id: number | undefined) => void;
  /** 選取的關聯類型 */
  selectedLinkType: LinkType;
  /** 設定選取的關聯類型 */
  setSelectedLinkType: (type: LinkType) => void;

  // 操作 handlers
  /** 處理建立關聯 */
  onLinkDocument: () => void;
  /** 建立關聯 mutation 狀態 */
  linkDocMutationPending: boolean;
  /** 處理解除關聯 */
  onUnlinkDocument: (linkId: number) => void;
  /** 解除關聯 mutation 狀態 */
  unlinkDocMutationPending: boolean;

  /** 重新取得資料 */
  refetch: () => void;
  /** 導航函數 */
  navigate: (path: string) => void;
}

// ============================================================================
// 附件管理 Tab Props 型別定義
// ============================================================================

/** 附件管理 Tab Props */
export interface DispatchAttachmentsTabProps {
  /** 派工單 ID */
  dispatchId: number;
  /** 是否為編輯模式 */
  isEditing: boolean;
  /** 是否正在載入 */
  isLoading: boolean;
  /** 附件列表 */
  attachments: DispatchAttachment[];
  /** 待上傳檔案列表 */
  fileList: UploadFile[];
  /** 設定待上傳檔案列表 */
  setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>;
  /** 是否正在上傳 */
  uploading: boolean;
  /** 上傳進度 (0-100) */
  uploadProgress: number;
  /** 上傳錯誤訊息列表 */
  uploadErrors: string[];
  /** 設定上傳錯誤訊息列表 */
  setUploadErrors: React.Dispatch<React.SetStateAction<string[]>>;
  /** 上傳附件 mutation */
  uploadAttachmentsMutation: UseMutationResult<unknown, Error, void, unknown>;
  /** 刪除附件 mutation */
  deleteAttachmentMutation: UseMutationResult<unknown, Error, number, unknown>;
}

// ============================================================================
// 輔助函數型別
// ============================================================================

/** 根據公文字號判斷關聯類型 */
export type DetectLinkTypeFn = (docNumber?: string) => LinkType;

// ============================================================================
// 契金維護 Tab Props 型別定義
// ============================================================================

/** 契金維護 Tab Props */
export interface DispatchPaymentTabProps {
  /** 派工單資料 */
  dispatch?: DispatchOrder;
  /** 契金資料 */
  paymentData?: ContractPayment | null;
  /** 是否可編輯 */
  canEdit: boolean;
  /** 是否處於編輯模式 */
  isPaymentEditing: boolean;
  /** 設定編輯模式 */
  setIsPaymentEditing: (editing: boolean) => void;
  /** 契金表單實例 */
  paymentForm: FormInstance;
  /** 儲存中狀態 */
  isSaving: boolean;
  /** 儲存契金處理函數 */
  onSavePayment: (values: ContractPaymentCreate) => void;
}
