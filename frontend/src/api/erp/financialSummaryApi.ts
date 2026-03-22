/**
 * 財務彙總 API 服務
 * 對應後端 api/endpoints/erp/financial_summary.py
 */
import { apiClient } from '../client';
import type { SuccessResponse } from '../types';
import { ERP_ENDPOINTS } from '../endpoints';
import type {
  ProjectFinancialSummary,
  CompanyFinancialOverview,
  ProjectSummaryRequest,
  AllProjectsSummaryRequest,
  CompanyOverviewRequest,
  ProjectsSummaryResponse,
  MonthlyTrendRequest,
  MonthlyTrendResponse,
  BudgetRankingRequest,
  BudgetRankingResponse,
  ExportExpensesRequest,
  ExportLedgerRequest,
} from '../../types/erp';

export const financialSummaryApi = {
  async project(data: ProjectSummaryRequest): Promise<SuccessResponse<ProjectFinancialSummary>> {
    return apiClient.post<SuccessResponse<ProjectFinancialSummary>>(ERP_ENDPOINTS.FINANCIAL_SUMMARY_PROJECT, data);
  },

  async projects(params?: AllProjectsSummaryRequest): Promise<ProjectsSummaryResponse> {
    return apiClient.post<ProjectsSummaryResponse>(ERP_ENDPOINTS.FINANCIAL_SUMMARY_PROJECTS, params || {});
  },

  async company(params?: CompanyOverviewRequest): Promise<SuccessResponse<CompanyFinancialOverview>> {
    return apiClient.post<SuccessResponse<CompanyFinancialOverview>>(ERP_ENDPOINTS.FINANCIAL_SUMMARY_COMPANY, params || {});
  },

  async monthlyTrend(params?: MonthlyTrendRequest): Promise<SuccessResponse<MonthlyTrendResponse>> {
    return apiClient.post<SuccessResponse<MonthlyTrendResponse>>(ERP_ENDPOINTS.FINANCIAL_SUMMARY_MONTHLY_TREND, params || {});
  },

  async budgetRanking(params?: BudgetRankingRequest): Promise<SuccessResponse<BudgetRankingResponse>> {
    return apiClient.post<SuccessResponse<BudgetRankingResponse>>(ERP_ENDPOINTS.FINANCIAL_SUMMARY_BUDGET_RANKING, params || {});
  },

  async exportExpenses(params?: ExportExpensesRequest): Promise<Blob> {
    return apiClient.post<Blob>(ERP_ENDPOINTS.EXPORT_EXPENSES, params || {}, { responseType: 'blob' });
  },

  async exportLedger(params?: ExportLedgerRequest): Promise<Blob> {
    return apiClient.post<Blob>(ERP_ENDPOINTS.EXPORT_LEDGER, params || {}, { responseType: 'blob' });
  },
};
