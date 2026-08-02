/**
 * 請款管理 Handlers Hook
 *
 * 從 BillingsTab 提取的狀態、查詢、mutation 與 handler 邏輯。
 *
 * 2026-08-02：請款「新增/編輯」已移出至獨立頁 `ERPBillingFormPage`，
 * 本 hook 隨之移除 billing form／modalOpen／editingRecord／handleAdd／handleEdit／
 * handleSubmit／handleCancel／createMutation —— 唯一 caller（BillingsTab）已不再使用它們，
 * 留著會變成「看起來還能用、其實沒有接線」的死碼。
 * 現存職責：列表查詢 + 刪除 + 兩個快速動作（開立發票／確認收款）。
 *
 * @version 2.0.0
 */

import { useState, useCallback } from 'react';
import { Form, App } from 'antd';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';

import {
  useERPBillings,
  useUpdateERPBilling,
  useDeleteERPBilling,
  useCreateInvoiceFromBilling,
} from '../../hooks/business/useERPQuotations';

// 期別整合型別
export interface BillingWithDetails {
  id: number;
  billing_period?: string;
  billing_date?: string;
  billing_amount: number;
  payment_status: string;
  invoices: Array<{ id: number; invoice_number: string; invoice_date?: string; amount: number; status: string }>;
  vendor_payables: Array<{ id: number; vendor_name: string; payable_amount: number; payment_status: string; description?: string }>;
}

export function useBillingHandlers(erpQuotationId: number) {
  const { message } = App.useApp();

  // Forms
  const [invoiceForm] = Form.useForm();
  const [paymentForm] = Form.useForm();

  // State
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false);
  const [invoiceBillingId, setInvoiceBillingId] = useState<number | null>(null);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentBillingId, setPaymentBillingId] = useState<number | null>(null);

  // Data queries
  const { data: billings, isLoading } = useERPBillings(erpQuotationId);

  const { data: billingsWithDetails } = useQuery({
    queryKey: ['erp-billings-details', erpQuotationId],
    queryFn: async () => {
      const { apiClient } = await import('../../api/client');
      const { ERP_ENDPOINTS } = await import('../../api/endpoints');
      const resp = await apiClient.post<{ success: boolean; data: BillingWithDetails[] }>(
        ERP_ENDPOINTS.BILLINGS_LIST_DETAILS,
        { erp_quotation_id: erpQuotationId },
      );
      return resp.data;
    },
    staleTime: 60_000,
  });

  // Mutations
  const updateMutation = useUpdateERPBilling(erpQuotationId);
  const deleteMutation = useDeleteERPBilling(erpQuotationId);
  const createInvoiceMutation = useCreateInvoiceFromBilling();

  // Handlers
  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('請款紀錄已刪除');
    } catch {
      message.error('刪除失敗');
    }
  }, [deleteMutation, message]);

  const handleOpenInvoiceModal = useCallback((billingId: number) => {
    setInvoiceBillingId(billingId);
    invoiceForm.resetFields();
    setInvoiceModalOpen(true);
  }, [invoiceForm]);

  const handleCancelInvoiceModal = useCallback(() => {
    setInvoiceModalOpen(false);
    invoiceForm.resetFields();
    setInvoiceBillingId(null);
  }, [invoiceForm]);

  const handleConfirmPayment = useCallback((billingId: number, billingAmount: number) => {
    setPaymentBillingId(billingId);
    paymentForm.setFieldsValue({
      payment_amount: billingAmount,
      payment_date: dayjs(),
      payment_status: 'paid',
    });
    setPaymentModalOpen(true);
  }, [paymentForm]);

  const handleCancelPaymentModal = useCallback(() => {
    setPaymentModalOpen(false);
    paymentForm.resetFields();
    setPaymentBillingId(null);
  }, [paymentForm]);

  const handlePaymentSubmit = useCallback(async () => {
    try {
      const values = await paymentForm.validateFields();
      if (!paymentBillingId) return;
      await updateMutation.mutateAsync({
        id: paymentBillingId,
        data: {
          payment_status: values.payment_status,
          payment_date: values.payment_date?.format('YYYY-MM-DD'),
          payment_amount: values.payment_amount,
        },
      });
      message.success('收款確認成功，已自動入帳');
      setPaymentModalOpen(false);
      paymentForm.resetFields();
      setPaymentBillingId(null);
    } catch {
      // form validation failed or API error
    }
  }, [paymentForm, paymentBillingId, updateMutation, message]);

  const handleCreateInvoice = useCallback(async () => {
    try {
      const values = await invoiceForm.validateFields();
      if (!invoiceBillingId) return;
      await createInvoiceMutation.mutateAsync({
        billing_id: invoiceBillingId,
        invoice_number: values.invoice_number,
        invoice_date: values.invoice_date?.format('YYYY-MM-DD'),
        notes: values.notes,
      });
      message.success('發票開立成功');
      setInvoiceModalOpen(false);
      invoiceForm.resetFields();
      setInvoiceBillingId(null);
    } catch {
      // form validation failed or API error
    }
  }, [invoiceForm, invoiceBillingId, createInvoiceMutation, message]);

  return {
    // forms（billing 主表單已移至 ERPBillingFormPage）
    invoiceForm,
    paymentForm,
    // state
    invoiceModalOpen,
    invoiceBillingId,
    paymentModalOpen,
    paymentBillingId,
    // data
    billings,
    billingsWithDetails,
    isLoading,
    // mutations loading
    updatePending: updateMutation.isPending,
    createInvoicePending: createInvoiceMutation.isPending,
    // handlers
    handleDelete,
    handleOpenInvoiceModal,
    handleCancelInvoiceModal,
    handleConfirmPayment,
    handleCancelPaymentModal,
    handlePaymentSubmit,
    handleCreateInvoice,
  };
}
