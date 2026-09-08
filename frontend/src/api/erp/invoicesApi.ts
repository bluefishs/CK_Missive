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
    /** 2026-09-08（第二版）：填的是**發票種類**（聯式），而銷售額與稅額一律由發票金額反算。
     *  owner：「原用意是書寫發票所需數據，係由發票金額反算稅額(發票)與銷售額(發票)」。
     *  ⚠️ 聯式與課稅別是兩個維度 —— 二聯式（機關／個人）一樣可以是應稅。 */
    invoice_kind?: 'triplicate' | 'duplicate';
    /** 零稅率／免稅（與聯式無關） */
    tax_exempt?: boolean;
    buyer_name?: string;
    buyer_tax_id?: string;
    invoice_remark?: string;
  }): Promise<ERPInvoice> {
    const response = await apiClient.post<SuccessResponse<ERPInvoice>>(
      ERP_ENDPOINTS.INVOICES_CREATE_FROM_BILLING,
      data,
    );
    return response.data!;
  },

  /** 把已登錄但未關聯請款的發票掛到某期請款（2026-09-04） */
  async linkToBilling(data: { invoice_id: number; billing_id: number }): Promise<ERPInvoice> {
    const response = await apiClient.post<SuccessResponse<ERPInvoice>>(ERP_ENDPOINTS.INVOICES_LINK_TO_BILLING, data);
    return response.data!;
  },
};
