/**
 * ERP 廠商應付 API 服務
 */

import { apiClient } from '../client';
import type { SuccessResponse, DeleteResponse } from '../types';
import type {
  ERPVendorPayable,
  ERPVendorPayableCreate,
  ERPVendorPayableUpdate,
} from '../../types/erp';
import { ERP_ENDPOINTS } from '../endpoints';

export const erpVendorPayablesApi = {
  /** 取得報價單廠商應付列表 */
  async list(erpQuotationId: number): Promise<ERPVendorPayable[]> {
    const response = await apiClient.post<SuccessResponse<ERPVendorPayable[]>>(
      ERP_ENDPOINTS.VENDOR_PAYABLES_LIST,
      { erp_quotation_id: erpQuotationId }
    );
    return response.data!;
  },

  /** 建立廠商應付 */
  async create(data: ERPVendorPayableCreate): Promise<ERPVendorPayable> {
    const response = await apiClient.post<SuccessResponse<ERPVendorPayable>>(
      ERP_ENDPOINTS.VENDOR_PAYABLES_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新廠商應付 */
  async update(id: number, data: ERPVendorPayableUpdate): Promise<ERPVendorPayable> {
    const response = await apiClient.post<SuccessResponse<ERPVendorPayable>>(
      ERP_ENDPOINTS.VENDOR_PAYABLES_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除廠商應付 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(ERP_ENDPOINTS.VENDOR_PAYABLES_DELETE, { id });
  },
};
