import type { ERPQuotationLegacyImportResult, ERPSignedImportResult, ERPQuotationTemplateMeta } from '../../types/erp';
/**
 * ERP 報價/成本主檔 API 服務
 */

import { apiClient } from '../client';
import type { PaginatedResponse, SuccessResponse, DeleteResponse } from '../types';
import type {
  ERPQuotation,
  ERPQuotationCreate,
  ERPQuotationUpdate,
  ERPQuotationListParams,
  ERPProfitSummary,
  ERPProfitTrendItem,
} from '../../types/erp';
import { ERP_ENDPOINTS } from '../endpoints';

export const erpQuotationsApi = {
  /** 取得報價列表 */
  async list(params?: ERPQuotationListParams): Promise<PaginatedResponse<ERPQuotation>> {
    const queryParams: Record<string, unknown> = {
      page: params?.page ?? 1,
      limit: params?.limit ?? 20,
      sort_by: params?.sort_by ?? 'created_at',
      sort_order: params?.sort_order ?? 'desc',
    };
    // 2026-09-04 晚 owner「計畫類別／委託單位皆無法正常篩選」：這裡此前**逐一白名單**只放行
    // search／year／status／case_code，頁面送的 category／client_name／case_status／include_unawarded
    // 全部在這一層被丟掉——後端與頁面各自都驗過，就是沒驗到中間這一層（verified_wrong_layer 第四次）。
    // 改為全部透傳（去掉 undefined／空字串），新增參數不必再來這裡登記。
    for (const [k, v] of Object.entries(params ?? {})) {
      if (k in queryParams) continue;
      if (v === undefined || v === null || v === '') continue;
      queryParams[k] = v;
    }

    return await apiClient.postList<ERPQuotation>(ERP_ENDPOINTS.QUOTATIONS_LIST, queryParams);
  },

  /** 取得報價詳情 */
  async detail(id: number): Promise<ERPQuotation> {
    const response = await apiClient.post<SuccessResponse<ERPQuotation>>(
      ERP_ENDPOINTS.QUOTATIONS_DETAIL,
      { id }
    );
    return response.data!;
  },

  /** 建立報價 */
  async create(data: ERPQuotationCreate): Promise<ERPQuotation> {
    const response = await apiClient.post<SuccessResponse<ERPQuotation>>(
      ERP_ENDPOINTS.QUOTATIONS_CREATE,
      data
    );
    return response.data!;
  },

  /** 更新報價 */
  async update(id: number, data: ERPQuotationUpdate): Promise<ERPQuotation> {
    const response = await apiClient.post<SuccessResponse<ERPQuotation>>(
      ERP_ENDPOINTS.QUOTATIONS_UPDATE,
      { id, data }
    );
    return response.data!;
  },

  /** 刪除報價 */
  async delete(id: number): Promise<DeleteResponse> {
    return await apiClient.post<DeleteResponse>(ERP_ENDPOINTS.QUOTATIONS_DELETE, { id });
  },

  /** 取得損益摘要 */
  async profitSummary(params?: { year?: number; search?: string; category?: string; client_name?: string }): Promise<ERPProfitSummary> {
    const response = await apiClient.post<SuccessResponse<ERPProfitSummary>>(
      ERP_ENDPOINTS.PROFIT_SUMMARY,
      params ?? {}
    );
    return response.data!;
  },

  /** 委託單位篩選選項＝案件實際客戶（2026-09-04；主檔 client 型清單會漏掉 subcontractor 型的委託單位與異體字重複） */
  async clientOptions(params?: { year?: number; category?: string }): Promise<{ data: { name: string; count: number }[] }> {
    return apiClient.post<{ data: { name: string; count: number }[] }>(ERP_ENDPOINTS.QUOTATION_CLIENT_OPTIONS, params ?? {});
  },

  /** 取得損益趨勢 */
  async profitTrend(): Promise<ERPProfitTrendItem[]> {
    const response = await apiClient.post<SuccessResponse<ERPProfitTrendItem[]>>(
      ERP_ENDPOINTS.PROFIT_TREND,
      {}
    );
    return response.data!;
  },

  /** 匯出 CSV */
  async exportCsv(params?: { year?: number }): Promise<Blob> {
    return apiClient.postBlob(ERP_ENDPOINTS.EXPORT, params ?? {});
  },

  /** 匯出 Excel */
  async exportExcel(params?: { year?: number }): Promise<Blob> {
    return apiClient.postBlob(ERP_ENDPOINTS.EXPORT_EXCEL, params ?? {});
  },

  /** 下載匯入範本 */
  async downloadTemplate(): Promise<Blob> {
    return apiClient.postBlob(ERP_ENDPOINTS.IMPORT_TEMPLATE, {});
  },

  /** 匯入 Excel */
  // 2026-09-03：importExcel（舊 11 欄）移除——匯入統一走 importLegacy（總表格式，先預覽再確認）。

  /**
   * 匯入既有報價單彙整（一個入口做 upsert：有就更新、沒有就新增）。
   *
   * `dryRun` 預設 true —— 先回報「會新增幾筆、更新幾筆」不寫入。
   * 第一次匯入是 277 列業務資料，沒有預覽就寫進去，錯了要靠備份還原。
   */
  async importLegacy(file: File, dryRun = true): Promise<ERPQuotationLegacyImportResult> {
    const response = await apiClient.upload<SuccessResponse<ERPQuotationLegacyImportResult>>(
      `${ERP_ENDPOINTS.IMPORT_LEGACY}?dry_run=${dryRun}`, file, 'file',
    );
    return response.data!;
  },

  /**
   * 匯入客戶回簽報價單（多檔）。
   *
   * ⚠️ 用 FormData 手動組多檔 —— `apiClient.upload` 只收單檔。
   * 檔名就是對應關係：`回簽報價單_<舊案號>_<客戶>_<標的>_<項目>.pdf`
   */
  async importSigned(files: File[], dryRun = true): Promise<ERPSignedImportResult> {
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    const response = await apiClient.post<SuccessResponse<ERPSignedImportResult>>(
      `${ERP_ENDPOINTS.IMPORT_SIGNED}?dry_run=${dryRun}`, fd,
    );
    return response.data!;
  },

  /** 產生案號 */
  async generateCode(params: { year: number; category?: string }): Promise<string> {
    const response = await apiClient.post<SuccessResponse<{ case_code: string }>>(
      ERP_ENDPOINTS.GENERATE_CODE,
      { year: params.year, category: params.category ?? '01' }
    );
    return response.data!.case_code;
  },

  /**
   * 正式 XLS 範本的容量 —— 前端不得自行寫死（來源＝後端 ITEM_{FIRST,LAST}_ROW）。
   * 2026-08-29 手抄常數漂移事故的修法，見 QuotationTemplateCreatePage 檔頭。
   */
  async getTemplateMeta(): Promise<ERPQuotationTemplateMeta> {
    const response = await apiClient.post<SuccessResponse<ERPQuotationTemplateMeta>>(
      ERP_ENDPOINTS.QUOTATION_TEMPLATE_META, {},
    );
    return response.data!;
  },
};
