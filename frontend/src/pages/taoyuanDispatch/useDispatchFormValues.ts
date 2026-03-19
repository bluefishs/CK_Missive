/**
 * TaoyuanDispatchDetailPage — 表單值初始化與儲存邏輯
 *
 * 提取 form.setFieldsValue / handleSave / handleCancelEdit
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import { useEffect, useMemo, useCallback } from 'react';
import type { FormInstance } from 'antd';
import type { UseMutationResult } from '@tanstack/react-query';
import dayjs from 'dayjs';
import type {
  DispatchOrder,
  DispatchOrderUpdate,
  ContractPayment,
} from '../../types/taoyuan';
import type {
  DispatchDocumentLink,
  ContractPaymentCreate,
} from '../../types/api';
import {
  parseWorkTypeCodes,
  validatePaymentConsistency,
} from './tabs/paymentUtils';

interface UseDispatchFormValuesParams {
  id: string | undefined;
  dispatch: DispatchOrder | undefined;
  paymentData: ContractPayment | null | undefined;
  form: FormInstance;
  message: { error: (msg: string) => void; warning: (msg: string) => void };
  updateMutation: UseMutationResult<DispatchOrder, Error, DispatchOrderUpdate, unknown>;
  paymentMutation: { mutate: (data: ContractPaymentCreate) => void };
  uploadAttachmentsMutation: { mutate: () => void };
  fileList: unknown[];
  setIsEditing: (v: boolean) => void;
}

export function useDispatchFormValues({
  id,
  dispatch,
  paymentData,
  form,
  message,
  updateMutation,
  paymentMutation,
  uploadAttachmentsMutation,
  fileList,
  setIsEditing,
}: UseDispatchFormValuesParams) {
  const dispatchDate = useMemo(() => {
    const agencyDocs = (dispatch?.linked_documents || [])
      .filter(
        (link: DispatchDocumentLink) =>
          link.link_type === 'agency_incoming' && link.doc_date
      )
      .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
        const dateA = a.doc_date || '9999-12-31';
        const dateB = b.doc_date || '9999-12-31';
        return dateA.localeCompare(dateB);
      });
    return agencyDocs[0]?.doc_date || null;
  }, [dispatch?.linked_documents]);

  const buildFormValues = useCallback(() => {
    if (!dispatch) return;

    const workTypeArray = dispatch.work_type
      ? dispatch.work_type
          .split(',')
          .map((t: string) => t.trim())
          .filter(Boolean)
      : [];

    const activeCodes = parseWorkTypeCodes(workTypeArray);

    const toDateValue = (code: string): ReturnType<typeof dayjs> | undefined => {
      const dateKey = `work_${code}_date` as keyof ContractPayment;
      const val = paymentData?.[dateKey] as string | undefined;
      if (val) return dayjs(val);
      if (activeCodes.includes(code) && dispatchDate) return dayjs(dispatchDate);
      return undefined;
    };

    return {
      dispatch_no: dispatch.dispatch_no,
      project_name: dispatch.project_name,
      work_type: workTypeArray,
      sub_case_name: dispatch.sub_case_name,
      deadline: dispatch.deadline,
      case_handler: dispatch.case_handler,
      survey_unit: dispatch.survey_unit,
      contact_note: dispatch.contact_note,
      cloud_folder: dispatch.cloud_folder,
      project_folder: dispatch.project_folder,
      batch_no: dispatch.batch_no,
      work_01_date: toDateValue('01'),
      work_01_amount: paymentData?.work_01_amount,
      work_02_date: toDateValue('02'),
      work_02_amount: paymentData?.work_02_amount,
      work_03_date: toDateValue('03'),
      work_03_amount: paymentData?.work_03_amount,
      work_04_date: toDateValue('04'),
      work_04_amount: paymentData?.work_04_amount,
      work_05_date: toDateValue('05'),
      work_05_amount: paymentData?.work_05_amount,
      work_06_date: toDateValue('06'),
      work_06_amount: paymentData?.work_06_amount,
      work_07_date: toDateValue('07'),
      work_07_amount: paymentData?.work_07_amount,
    };
  }, [dispatch, paymentData, dispatchDate]);

  // 初始化表單值
  useEffect(() => {
    const values = buildFormValues();
    if (values) {
      form.setFieldsValue(values);
    }
  }, [buildFormValues, form]);

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false);
    const values = buildFormValues();
    if (values) {
      form.setFieldsValue(values);
    }
  }, [setIsEditing, buildFormValues, form]);

  const handleSave = useCallback(async () => {
    try {
      const validated = await form.validateFields();
      const allValues = form.getFieldsValue(true);
      const values = { ...allValues, ...validated };

      const workTypeString = Array.isArray(values.work_type)
        ? values.work_type.join(', ')
        : values.work_type || '';

      const workTypeCodes = parseWorkTypeCodes(values.work_type);

      /* eslint-disable @typescript-eslint/no-unused-vars */
      const {
        work_01_amount,
        work_02_amount,
        work_03_amount,
        work_04_amount,
        work_05_amount,
        work_06_amount,
        work_07_amount,
        current_amount,
        cumulative_amount,
        remaining_amount,
        ...dispatchValues
      } = values;
      /* eslint-enable @typescript-eslint/no-unused-vars */

      const originalAmounts: Record<string, number | undefined> = {
        work_01_amount,
        work_02_amount,
        work_03_amount,
        work_04_amount,
        work_05_amount,
        work_06_amount,
        work_07_amount,
      };

      const inconsistencies = validatePaymentConsistency(workTypeCodes, originalAmounts);

      const syncedAmounts: Record<string, number | null | undefined> = {};
      for (let i = 1; i <= 7; i++) {
        const code = i.toString().padStart(2, '0');
        const field = `work_${code}_amount`;
        if (workTypeCodes.includes(code)) {
          const val = originalAmounts[field];
          syncedAmounts[field] = (val && val > 0) ? val : null;
        } else {
          syncedAmounts[field] = null;
        }
      }

      if (inconsistencies.length > 0) {
        const clearedInfo = inconsistencies
          .map(item => `${item.label}: $${item.amount.toLocaleString()}`)
          .join('、');
        message.warning(`以下金額因作業類別變更已自動清除：${clearedInfo}`);
      }

      const calculatedCurrentAmount =
        (syncedAmounts.work_01_amount || 0) +
        (syncedAmounts.work_02_amount || 0) +
        (syncedAmounts.work_03_amount || 0) +
        (syncedAmounts.work_04_amount || 0) +
        (syncedAmounts.work_05_amount || 0) +
        (syncedAmounts.work_06_amount || 0) +
        (syncedAmounts.work_07_amount || 0);

      const formatDateField = (dateValue: unknown): string | null => {
        if (!dateValue) return null;
        if (typeof dateValue === 'object' && dateValue !== null && 'format' in dateValue) {
          return (dateValue as { format: (fmt: string) => string }).format('YYYY-MM-DD');
        }
        if (typeof dateValue === 'string') return dateValue;
        return null;
      };

      const sanitizedDispatch = Object.fromEntries(
        Object.entries({
          ...dispatchValues,
          work_type: workTypeString,
          batch_label: dispatchValues.batch_no
            ? `第${dispatchValues.batch_no}批結案`
            : null,
        }).map(([k, v]) => [k, v === undefined ? null : v]),
      );
      try {
        await updateMutation.mutateAsync(sanitizedDispatch as DispatchOrderUpdate);
      } catch {
        return;
      }

      if (calculatedCurrentAmount > 0 || paymentData?.id) {
        const paymentValues: ContractPaymentCreate = {
          dispatch_order_id: parseInt(id || '0', 10),
          work_01_date: workTypeCodes.includes('01') ? formatDateField(values.work_01_date) : null,
          work_02_date: workTypeCodes.includes('02') ? formatDateField(values.work_02_date) : null,
          work_03_date: workTypeCodes.includes('03') ? formatDateField(values.work_03_date) : null,
          work_04_date: workTypeCodes.includes('04') ? formatDateField(values.work_04_date) : null,
          work_05_date: workTypeCodes.includes('05') ? formatDateField(values.work_05_date) : null,
          work_06_date: workTypeCodes.includes('06') ? formatDateField(values.work_06_date) : null,
          work_07_date: workTypeCodes.includes('07') ? formatDateField(values.work_07_date) : null,
          work_01_amount: syncedAmounts.work_01_amount ?? null,
          work_02_amount: syncedAmounts.work_02_amount ?? null,
          work_03_amount: syncedAmounts.work_03_amount ?? null,
          work_04_amount: syncedAmounts.work_04_amount ?? null,
          work_05_amount: syncedAmounts.work_05_amount ?? null,
          work_06_amount: syncedAmounts.work_06_amount ?? null,
          work_07_amount: syncedAmounts.work_07_amount ?? null,
          current_amount: calculatedCurrentAmount > 0 ? calculatedCurrentAmount : null,
        };
        paymentMutation.mutate(paymentValues);
      }

      if (fileList.length > 0) {
        uploadAttachmentsMutation.mutate();
      }
    } catch {
      message.error('請檢查表單欄位');
    }
  }, [form, id, updateMutation, paymentMutation, uploadAttachmentsMutation, fileList, paymentData, message]);

  return {
    dispatchDate,
    handleSave,
    handleCancelEdit,
  };
}
