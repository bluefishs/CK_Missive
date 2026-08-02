/**
 * 請款管理 Handlers Hook
 *
 * 從 BillingsTab 提取的狀態、查詢、mutation 與 handler 邏輯。
 *
 * @version 1.0.0
 */

import { useState, useCallback } from 'react';
import { Form, App } from 'antd';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';

import type {
  ERPBilling,
  ERPBillingCreate,
  ERPBillingUpdate,
} from '../../types/erp';

import {
  useERPBillings,
  useCreateERPBilling,
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
  const [form] = Form.useForm();
  const [invoiceForm] = Form.useForm();
  const [paymentForm] = Form.useForm();

  // State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ERPBilling | null>(null);
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
  const createMutation = useCreateERPBilling();
  const updateMutation = useUpdateERPBilling(erpQuotationId);
  const deleteMutation = useDeleteERPBilling(erpQuotationId);
  const createInvoiceMutation = useCreateInvoiceFromBilling();

  // Handlers
  const handleAdd = useCallback(() => {
    setEditingRecord(null);
    form.resetFields();
    setModalOpen(true);
  }, [form]);

  const handleEdit = useCallback((record: ERPBilling) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      billing_date: record.billing_date ? dayjs(record.billing_date) : null,
      billing_amount: record.billing_amount ? Number(record.billing_amount) : null,
    });
    setModalOpen(true);
  }, [form]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('請款紀錄已刪除');
    } catch {
      message.error('刪除失敗');
    }
  }, [deleteMutation, message]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        billing_date: values.billing_date?.format('YYYY-MM-DD'),
        billing_amount: String(values.billing_amount),
      };

      if (editingRecord) {
        const updateData: ERPBillingUpdate = { ...payload };
        await updateMutation.mutateAsync({ id: editingRecord.id, data: updateData });
        message.success('請款紀錄已更新');
      } else {
        const createData: ERPBillingCreate = {
          ...payload,
          erp_quotation_id: erpQuotationId,
        };
        await createMutation.mutateAsync(createData);
        message.success('請款紀錄已新增');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingRecord(null);
    } catch {
      // form validation failed or API error
    }
  }, [form, editingRecord, erpQuotationId, createMutation, updateMutation, message]);

  const handleCancel = useCallback(() => {
    setModalOpen(false);
    form.resetFields();
    setEditingRecord(null);
  }, [form]);

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
    // forms
    form,
    invoiceForm,
    paymentForm,
    // state
    modalOpen,
    setModalOpen,
    editingRecord,
    invoiceModalOpen,
    invoiceBillingId,
    paymentModalOpen,
    paymentBillingId,
    // data
    billings,
    billingsWithDetails,
    isLoading,
    // mutations loading
    createPending: createMutation.isPending,
    updatePending: updateMutation.isPending,
    createInvoicePending: createInvoiceMutation.isPending,
    // handlers
    handleAdd,
    handleEdit,
    handleDelete,
    handleSubmit,
    handleCancel,
    handleOpenInvoiceModal,
    handleCancelInvoiceModal,
    handleConfirmPayment,
    handleCancelPaymentModal,
    handlePaymentSubmit,
    handleCreateInvoice,
  };
}
