/**
 * 桃園查估派工 - 契金管控/總控表/統計 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  ContractPayment,
  ContractPaymentCreate,
  ContractPaymentUpdate,
  ContractPaymentListResponse,
  PaymentControlResponse,
  MasterControlQuery,
  MasterControlResponse,
  TaoyuanStatisticsResponse,
} from '../../types/api';

/**
 * 契金管控 API 服務
 */
export const contractPaymentsApi = {
  /**
   * 取得契金列表
   */
  async getList(dispatchOrderId: number): Promise<ContractPaymentListResponse> {
    return apiClient.post<ContractPaymentListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PAYMENTS_LIST,
      { dispatch_order_id: dispatchOrderId }
    );
  },

  /**
   * 建立契金紀錄
   */
  async create(data: ContractPaymentCreate): Promise<ContractPayment> {
    const response = await apiClient.post<{ success: boolean; data: ContractPayment }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PAYMENTS_CREATE,
      data
    );
    return response.data;
  },

  /**
   * 更新契金紀錄
   */
  async update(id: number, data: ContractPaymentUpdate): Promise<ContractPayment> {
    const response = await apiClient.post<{ success: boolean; data: ContractPayment }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PAYMENTS_UPDATE(id),
      data
    );
    return response.data;
  },

  /**
   * 刪除契金紀錄
   */
  async delete(id: number): Promise<void> {
    await apiClient.post(API_ENDPOINTS.TAOYUAN_DISPATCH.PAYMENTS_DELETE(id), {});
  },

  /**
   * 取得契金管控展示資料（派工單為主，含派工日期）
   */
  async getControlList(contractProjectId?: number): Promise<PaymentControlResponse> {
    return apiClient.post<PaymentControlResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PAYMENTS_CONTROL,
      { contract_project_id: contractProjectId, limit: 500 }
    );
  },
};

/**
 * 總控表 API 服務
 */
export const masterControlApi = {
  /**
   * 取得總控表資料
   */
  async getReport(params?: MasterControlQuery): Promise<MasterControlResponse> {
    return apiClient.post<MasterControlResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.MASTER_CONTROL,
      params ?? {}
    );
  },
};

/**
 * 統計 API 服務
 */
export const statisticsApi = {
  /**
   * 取得桃園查估派工統計資料
   */
  async getStatistics(contractProjectId: number): Promise<TaoyuanStatisticsResponse> {
    return apiClient.post<TaoyuanStatisticsResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.STATISTICS,
      {},
      {
        params: {
          contract_project_id: contractProjectId,
        },
      }
    );
  },
};
