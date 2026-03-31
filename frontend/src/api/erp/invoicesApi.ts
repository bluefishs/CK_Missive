/**
 * ERP 發票 API 服務
 */

import { apiClient } from '../client';
import type { SuccessResponse, DeleteResponse } from '../types';
import type {
  ERPInvoice,
  ERPInvoiceCreate,
  ERPInvoiceUpdate,
} from '../../types/erp';
import { ERP_ENDPOINTS } from '../endpoints';

export const erpInvoicesApi = {
  /** 取得報價單發票列表 */
  async list(erpQuotationId: number): Promise<ERPInvoice[]> {
    const response = await apiClient.post<SuccessResponse<ERPInvoice[]>>(
      ERP_ENDPOINTS.INVOICES_LIST,
      { erp_quotation_id: erpQuotationId }
    );
    return response.data!;
  },

  /** 建立發票 */
  async create(data: ERPInvoiceCreate): Promise<ERPInvoice> {
    const response = await apiClient.post<SuccessResponse<ERPInvoice>>(
      ERP_ENDPOINTS.INVOICES_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新發票 */
  async update(id: number, data: ERPInvoiceUpdate): Promise<ERPInvoice> {
    const response = await apiClient.post<SuccessResponse<ERPInvoice>>(
      ERP_ENDPOINTS.INVOICES_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除發票 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(ERP_ENDPOINTS.INVOICES_DELETE, { id });
  },

  /** 從請款記錄開立發票 */
  async createFromBilling(data: {
    billing_id: number;
    invoice_number: string;
    invoice_date?: string;
    notes?: string;
  }): Promise<ERPInvoice> {
    const response = await apiClient.post<SuccessResponse<ERPInvoice>>(
      ERP_ENDPOINTS.INVOICES_CREATE_FROM_BILLING,
      data,
    );
    return response.data!;
  },
};
