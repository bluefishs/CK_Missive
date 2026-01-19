/**
 * 桃園查估派工管理系統 API 服務
 *
 * 使用統一的 API Client 和型別定義
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { apiClient } from './client';
import { API_ENDPOINTS } from './endpoints';
import {
  TaoyuanProject,
  TaoyuanProjectCreate,
  TaoyuanProjectUpdate,
  TaoyuanProjectListQuery,
  TaoyuanProjectListResponse,
  DispatchOrder,
  DispatchOrderCreate,
  DispatchOrderUpdate,
  DispatchOrderListQuery,
  DispatchOrderListResponse,
  DispatchDocumentLinkCreate,
  ContractPayment,
  ContractPaymentCreate,
  ContractPaymentUpdate,
  ContractPaymentListResponse,
  MasterControlQuery,
  MasterControlResponse,
  ExcelImportResult,
} from '../types/api';

// ============================================================================
// 轄管工程 API
// ============================================================================

/**
 * 轄管工程 API 服務
 */
export const taoyuanProjectsApi = {
  /**
   * 取得轄管工程列表
   */
  async getList(params?: TaoyuanProjectListQuery): Promise<TaoyuanProjectListResponse> {
    return apiClient.post<TaoyuanProjectListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_LIST,
      params ?? {}
    );
  },

  /**
   * 建立轄管工程
   */
  async create(data: TaoyuanProjectCreate): Promise<TaoyuanProject> {
    const response = await apiClient.post<{ success: boolean; data: TaoyuanProject }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_CREATE,
      data
    );
    return response.data;
  },

  /**
   * 取得轄管工程詳情
   */
  async getDetail(id: number): Promise<TaoyuanProject> {
    const response = await apiClient.post<{ success: boolean; data: TaoyuanProject }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_DETAIL(id),
      {}
    );
    return response.data;
  },

  /**
   * 更新轄管工程
   */
  async update(id: number, data: TaoyuanProjectUpdate): Promise<TaoyuanProject> {
    const response = await apiClient.post<{ success: boolean; data: TaoyuanProject }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_UPDATE(id),
      data
    );
    return response.data;
  },

  /**
   * 刪除轄管工程
   */
  async delete(id: number): Promise<void> {
    await apiClient.post(API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_DELETE(id), {});
  },

  /**
   * Excel 匯入工程資料
   */
  async importExcel(
    file: File,
    contractProjectId: number,
    reviewYear?: number
  ): Promise<ExcelImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('contract_project_id', String(contractProjectId));
    if (reviewYear) {
      formData.append('review_year', String(reviewYear));
    }

    return apiClient.post<ExcelImportResult>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_IMPORT,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },
};

// ============================================================================
// 派工單 API
// ============================================================================

/**
 * 派工單 API 服務
 */
export const dispatchOrdersApi = {
  /**
   * 取得派工單列表
   */
  async getList(params?: DispatchOrderListQuery): Promise<DispatchOrderListResponse> {
    return apiClient.post<DispatchOrderListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_LIST,
      params ?? {}
    );
  },

  /**
   * 建立派工單
   */
  async create(data: DispatchOrderCreate): Promise<DispatchOrder> {
    const response = await apiClient.post<{ success: boolean; data: DispatchOrder }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_CREATE,
      data
    );
    return response.data;
  },

  /**
   * 取得派工單詳情
   */
  async getDetail(id: number): Promise<DispatchOrder> {
    const response = await apiClient.post<{ success: boolean; data: DispatchOrder }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_DETAIL(id),
      {}
    );
    return response.data;
  },

  /**
   * 更新派工單
   */
  async update(id: number, data: DispatchOrderUpdate): Promise<DispatchOrder> {
    const response = await apiClient.post<{ success: boolean; data: DispatchOrder }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_UPDATE(id),
      data
    );
    return response.data;
  },

  /**
   * 刪除派工單
   */
  async delete(id: number): Promise<void> {
    await apiClient.post(API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_DELETE(id), {});
  },

  /**
   * 新增公文關聯
   */
  async linkDocument(dispatchOrderId: number, data: DispatchDocumentLinkCreate): Promise<void> {
    await apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_LINK_DOCUMENT(dispatchOrderId),
      data
    );
  },

  /**
   * 移除公文關聯
   */
  async unlinkDocument(dispatchOrderId: number, linkId: number): Promise<void> {
    await apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_UNLINK_DOCUMENT(dispatchOrderId, linkId),
      {}
    );
  },
};

// ============================================================================
// 契金管控 API
// ============================================================================

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
};

// ============================================================================
// 總控表 API
// ============================================================================

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

// ============================================================================
// 統一匯出
// ============================================================================

/**
 * 桃園派工管理 API 統一入口
 */
export const taoyuanDispatchApi = {
  projects: taoyuanProjectsApi,
  dispatchOrders: dispatchOrdersApi,
  payments: contractPaymentsApi,
  masterControl: masterControlApi,
};

export default taoyuanDispatchApi;
