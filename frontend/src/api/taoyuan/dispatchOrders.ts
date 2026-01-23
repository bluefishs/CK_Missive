/**
 * 桃園查估派工 - 派工單 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  DispatchOrder,
  DispatchOrderCreate,
  DispatchOrderUpdate,
  DispatchOrderListQuery,
  DispatchOrderListResponse,
  DispatchDocumentLinkCreate,
  ExcelImportResult,
  DocumentHistoryMatchResponse,
  DispatchOrderWithHistoryResponse,
} from '../../types/api';

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
   * 取得下一個派工單號（自動生成）
   * 格式: 115年_派工單號001, 115年_派工單號002, ...
   */
  async getNextDispatchNo(): Promise<{
    success: boolean;
    next_dispatch_no: string;
    current_year: number;
    next_sequence: number;
  }> {
    return apiClient.post(API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_NEXT_NO, {});
  },

  /**
   * 建立派工單
   */
  async create(data: DispatchOrderCreate): Promise<DispatchOrder> {
    return apiClient.post<DispatchOrder>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_CREATE,
      data
    );
  },

  /**
   * 取得派工單詳情
   */
  async getDetail(id: number): Promise<DispatchOrder> {
    return apiClient.post<DispatchOrder>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_DETAIL(id),
      {}
    );
  },

  /**
   * 更新派工單
   */
  async update(id: number, data: DispatchOrderUpdate): Promise<DispatchOrder> {
    return apiClient.post<DispatchOrder>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_UPDATE(id),
      data
    );
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

  /**
   * 取得派工單詳情 (含公文歷程)
   */
  async getDetailWithHistory(id: number): Promise<DispatchOrderWithHistoryResponse> {
    return apiClient.post<DispatchOrderWithHistoryResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_DETAIL_WITH_HISTORY(id),
      {}
    );
  },

  /**
   * 匹配公文歷程
   */
  async matchDocuments(projectName: string, includeSubject?: boolean): Promise<DocumentHistoryMatchResponse> {
    return apiClient.post<DocumentHistoryMatchResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.MATCH_DOCUMENTS,
      {
        project_name: projectName,
        include_subject: includeSubject ?? false,
      }
    );
  },

  /**
   * Excel 匯入派工紀錄
   */
  async importExcel(
    file: File,
    contractProjectId: number
  ): Promise<ExcelImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('contract_project_id', String(contractProjectId));

    return apiClient.post<ExcelImportResult>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_IMPORT,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },

  /**
   * 下載匯入範本 (POST + blob 下載，符合資安規範)
   */
  async downloadImportTemplate(): Promise<void> {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
    const url = `${baseUrl}/api${API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_IMPORT_TEMPLATE}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('下載範本失敗');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'dispatch_orders_import_template.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  },
};
