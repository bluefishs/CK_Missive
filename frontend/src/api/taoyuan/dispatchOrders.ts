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
   * 搜尋可關聯的桃園派工公文
   *
   * 此方法只回傳 contract_project_id = 21 (桃園查估派工專案) 的公文
   * 用於派工單公文關聯的下拉選單
   *
   * @param keyword 搜尋關鍵字（公文字號或主旨）
   * @param limit 回傳筆數上限
   * @param excludeDocumentIds 排除的公文 ID 列表（已關聯的公文）
   * @param linkType 關聯類型 ('agency_incoming' | 'company_outgoing')
   *                 - agency_incoming: 只顯示機關公文（排除「乾坤」開頭）
   *                 - company_outgoing: 只顯示「乾坤」開頭的公文
   */
  async searchLinkableDocuments(
    keyword: string,
    limit = 20,
    excludeDocumentIds?: number[],
    linkType?: 'agency_incoming' | 'company_outgoing'
  ): Promise<{
    success: boolean;
    items: Array<{
      id: number;
      doc_number: string | null;
      subject: string | null;
      doc_date: string | null;
      category: string | null;
      sender: string | null;
      receiver: string | null;
    }>;
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_SEARCH_LINKABLE_DOCUMENTS,
      {
        keyword,
        limit,
        exclude_document_ids: excludeDocumentIds,
        link_type: linkType,
      }
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
  async matchDocuments(
    projectName: string,
    dispatchId?: number,
  ): Promise<DocumentHistoryMatchResponse> {
    const body: Record<string, unknown> = { project_name: projectName };
    if (dispatchId != null) {
      body.dispatch_id = dispatchId;
    }
    return apiClient.post<DocumentHistoryMatchResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.MATCH_DOCUMENTS,
      body,
    );
  },

  /**
   * 匯出派工總表 Excel (5 工作表: 派工總表/作業紀錄/公文矩陣/契金/統計)
   *
   * 使用 apiClient.downloadPost 確保 auth/CSRF/token refresh 正確處理。
   */
  async exportMasterExcel(params?: {
    contract_project_id?: number;
    work_type?: string;
    search?: string;
  }): Promise<void> {
    await apiClient.downloadPost(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_EXPORT_EXCEL,
      params ?? {},
      'dispatch_master.xlsx',
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
    await apiClient.downloadPost(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_IMPORT_TEMPLATE,
      {},
      'dispatch_orders_import_template.xlsx',
    );
  },
};
