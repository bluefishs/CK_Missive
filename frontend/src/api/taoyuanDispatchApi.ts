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
  PaymentControlResponse,
  MasterControlQuery,
  MasterControlResponse,
  ExcelImportResult,
  DocumentHistoryMatchResponse,
  DispatchOrderWithHistoryResponse,
  // 關聯型別
  LinkType,
  DocumentDispatchLink,
  DocumentProjectLink,
  ProjectDispatchLink,
  // 統計型別
  TaoyuanStatisticsResponse,
  // 附件型別
  DispatchAttachment,
  DispatchAttachmentListResponse,
  DispatchAttachmentUploadResult,
  DispatchAttachmentDeleteResult,
  DispatchAttachmentVerifyResult,
} from '../types/api';

// 重新匯出關聯型別供外部使用
export type { LinkType, DocumentDispatchLink, DocumentProjectLink, ProjectDispatchLink };

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
    // 後端直接返回 TaoyuanProjectSchema，非包裝格式
    return apiClient.post<TaoyuanProject>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_DETAIL(id),
      {}
    );
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

  /**
   * 下載匯入範本 (POST + blob 下載，符合資安規範)
   */
  async downloadImportTemplate(): Promise<void> {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
    const url = `${baseUrl}/api${API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_IMPORT_TEMPLATE}`;

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
    link.download = 'taoyuan_projects_import_template.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
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
   * 後端直接返回 DispatchOrderSchema，非包裝格式
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
    // 後端直接返回 DispatchOrderSchema，非包裝格式
    return apiClient.post<DispatchOrder>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ORDERS_DETAIL(id),
      {}
    );
  },

  /**
   * 更新派工單
   * 後端直接返回 DispatchOrderSchema，非包裝格式
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
   * 對應原始需求欄位 14-17
   */
  async getDetailWithHistory(id: number): Promise<DispatchOrderWithHistoryResponse> {
    return apiClient.post<DispatchOrderWithHistoryResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_DETAIL_WITH_HISTORY(id),
      {}
    );
  },

  /**
   * 匹配公文歷程
   * 根據工程名稱自動匹配公文紀錄
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
   * 對應原始需求的 12 個欄位
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
// 統計 API
// ============================================================================

/**
 * 統計 API 服務
 */
export const statisticsApi = {
  /**
   * 取得桃園查估派工統計資料
   * 包含工程、派工、契金三大類統計數據
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

// ============================================================================
// 統一匯出
// ============================================================================

// ============================================================================
// 公文關聯 API (以公文為主體)
// ============================================================================

/**
 * 公文關聯 API 服務
 */
export const documentLinksApi = {
  /**
   * 查詢公文關聯的派工單
   */
  async getDispatchLinks(documentId: number): Promise<{
    success: boolean;
    document_id: number;
    dispatch_orders: DocumentDispatchLink[];
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_DISPATCH_LINKS(documentId),
      {}
    );
  },

  /**
   * 將公文關聯到派工單
   */
  async linkDispatch(
    documentId: number,
    dispatchOrderId: number,
    linkType: 'agency_incoming' | 'company_outgoing' = 'agency_incoming'
  ): Promise<{ success: boolean; message: string; link_id: number }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_LINK_DISPATCH(documentId),
      {},
      {
        params: {
          dispatch_order_id: dispatchOrderId,
          link_type: linkType,
        },
      }
    );
  },

  /**
   * 移除公文與派工的關聯
   */
  async unlinkDispatch(documentId: number, linkId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_UNLINK_DISPATCH(documentId, linkId),
      {}
    );
  },

  /**
   * 批次查詢多筆公文的派工關聯
   */
  async getBatchDispatchLinks(documentIds: number[]): Promise<{
    success: boolean;
    links: Record<number, DocumentDispatchLink[]>;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENTS_BATCH_DISPATCH_LINKS,
      documentIds
    );
  },
};

// ============================================================================
// 公文-工程直接關聯 API (不經過派工單)
// ============================================================================

/**
 * 公文-工程直接關聯 API 服務
 * 用於將公文直接關聯到工程，不經過派工單
 */
export const documentProjectLinksApi = {
  /**
   * 查詢公文關聯的工程
   */
  async getProjectLinks(documentId: number): Promise<{
    success: boolean;
    document_id: number;
    projects: DocumentProjectLink[];
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_PROJECT_LINKS(documentId),
      {}
    );
  },

  /**
   * 將公文關聯到工程
   */
  async linkProject(
    documentId: number,
    projectId: number,
    linkType: 'agency_incoming' | 'company_outgoing' = 'agency_incoming',
    notes?: string
  ): Promise<{ success: boolean; message: string; link_id: number }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_LINK_PROJECT(documentId),
      {},
      {
        params: {
          project_id: projectId,
          link_type: linkType,
          notes: notes,
        },
      }
    );
  },

  /**
   * 移除公文與工程的關聯
   */
  async unlinkProject(documentId: number, linkId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENT_UNLINK_PROJECT(documentId, linkId),
      {}
    );
  },

  /**
   * 批次查詢多筆公文的工程關聯
   */
  async getBatchProjectLinks(documentIds: number[]): Promise<{
    success: boolean;
    data: Record<number, DocumentProjectLink[]>;
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DOCUMENTS_BATCH_PROJECT_LINKS,
      documentIds
    );
  },
};

// ============================================================================
// 工程關聯 API (以工程為主體)
// ============================================================================

/**
 * 工程關聯 API 服務
 */
export const projectLinksApi = {
  /**
   * 查詢工程關聯的派工單
   */
  async getDispatchLinks(projectId: number): Promise<{
    success: boolean;
    project_id: number;
    dispatch_orders: ProjectDispatchLink[];
    total: number;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECT_DISPATCH_LINKS(projectId),
      {}
    );
  },

  /**
   * 將工程關聯到派工單
   */
  async linkDispatch(
    projectId: number,
    dispatchOrderId: number
  ): Promise<{ success: boolean; message: string; link_id: number }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECT_LINK_DISPATCH(projectId),
      {},
      {
        params: {
          dispatch_order_id: dispatchOrderId,
        },
      }
    );
  },

  /**
   * 移除工程與派工的關聯
   */
  async unlinkDispatch(projectId: number, linkId: number): Promise<{ success: boolean; message: string }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECT_UNLINK_DISPATCH(projectId, linkId),
      {}
    );
  },

  /**
   * 批次查詢多筆工程的派工關聯
   */
  async getBatchDispatchLinks(projectIds: number[]): Promise<{
    success: boolean;
    links: Record<number, ProjectDispatchLink[]>;
  }> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.PROJECTS_BATCH_DISPATCH_LINKS,
      projectIds
    );
  },
};

// ============================================================================
// 派工單附件 API
// ============================================================================

/**
 * 派工單附件 API 服務
 */
export const dispatchAttachmentsApi = {
  /**
   * 上傳派工單附件
   */
  async uploadFiles(
    dispatchOrderId: number,
    files: File[],
    onProgress?: (percent: number) => void
  ): Promise<DispatchAttachmentUploadResult> {
    return apiClient.uploadWithProgress<DispatchAttachmentUploadResult>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENTS_UPLOAD(dispatchOrderId),
      files,
      'files',
      onProgress
    );
  },

  /**
   * 取得派工單附件列表
   */
  async getAttachments(dispatchOrderId: number): Promise<DispatchAttachment[]> {
    const response = await apiClient.post<DispatchAttachmentListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENTS_LIST(dispatchOrderId),
      {}
    );
    return response.attachments || [];
  },

  /**
   * 下載附件
   */
  async downloadAttachment(attachmentId: number, filename: string): Promise<void> {
    await apiClient.downloadPost(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_DOWNLOAD(attachmentId),
      {},
      filename
    );
  },

  /**
   * 刪除附件
   */
  async deleteAttachment(attachmentId: number): Promise<DispatchAttachmentDeleteResult> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_DELETE(attachmentId),
      {}
    );
  },

  /**
   * 驗證附件完整性
   */
  async verifyAttachment(attachmentId: number): Promise<DispatchAttachmentVerifyResult> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_VERIFY(attachmentId),
      {}
    );
  },
};

// 重新匯出附件型別
export type {
  DispatchAttachment,
  DispatchAttachmentListResponse,
  DispatchAttachmentUploadResult,
  DispatchAttachmentDeleteResult,
  DispatchAttachmentVerifyResult,
};

/**
 * 桃園派工管理 API 統一入口
 */
export const taoyuanDispatchApi = {
  projects: taoyuanProjectsApi,
  dispatchOrders: dispatchOrdersApi,
  payments: contractPaymentsApi,
  masterControl: masterControlApi,
  statistics: statisticsApi,
  documentLinks: documentLinksApi,
  documentProjectLinks: documentProjectLinksApi,
  projectLinks: projectLinksApi,
  attachments: dispatchAttachmentsApi,
};

export default taoyuanDispatchApi;
