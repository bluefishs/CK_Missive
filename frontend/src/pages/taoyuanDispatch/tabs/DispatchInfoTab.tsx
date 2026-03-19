/**
 * 派工資訊 Tab 元件
 *
 * 顯示派工單的基本資訊。
 * 唯讀模式使用 DispatchInfoReadOnly 子元件，
 * 編輯模式使用共用 DispatchFormFields 元件。
 *
 * @version 2.1.0 - 唯讀視圖拆分至 DispatchInfoReadOnly
 */

import React from 'react';
import {
  Form,
  Divider,
  InputNumber,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
import type { FormInstance } from 'antd';

import { DispatchFormFields } from '../../../components/taoyuan/DispatchFormFields';
import type {
  DispatchOrder,
  ContractPayment,
  TaoyuanProject,
} from '../../../types/api';
import { type ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import { type ProjectVendor } from '../../../api/projectVendorsApi';
import { DispatchInfoReadOnly } from './DispatchInfoReadOnly';

// =============================================================================
// Props
// =============================================================================

export interface DispatchInfoTabProps {
  dispatch?: DispatchOrder;
  form: FormInstance;
  isEditing: boolean;
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
  paymentData?: ContractPayment | null;
  watchedWorkTypes: string[];
  watchedWorkAmounts: {
    work_01_amount: number;
    work_02_amount: number;
    work_03_amount: number;
    work_04_amount: number;
    work_05_amount: number;
    work_06_amount: number;
    work_07_amount: number;
  };
  availableProjects?: TaoyuanProject[];
  onProjectSelect?: (projectId: number, projectName: string) => void;
  onCreateProject?: (projectName: string) => void;
}

// =============================================================================
// PaymentEditSummary (edit mode only)
// =============================================================================

interface PaymentEditSummaryProps {
  watchedWorkAmounts: DispatchInfoTabProps['watchedWorkAmounts'];
  paymentData?: ContractPayment | null;
}

const PaymentEditSummary: React.FC<PaymentEditSummaryProps> = ({
  watchedWorkAmounts,
  paymentData,
}) => {
  const editCurrentAmount =
    (watchedWorkAmounts.work_01_amount ?? 0) +
    (watchedWorkAmounts.work_02_amount ?? 0) +
    (watchedWorkAmounts.work_03_amount ?? 0) +
    (watchedWorkAmounts.work_04_amount ?? 0) +
    (watchedWorkAmounts.work_05_amount ?? 0) +
    (watchedWorkAmounts.work_06_amount ?? 0) +
    (watchedWorkAmounts.work_07_amount ?? 0);

  const cumulativeAmount = paymentData?.cumulative_amount ?? 0;
  const remainingAmount = paymentData?.remaining_amount ?? 0;

  return (
    <>
      <Divider dashed style={{ margin: '12px 0' }} />
      <ResponsiveFormRow>
        <Form.Item label="本次派工總金額（自動加總）">
          <InputNumber
            style={{ width: '100%' }} value={editCurrentAmount} disabled precision={0}
            formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          />
        </Form.Item>
        <Form.Item label="累進派工金額（統計）">
          <InputNumber
            style={{ width: '100%' }} value={cumulativeAmount} disabled precision={0}
            formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          />
        </Form.Item>
        <Form.Item label="剩餘金額（統計）">
          <InputNumber
            style={{ width: '100%' }} value={remainingAmount} disabled precision={0}
            formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          />
        </Form.Item>
      </ResponsiveFormRow>
    </>
  );
};

// =============================================================================
// Main component
// =============================================================================

export const DispatchInfoTab: React.FC<DispatchInfoTabProps> = ({
  dispatch, form, isEditing, agencyContacts, projectVendors,
  paymentData, watchedWorkTypes, watchedWorkAmounts,
  availableProjects = [], onProjectSelect, onCreateProject,
}) => {
  // Read-only mode
  if (!isEditing && dispatch) {
    return (
      <DispatchInfoReadOnly
        dispatch={dispatch}
        paymentData={paymentData}
        watchedWorkTypes={watchedWorkTypes}
      />
    );
  }

  // Edit mode
  return (
    <Form form={form} layout="vertical">
      <DispatchFormFields
        form={form} mode="edit"
        availableProjects={availableProjects}
        agencyContacts={agencyContacts}
        projectVendors={projectVendors}
        onProjectSelect={onProjectSelect}
        onCreateProject={onCreateProject}
        showPaymentFields={true}
        watchedWorkTypes={watchedWorkTypes}
        showDocLinkFields={false}
        showProjectLinkFields={false}
      />
      <PaymentEditSummary
        watchedWorkAmounts={watchedWorkAmounts}
        paymentData={paymentData}
      />
    </Form>
  );
};

export default DispatchInfoTab;
