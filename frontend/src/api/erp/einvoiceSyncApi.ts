/**
 * 電子發票同步 API 服務
 * 對應後端 api/endpoints/erp/einvoice_sync.py
 */
import { apiClient } from '../client';
import type { SuccessResponse } from '../types';
import { ERP_ENDPOINTS } from '../endpoints';
import type {
  ExpenseInvoice,
  EInvoiceSyncRequest,
  EInvoiceSyncLogQuery,
  PendingReceiptQuery,
  SyncResult,
  PendingListResponse,
  SyncLogsResponse,
} from '../../types/erp';

export const einvoiceSyncApi = {
  async sync(params?: EInvoiceSyncRequest): Promise<SuccessResponse<SyncResult>> {
    return apiClient.post<SuccessResponse<SyncResult>>(ERP_ENDPOINTS.EINVOICE_SYNC, params || {});
  },

  async pendingList(params?: PendingReceiptQuery): Promise<PendingListResponse> {
    return apiClient.post<PendingListResponse>(
      ERP_ENDPOINTS.EINVOICE_PENDING_LIST,
      { skip: 0, limit: 20, ...params },
    );
  },

  async uploadReceipt(
    invoiceId: number, file: File, caseCode?: string, category?: string,
  ): Promise<SuccessResponse<ExpenseInvoice>> {
    const additionalData: Record<string, string> = { invoice_id: String(invoiceId) };
    if (caseCode) additionalData.case_code = caseCode;
    if (category) additionalData.category = category;
    return apiClient.upload<SuccessResponse<ExpenseInvoice>>(
      ERP_ENDPOINTS.EINVOICE_UPLOAD_RECEIPT, file, 'file', additionalData,
    );
  },

  async syncLogs(params?: EInvoiceSyncLogQuery): Promise<SyncLogsResponse> {
    return apiClient.post<SyncLogsResponse>(ERP_ENDPOINTS.EINVOICE_SYNC_LOGS, params || {});
  },
};
