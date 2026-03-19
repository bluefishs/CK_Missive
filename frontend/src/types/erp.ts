/**
 * ERP 財務管理型別定義
 * 對應後端 app/schemas/erp/
 */

// Re-export from api.ts SSOT
export type { ERPQuotation, ERPQuotationCreate, ERPQuotationUpdate, ERPProfitSummary, ERPProfitTrendItem, ERPQuotationStatus, ERPVendorPayable } from './api';
export { ERP_QUOTATION_STATUS_LABELS, ERP_QUOTATION_STATUS_COLORS } from './api';

/** ERP 報價列表查詢參數 */
export interface ERPQuotationListParams {
  page?: number;
  page_size?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  year?: number;
  status?: string;
  case_code?: string;
  search?: string;
  [key: string]: unknown;
}

/** ERP 發票 */
export interface ERPInvoice {
  id: number;
  erp_quotation_id: number;
  invoice_number: string;
  invoice_date: string;
  amount: number;
  tax_amount: number;
  invoice_type: string;
  description?: string;
  status: string;
  voided_at?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ERPInvoiceCreate {
  erp_quotation_id: number;
  invoice_number: string;
  invoice_date: string;
  amount: number;
  tax_amount?: number;
  invoice_type?: string;
  description?: string;
  notes?: string;
}

export type ERPInvoiceUpdate = Partial<Omit<ERPInvoiceCreate, 'erp_quotation_id'>> & {
  status?: string;
};

/** ERP 請款 */
export interface ERPBilling {
  id: number;
  erp_quotation_id: number;
  billing_period?: string;
  billing_date: string;
  billing_amount: number;
  invoice_id?: number;
  payment_status: string;
  payment_date?: string;
  payment_amount?: number;
  notes?: string;
  invoice_number?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ERPBillingCreate {
  erp_quotation_id: number;
  billing_period?: string;
  billing_date: string;
  billing_amount: number;
  invoice_id?: number;
  payment_status?: string;
  notes?: string;
}

export type ERPBillingUpdate = Partial<Omit<ERPBillingCreate, 'erp_quotation_id'>> & {
  payment_date?: string;
  payment_amount?: number;
};

/** ERP 廠商應付 (full detail interface) */
export interface ERPVendorPayableDetail {
  id: number;
  erp_quotation_id: number;
  vendor_name: string;
  vendor_code?: string;
  payable_amount: number;
  description?: string;
  due_date?: string;
  paid_date?: string;
  paid_amount?: number;
  payment_status: string;
  invoice_number?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ERPVendorPayableCreate {
  erp_quotation_id: number;
  vendor_name: string;
  vendor_code?: string;
  payable_amount: number;
  description?: string;
  due_date?: string;
  invoice_number?: string;
  notes?: string;
}

export type ERPVendorPayableUpdate = Partial<Omit<ERPVendorPayableCreate, 'erp_quotation_id'>> & {
  paid_date?: string;
  paid_amount?: number;
  payment_status?: string;
};

// ============================================================================
// Extended types and constants for sub-module consumers
// ============================================================================

export type ERPInvoiceType = 'sales' | 'purchase';
export type ERPInvoiceStatus = 'issued' | 'voided' | 'cancelled';
export type ERPBillingStatus = 'pending' | 'partial' | 'paid' | 'overdue';
export type ERPPayableStatus = 'unpaid' | 'partial' | 'paid';

export const ERP_INVOICE_TYPE_LABELS: Record<ERPInvoiceType, string> = {
  sales: '銷項',
  purchase: '進項',
};

export const ERP_BILLING_STATUS_LABELS: Record<ERPBillingStatus, string> = {
  pending: '待收款',
  partial: '部分收款',
  paid: '已收款',
  overdue: '逾期',
};

export const ERP_PAYABLE_STATUS_LABELS: Record<ERPPayableStatus, string> = {
  unpaid: '未付',
  partial: '部分付款',
  paid: '已付清',
};

export const ERP_CATEGORY_CODES: Record<string, string> = {
  '01': '報價單',
  '02': '變更單',
  '03': '追加減',
  '99': '其他',
};
