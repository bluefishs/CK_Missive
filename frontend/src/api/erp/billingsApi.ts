/**
 * ERP 請款 API 服務
 */

import { apiClient } from '../client';
import type { SuccessResponse, DeleteResponse } from '../types';
import type {
  ERPBilling,
  ERPBillingCreate,
  ERPBillingUpdate,
} from '../../types/erp';
import { ERP_ENDPOINTS } from '../endpoints';

export const erpBillingsApi = {
  /** 取得報價單請款列表 */
  async list(erpQuotationId: number): Promise<ERPBilling[]> {
    const response = await apiClient.post<SuccessResponse<ERPBilling[]>>(
      ERP_ENDPOINTS.BILLINGS_LIST,
      { erp_quotation_id: erpQuotationId }
    );
    return response.data!;
  },

  /** 建立請款 */
  async create(data: ERPBillingCreate): Promise<ERPBilling> {
    const response = await apiClient.post<SuccessResponse<ERPBilling>>(
      ERP_ENDPOINTS.BILLINGS_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新請款 */
  async update(id: number, data: ERPBillingUpdate): Promise<ERPBilling> {
    const response = await apiClient.post<SuccessResponse<ERPBilling>>(
      ERP_ENDPOINTS.BILLINGS_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除請款 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(ERP_ENDPOINTS.BILLINGS_DELETE, { id });
  },
};
