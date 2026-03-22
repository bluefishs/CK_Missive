/**
 * 統一帳本 API 服務
 * 對應後端 api/endpoints/erp/ledger.py
 */
import { apiClient } from '../client';
import type { SuccessResponse } from '../types';
import { ERP_ENDPOINTS } from '../endpoints';
import type {
  FinanceLedger,
  LedgerCreate,
  LedgerQuery,
  LedgerBalanceRequest,
  LedgerCategoryBreakdownRequest,
  LedgerBalance,
  LedgerCategoryBreakdown,
  LedgerListResponse,
} from '../../types/erp';

export const ledgerApi = {
  async list(params?: LedgerQuery): Promise<LedgerListResponse> {
    return apiClient.post<LedgerListResponse>(ERP_ENDPOINTS.LEDGER_LIST, params || {});
  },

  async create(data: LedgerCreate): Promise<SuccessResponse<FinanceLedger>> {
    return apiClient.post<SuccessResponse<FinanceLedger>>(ERP_ENDPOINTS.LEDGER_CREATE, data);
  },

  async detail(id: number): Promise<SuccessResponse<FinanceLedger>> {
    return apiClient.post<SuccessResponse<FinanceLedger>>(ERP_ENDPOINTS.LEDGER_DETAIL, { id });
  },

  async balance(data: LedgerBalanceRequest): Promise<SuccessResponse<LedgerBalance>> {
    return apiClient.post<SuccessResponse<LedgerBalance>>(ERP_ENDPOINTS.LEDGER_BALANCE, data);
  },

  async categoryBreakdown(data: LedgerCategoryBreakdownRequest): Promise<SuccessResponse<LedgerCategoryBreakdown[]>> {
    return apiClient.post<SuccessResponse<LedgerCategoryBreakdown[]>>(ERP_ENDPOINTS.LEDGER_CATEGORY_BREAKDOWN, data);
  },

  async remove(id: number): Promise<SuccessResponse<null>> {
    return apiClient.post<SuccessResponse<null>>(ERP_ENDPOINTS.LEDGER_DELETE, { id });
  },
};
