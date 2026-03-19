/**
 * Dispatch Info - Read-Only View
 *
 * Extracted from DispatchInfoTab.tsx to reduce main file size.
 * Displays dispatch order information in read-only mode.
 */

import React from 'react';
import {
  Descriptions,
  Divider,
  Typography,
  Tag,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
import dayjs from 'dayjs';

import type {
  DispatchOrder,
  DispatchDocumentLink,
  LinkType,
  ContractPayment,
} from '../../../types/api';

const { Text } = Typography;

// =============================================================================
// Utilities (shared with DispatchInfoTab)
// =============================================================================

const detectLinkType = (docNumber?: string): LinkType => {
  if (!docNumber) return 'agency_incoming';
  if (docNumber.startsWith('乾坤')) return 'company_outgoing';
  return 'agency_incoming';
};

const formatCurrency = (val?: number | null): string => {
  if (val === undefined || val === null || val === 0) return '-';
  return `$${Math.round(val).toLocaleString()}`;
};

/** 作業類別與金額欄位的對應表 */
const WORK_TYPE_AMOUNT_MAPPING: Record<
  string,
  { dateField: string; amountField: string; label: string }
> = {
  '01.地上物查估作業': { dateField: 'work_01_date', amountField: 'work_01_amount', label: '01.地上物查估' },
  '02.土地協議市價查估作業': { dateField: 'work_02_date', amountField: 'work_02_amount', label: '02.土地協議市價查估' },
  '03.土地徵收市價查估作業': { dateField: 'work_03_date', amountField: 'work_03_amount', label: '03.土地徵收市價查估' },
  '04.相關計畫書製作': { dateField: 'work_04_date', amountField: 'work_04_amount', label: '04.相關計畫書製作' },
  '05.測量作業': { dateField: 'work_05_date', amountField: 'work_05_amount', label: '05.測量作業' },
  '06.樁位測釘作業': { dateField: 'work_06_date', amountField: 'work_06_amount', label: '06.樁位測釘作業' },
  '07.辦理教育訓練': { dateField: 'work_07_date', amountField: 'work_07_amount', label: '07.辦理教育訓練' },
};

// =============================================================================
// ReadOnlyField component
// =============================================================================

const ReadOnlyField: React.FC<{ value?: string; placeholder?: string }> = ({ value, placeholder }) => (
  <Text style={{
    display: 'block',
    padding: '4px 11px',
    minHeight: 32,
    lineHeight: '22px',
    color: value ? 'rgba(0, 0, 0, 0.88)' : 'rgba(0, 0, 0, 0.25)',
    background: '#fafafa',
    borderRadius: 6,
    border: '1px solid #d9d9d9',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  }}>
    {value || placeholder || '-'}
  </Text>
);

// =============================================================================
// PaymentReadOnlySection
// =============================================================================

interface PaymentReadOnlySectionProps {
  paymentData?: ContractPayment | null;
  watchedWorkTypes: string[];
}

const PaymentReadOnlySection: React.FC<PaymentReadOnlySectionProps> = ({
  paymentData,
  watchedWorkTypes,
}) => {
  const validWorkTypes = watchedWorkTypes.filter(
    (wt) => WORK_TYPE_AMOUNT_MAPPING[wt]
  );

  const currentAmount =
    (paymentData?.work_01_amount ?? 0) +
    (paymentData?.work_02_amount ?? 0) +
    (paymentData?.work_03_amount ?? 0) +
    (paymentData?.work_04_amount ?? 0) +
    (paymentData?.work_05_amount ?? 0) +
    (paymentData?.work_06_amount ?? 0) +
    (paymentData?.work_07_amount ?? 0);

  const cumulativeAmount = paymentData?.cumulative_amount ?? 0;
  const remainingAmount = paymentData?.remaining_amount ?? 0;

  const workTypeItems = validWorkTypes
    .map((wt) => {
      const mapping = WORK_TYPE_AMOUNT_MAPPING[wt];
      if (!mapping) return null;
      const amount = paymentData?.[
        mapping.amountField as keyof typeof paymentData
      ] as number | undefined;
      return {
        key: wt,
        label: `${mapping.label} 金額`,
        value: formatCurrency(amount),
      };
    })
    .filter(Boolean);

  return (
    <Descriptions size="small" column={3} bordered items={[
      ...workTypeItems
        .filter(Boolean)
        .map((item) => ({
          key: item!.key,
          label: item!.label,
          children: item!.value,
        })),
      { key: '本次派工總金額', label: '本次派工總金額', children: (
        <Text strong style={{ color: '#1890ff' }}>{formatCurrency(currentAmount)}</Text>
      ) },
      { key: '累進派工金額', label: '累進派工金額（統計）', children: (
        <Text>{formatCurrency(cumulativeAmount)}</Text>
      ) },
      { key: '剩餘金額', label: '剩餘金額（統計）', children: (
        <Text type={remainingAmount > 0 && remainingAmount < 1000000 ? 'warning' : undefined}>
          {formatCurrency(remainingAmount)}
        </Text>
      ) },
    ]} />
  );
};

// =============================================================================
// Main read-only component
// =============================================================================

interface DispatchInfoReadOnlyProps {
  dispatch: DispatchOrder;
  paymentData?: ContractPayment | null;
  watchedWorkTypes: string[];
}

export const DispatchInfoReadOnly: React.FC<DispatchInfoReadOnlyProps> = ({
  dispatch,
  paymentData,
  watchedWorkTypes,
}) => (
  <div>
    {/* Row 1: dispatch number + project name */}
    <div style={{ marginBottom: 16 }}>
      <ResponsiveFormRow>
        <div>
          <div style={{ marginBottom: 8 }}>
            <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>
              <span style={{ color: '#ff4d4f' }}>* </span>派工單號
            </Text>
          </div>
          <ReadOnlyField value={dispatch.dispatch_no} />
        </div>
        <div>
          <div style={{ marginBottom: 8 }}>
            <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>工程名稱/派工事項</Text>
          </div>
          <ReadOnlyField value={dispatch.project_name} />
        </div>
      </ResponsiveFormRow>
    </div>

    {/* Row 2: work type + sub case + deadline */}
    <div style={{ marginBottom: 16 }}>
      <ResponsiveFormRow>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>作業類別</Text></div>
          <ReadOnlyField value={dispatch.work_type} />
        </div>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>分案名稱/派工備註</Text></div>
          <ReadOnlyField value={dispatch.sub_case_name} />
        </div>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>履約期限</Text></div>
          <ReadOnlyField value={dispatch.deadline} />
        </div>
      </ResponsiveFormRow>
    </div>

    {/* Row 3: handler + survey unit + contact note */}
    <div style={{ marginBottom: 16 }}>
      <ResponsiveFormRow>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>案件承辦</Text></div>
          <ReadOnlyField value={dispatch.case_handler} />
        </div>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>查估單位</Text></div>
          <ReadOnlyField value={dispatch.survey_unit} />
        </div>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>聯絡備註</Text></div>
          <ReadOnlyField value={dispatch.contact_note} />
        </div>
      </ResponsiveFormRow>
    </div>

    {/* Row 4: cloud folder + project folder */}
    <div style={{ marginBottom: 16 }}>
      <ResponsiveFormRow>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>雲端資料夾</Text></div>
          {dispatch.cloud_folder ? (
            <a href={dispatch.cloud_folder} target="_blank" rel="noopener noreferrer">
              <ReadOnlyField value={dispatch.cloud_folder} />
            </a>
          ) : (
            <ReadOnlyField value={undefined} />
          )}
        </div>
        <div>
          <div style={{ marginBottom: 8 }}><Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>專案資料夾</Text></div>
          <ReadOnlyField value={dispatch.project_folder} />
        </div>
      </ResponsiveFormRow>
    </div>

    {/* Payment info */}
    <Divider titlePlacement="left">契金資訊</Divider>
    <PaymentReadOnlySection paymentData={paymentData} watchedWorkTypes={watchedWorkTypes} />

    {/* System info */}
    <Divider />
    <Descriptions size="small" column={3} items={[
      { key: '機關函文號', label: '機關函文號', children: (() => {
        const agencyDocs = (dispatch.linked_documents || [])
          .filter((d: DispatchDocumentLink) => detectLinkType(d.doc_number) === 'agency_incoming')
          .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) =>
            (a.doc_date || '9999-12-31').localeCompare(b.doc_date || '9999-12-31')
          );
        return agencyDocs.length > 0 ? agencyDocs[0]?.doc_number || '-' : '-';
      })() },
      { key: '乾坤函文號', label: '乾坤函文號', children: (() => {
        const companyDocs = (dispatch.linked_documents || [])
          .filter((d: DispatchDocumentLink) => detectLinkType(d.doc_number) === 'company_outgoing')
          .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) =>
            (a.doc_date || '9999-12-31').localeCompare(b.doc_date || '9999-12-31')
          );
        return companyDocs.length > 0 ? companyDocs[0]?.doc_number || '-' : '-';
      })() },
      { key: '建立時間', label: '建立時間', children: dispatch.created_at
        ? dayjs(dispatch.created_at).format('YYYY-MM-DD HH:mm')
        : '-' },
    ]} />

    {/* Batch info */}
    <Divider titlePlacement="left">結案批次</Divider>
    <div>
      {dispatch.batch_no ? (
        <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
          第{dispatch.batch_no}批結案
        </Tag>
      ) : (
        <Text type="secondary">未設定</Text>
      )}
    </div>
  </div>
);
