/**
 * 案件附件型別（SSOT）。
 *
 * 2026-08-19：抽自 `pmCase/QuotationRecordsTab.tsx` 的本地 interface。
 *
 * 為什麼獨立一個檔：這組型別會被**多個模組**共用（報價紀錄、報價單詳情、
 * 承攬案件附件、日後的公文附件遷移），放在任何一個頁面底下都會讓其他頁面
 * 去 import 一個「別人的頁面」—— 那是異質同工的起點。
 */

/** 對應後端 `pm_case_attachments` */
export interface CaseAttachment {
  id: number;
  file_name: string;
  file_size?: number;
  mime_type?: string;
  notes?: string;
  uploaded_by?: number;
  created_at?: string;
  /**
   * 文件類型（2026-08-19 新增）。
   *
   * `generated_quotation` 系統輸出的報價單
   * `signed_quotation`    客戶回簽的報價單
   * `other`               人工判定過、確認是其他佐證
   * `undefined`/`null`    **還沒有人分類過**（與 other 意思不同）
   */
  doc_type?: string | null;
}

export interface CaseAttachmentListResponse {
  success: boolean;
  attachments: CaseAttachment[];
  total: number;
}

/** 文件類型的顯示標籤 */
export const ATTACHMENT_DOC_TYPE_LABELS: Record<string, string> = {
  generated_quotation: '系統產出報價單',
  contract_document: '契約文件',
  signed_quotation: '客戶回簽',
  other: '其他佐證',
};

/** 文件類型的標籤顏色 */
export const ATTACHMENT_DOC_TYPE_COLORS: Record<string, string> = {
  generated_quotation: 'blue',
  contract_document: 'purple',
  signed_quotation: 'green',
  other: 'default',
};
