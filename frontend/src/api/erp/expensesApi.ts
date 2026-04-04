/**
 * 費用報銷 API 服務
 * 對應後端 api/endpoints/erp/expenses.py
 */
import { apiClient } from '../client';
import type { SuccessResponse } from '../types';
import { ERP_ENDPOINTS } from '../endpoints';
import type {
  ExpenseInvoice,
  ExpenseInvoiceCreate,
  ExpenseInvoiceUpdate,
  ExpenseInvoiceQuery,
  ExpenseInvoiceRejectRequest,
  ExpenseInvoiceQRScanRequest,
  ExpenseInvoiceOCRResult,
  ExpenseListResponse,
} from '../../types/erp';

export const expensesApi = {
  async list(params?: ExpenseInvoiceQuery): Promise<ExpenseListResponse> {
    return apiClient.post<ExpenseListResponse>(ERP_ENDPOINTS.EXPENSES_LIST, params || {});
  },

  async create(data: ExpenseInvoiceCreate): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.post<SuccessResponse<ExpenseInvoice>>(ERP_ENDPOINTS.EXPENSES_CREATE, data);
  },

  async detail(id: number): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.post<SuccessResponse<ExpenseInvoice>>(ERP_ENDPOINTS.EXPENSES_DETAIL, { id });
  },

  async update(id: number, data: ExpenseInvoiceUpdate): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.post<SuccessResponse<ExpenseInvoice>>(ERP_ENDPOINTS.EXPENSES_UPDATE, { id, data });
  },

  async approve(id: number): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.post<SuccessResponse<ExpenseInvoice>>(ERP_ENDPOINTS.EXPENSES_APPROVE, { id });
  },

  async reject(data: ExpenseInvoiceRejectRequest): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.post<SuccessResponse<ExpenseInvoice>>(ERP_ENDPOINTS.EXPENSES_REJECT, data);
  },

  async qrScan(data: ExpenseInvoiceQRScanRequest): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.post<SuccessResponse<ExpenseInvoice>>(ERP_ENDPOINTS.EXPENSES_QR_SCAN, data);
  },

  async ocrParse(file: File): Promise<SuccessResponse<ExpenseInvoiceOCRResult>> {
    return apiClient.upload<SuccessResponse<ExpenseInvoiceOCRResult>>(
      ERP_ENDPOINTS.EXPENSES_OCR_PARSE,
      file,
      'file',
    );
  },

  async uploadReceipt(invoiceId: number, file: File): Promise<SuccessResponse<ExpenseInvoice>> {
    return apiClient.upload<SuccessResponse<ExpenseInvoice>>(
      ERP_ENDPOINTS.EXPENSES_UPLOAD_RECEIPT,
      file,
      'file',
      { invoice_id: String(invoiceId) },
    );
  },

  /** 取得收據影像 URL (POST-only 安全策略，回傳 Blob) */
  async receiptImage(id: number): Promise<Blob> {
    return apiClient.post<Blob>(ERP_ENDPOINTS.EXPENSES_RECEIPT_IMAGE, { id }, { responseType: 'blob' });
  },

  /** 智慧發票辨識 (QR+OCR 一站式) */
  async smartScan(file: File, options?: { case_code?: string; category?: string; auto_create?: boolean }): Promise<SuccessResponse<SmartScanResult>> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.case_code) formData.append('case_code', options.case_code);
    if (options?.category) formData.append('category', options.category);
    formData.append('auto_create', String(options?.auto_create ?? true));
    return apiClient.postForm<SuccessResponse<SmartScanResult>>(ERP_ENDPOINTS.EXPENSES_SMART_SCAN, formData);
  },
};

/** 智慧辨識結果型別 */
export interface SmartScanResult {
  success: boolean;
  method: string;
  inv_num?: string;
  date?: string;
  random_code?: string;
  sales_amount?: number;
  total_amount?: number;
  amount?: number;
  tax_amount?: number;
  buyer_ban?: string;
  seller_ban?: string;
  items?: Array<{ name: string; qty: number; unit_price: number; amount: number }>;
  confidence: number;
  warnings: string[];
  receipt_path?: string;
  created?: boolean;
  invoice_id?: number;
  message?: string;
}
