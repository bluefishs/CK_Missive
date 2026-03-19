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
  EntitySimilarityResponse,
  CorrespondenceSuggestionsResponse,
} from '../../types/api';
import type { TaoyuanContractProject } from '../../types/taoyuan';

/**
 * 派工單 API 服務
 */
export const dispatchOrdersApi = {
  /**
   * 取得桃園派工承攬案件列表（用於專案切換下拉選單）
   */
  async getContractProjects(): Promise<TaoyuanContractProject[]> {
    const response = await apiClient.post<{ items: TaoyuanContractProject[] }>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_CONTRACT_PROJECTS,
      {}
    );
    return response.items ?? [];
  },

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
   * 格式: {民國年}年_派工單號001, ...
   * @param contractProjectId 承攬案件 ID（用於從專案名稱解析民國年）
   */
  async getNextDispatchNo(contractProjectId?: number): Promise<{
    success: boolean;
    next_dispatch_no: string;
    current_year: number;
    next_sequence: number;
  }> {
    return apiClient.post(API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_NEXT_NO, {
      contract_project_id: contractProjectId ?? null,
    });
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
   * 批量設定結案批次
   */
  async batchSetBatch(params: {
    dispatch_ids: number[];
    batch_no: number | null;
    batch_label?: string;
  }): Promise<{ success: boolean; updated_count: number; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_BATCH_SET_BATCH,
      params,
    );
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
    linkType?: 'agency_incoming' | 'company_outgoing',
    contractProjectId?: number,
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
        contract_project_id: contractProjectId,
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
   * 匯出派工總表 Excel (同步模式，適合小量資料)
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
   * 提交非同步匯出任務 (適合大量資料，支援進度追蹤)
   */
  async submitAsyncExport(params?: {
    contract_project_id?: number;
    work_type?: string;
    search?: string;
  }): Promise<{ success: boolean; task_id: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_EXPORT_ASYNC,
      params ?? {},
    );
  },

  /**
   * 查詢非同步匯出進度
   */
  async getExportProgress(taskId: string): Promise<{
    success: boolean;
    task_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    total: number;
    message: string;
    filename?: string;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_EXPORT_PROGRESS,
      { task_id: taskId },
    );
  },

  /**
   * 下載非同步匯出結果
   */
  async downloadAsyncExport(taskId: string, filename?: string): Promise<void> {
    await apiClient.downloadPost(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_EXPORT_DOWNLOAD,
      { task_id: taskId },
      filename || 'dispatch_master.xlsx',
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

  /**
   * 知識圖譜實體配對建議
   * 回傳公文間共享實體的相似度分數
   */
  async getEntitySimilarity(dispatchId: number): Promise<EntitySimilarityResponse> {
    return apiClient.post<EntitySimilarityResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ENTITY_SIMILARITY(dispatchId),
      {},
    );
  },

  /**
   * NER 驅動公文對照建議
   * 利用派工單實體連結做來文/發文配對建議
   */
  async getCorrespondenceSuggestions(dispatchId: number): Promise<CorrespondenceSuggestionsResponse> {
    return apiClient.post<CorrespondenceSuggestionsResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_CORRESPONDENCE_SUGGESTIONS(dispatchId),
      {},
    );
  },

  /**
   * 確認公文對照配對（回饋知識圖譜）
   */
  async confirmCorrespondence(
    dispatchId: number,
    pairs: { incoming_doc_id: number; outgoing_doc_id: number }[],
  ): Promise<{ success: boolean; confirmed_count: number; relationships_created: number; relationships_updated: number }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_CONFIRM_CORRESPONDENCE(dispatchId),
      { pairs },
    );
  },
};

// Re-export types for backward compatibility
export type {
  EntitySimilarityPair,
  EntitySimilarityResponse,
  CorrespondenceSuggestion,
  DispatchEntityInfo,
  CorrespondenceSuggestionsResponse,
} from '../../types/api';
