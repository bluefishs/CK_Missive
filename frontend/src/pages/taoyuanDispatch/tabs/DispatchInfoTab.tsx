/**
 * 派工資訊 Tab 元件
 *
 * 顯示派工單的基本資訊，包含：
 * - 派工單號、工程名稱（支援自動完成選擇工程）
 * - 作業類別、分案名稱、履約期限
 * - 案件承辦、查估單位、聯絡備註
 * - 雲端資料夾、專案資料夾
 * - 契金資訊
 * - 系統資訊（唯讀模式）
 *
 * 使用共用 DispatchFormFields 元件（編輯模式）
 *
 * @version 2.0.0 - 重構使用共用表單元件
 * @date 2026-01-29
 */

import React from 'react';
import {
  Form,
  Descriptions,
  Divider,
  Typography,
  InputNumber,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
import type { FormInstance } from 'antd';
import dayjs from 'dayjs';

import { DispatchFormFields } from '../../../components/taoyuan/DispatchFormFields';
import type {
  DispatchOrder,
  DispatchDocumentLink,
  LinkType,
  ContractPayment,
  TaoyuanProject,
} from '../../../types/api';
import { type ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import { type ProjectVendor } from '../../../api/projectVendorsApi';

const { Text } = Typography;

// =============================================================================
// 常數定義
// =============================================================================

/** 作業類別與金額欄位的對應表 */
const WORK_TYPE_AMOUNT_MAPPING: Record<
  string,
  { dateField: string; amountField: string; label: string }
> = {
  '01.地上物查估作業': {
    dateField: 'work_01_date',
    amountField: 'work_01_amount',
    label: '01.地上物查估',
  },
  '02.土地協議市價查估作業': {
    dateField: 'work_02_date',
    amountField: 'work_02_amount',
    label: '02.土地協議市價查估',
  },
  '03.土地徵收市價查估作業': {
    dateField: 'work_03_date',
    amountField: 'work_03_amount',
    label: '03.土地徵收市價查估',
  },
  '04.相關計畫書製作': {
    dateField: 'work_04_date',
    amountField: 'work_04_amount',
    label: '04.相關計畫書製作',
  },
  '05.測量作業': {
    dateField: 'work_05_date',
    amountField: 'work_05_amount',
    label: '05.測量作業',
  },
  '06.樁位測釘作業': {
    dateField: 'work_06_date',
    amountField: 'work_06_amount',
    label: '06.樁位測釘作業',
  },
  '07.辦理教育訓練': {
    dateField: 'work_07_date',
    amountField: 'work_07_amount',
    label: '07.辦理教育訓練',
  },
};

// =============================================================================
// 工具函數
// =============================================================================

/**
 * 根據公文字號自動判斷關聯類型
 */
const detectLinkType = (docNumber?: string): LinkType => {
  if (!docNumber) return 'agency_incoming';
  if (docNumber.startsWith('乾坤')) {
    return 'company_outgoing';
  }
  return 'agency_incoming';
};

/**
 * 格式化金額（整數，無小數）
 */
const formatCurrency = (val?: number | null): string => {
  if (val === undefined || val === null || val === 0) return '-';
  return `$${Math.round(val).toLocaleString()}`;
};

// =============================================================================
// Props 介面定義
// =============================================================================

export interface DispatchInfoTabProps {
  /** 派工單資料 */
  dispatch?: DispatchOrder;
  /** Ant Design Form 實例 */
  form: FormInstance;
  /** 是否處於編輯模式 */
  isEditing: boolean;
  /** 機關承辦清單 */
  agencyContacts: ProjectAgencyContact[];
  /** 協力廠商清單（查估單位） */
  projectVendors: ProjectVendor[];
  /** 契金資料 */
  paymentData?: ContractPayment | null;
  /** 監聽的作業類別 */
  watchedWorkTypes: string[];
  /** 各作業類別金額（用於編輯時即時計算） */
  watchedWorkAmounts: {
    work_01_amount: number;
    work_02_amount: number;
    work_03_amount: number;
    work_04_amount: number;
    work_05_amount: number;
    work_06_amount: number;
    work_07_amount: number;
  };
  /** 可選擇的工程列表（用於 project_name 自動完成） */
  availableProjects?: TaoyuanProject[];
  /** 選擇工程時的回調（傳入工程 ID 和名稱） */
  onProjectSelect?: (projectId: number, projectName: string) => void;
  /** 新增工程的回調 */
  onCreateProject?: (projectName: string) => void;
  /** 是否正在建立工程中 */
  creatingProject?: boolean;
}

// =============================================================================
// 子元件：契金資訊區塊（唯讀模式）
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

  // 計算本次派工金額
  const currentAmount =
    (paymentData?.work_01_amount || 0) +
    (paymentData?.work_02_amount || 0) +
    (paymentData?.work_03_amount || 0) +
    (paymentData?.work_04_amount || 0) +
    (paymentData?.work_05_amount || 0) +
    (paymentData?.work_06_amount || 0) +
    (paymentData?.work_07_amount || 0);

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
    <Descriptions size="small" column={3} bordered>
      {workTypeItems.map(
        (item) =>
          item && (
            <Descriptions.Item key={item.key} label={item.label}>
              {item.value}
            </Descriptions.Item>
          )
      )}
      <Descriptions.Item label="本次派工總金額">
        <Text strong style={{ color: '#1890ff' }}>
          {formatCurrency(currentAmount)}
        </Text>
      </Descriptions.Item>
      <Descriptions.Item label="累進派工金額（統計）">
        <Text>{formatCurrency(cumulativeAmount)}</Text>
      </Descriptions.Item>
      <Descriptions.Item label="剩餘金額（統計）">
        <Text
          type={
            remainingAmount > 0 && remainingAmount < 1000000
              ? 'warning'
              : undefined
          }
        >
          {formatCurrency(remainingAmount)}
        </Text>
      </Descriptions.Item>
    </Descriptions>
  );
};

// =============================================================================
// 子元件：契金資訊區塊（編輯模式 - 金額彙總）
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
    (watchedWorkAmounts.work_01_amount || 0) +
    (watchedWorkAmounts.work_02_amount || 0) +
    (watchedWorkAmounts.work_03_amount || 0) +
    (watchedWorkAmounts.work_04_amount || 0) +
    (watchedWorkAmounts.work_05_amount || 0) +
    (watchedWorkAmounts.work_06_amount || 0) +
    (watchedWorkAmounts.work_07_amount || 0);

  const cumulativeAmount = paymentData?.cumulative_amount ?? 0;
  const remainingAmount = paymentData?.remaining_amount ?? 0;

  return (
    <>
      <Divider dashed style={{ margin: '12px 0' }} />
      <ResponsiveFormRow>
        <Form.Item label="本次派工總金額（自動加總）">
          <InputNumber
            style={{ width: '100%' }}
            value={editCurrentAmount}
            disabled
            precision={0}
            formatter={(value) =>
              `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
            }
          />
        </Form.Item>
        <Form.Item label="累進派工金額（統計）">
          <InputNumber
            style={{ width: '100%' }}
            value={cumulativeAmount}
            disabled
            precision={0}
            formatter={(value) =>
              `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
            }
          />
        </Form.Item>
        <Form.Item label="剩餘金額（統計）">
          <InputNumber
            style={{ width: '100%' }}
            value={remainingAmount}
            disabled
            precision={0}
            formatter={(value) =>
              `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
            }
          />
        </Form.Item>
      </ResponsiveFormRow>
    </>
  );
};

// =============================================================================
// 主元件
// =============================================================================

export const DispatchInfoTab: React.FC<DispatchInfoTabProps> = ({
  dispatch,
  form,
  isEditing,
  agencyContacts,
  projectVendors,
  paymentData,
  watchedWorkTypes,
  watchedWorkAmounts,
  availableProjects = [],
  onProjectSelect,
  onCreateProject,
  creatingProject,
}) => {
  // 唯讀模式下的文字顯示元件（支援長文字換行）
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

  // 編輯模式下使用共用元件，唯讀模式下使用純文字
  if (!isEditing && dispatch) {
    // 唯讀模式：顯示純文字
    return (
      <div>
        {/* 第一行：派工單號 + 工程名稱 */}
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

        {/* 第二行：作業類別 + 分案名稱 + 履約期限 */}
        <div style={{ marginBottom: 16 }}>
          <ResponsiveFormRow>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>作業類別</Text>
              </div>
              <ReadOnlyField value={dispatch.work_type} />
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>分案名稱/派工備註</Text>
              </div>
              <ReadOnlyField value={dispatch.sub_case_name} />
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>履約期限</Text>
              </div>
              <ReadOnlyField value={dispatch.deadline} />
            </div>
          </ResponsiveFormRow>
        </div>

        {/* 第三行：案件承辦 + 查估單位 + 聯絡備註 */}
        <div style={{ marginBottom: 16 }}>
          <ResponsiveFormRow>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>案件承辦</Text>
              </div>
              <ReadOnlyField value={dispatch.case_handler} />
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>查估單位</Text>
              </div>
              <ReadOnlyField value={dispatch.survey_unit} />
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>聯絡備註</Text>
              </div>
              <ReadOnlyField value={dispatch.contact_note} />
            </div>
          </ResponsiveFormRow>
        </div>

        {/* 第四行：雲端資料夾 + 專案資料夾 */}
        <div style={{ marginBottom: 16 }}>
          <ResponsiveFormRow>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>雲端資料夾</Text>
              </div>
              {dispatch.cloud_folder ? (
                <a href={dispatch.cloud_folder} target="_blank" rel="noopener noreferrer">
                  <ReadOnlyField value={dispatch.cloud_folder} />
                </a>
              ) : (
                <ReadOnlyField value={undefined} />
              )}
            </div>
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ color: 'rgba(0, 0, 0, 0.88)' }}>專案資料夾</Text>
              </div>
              <ReadOnlyField value={dispatch.project_folder} />
            </div>
          </ResponsiveFormRow>
        </div>

        {/* 契金資訊 */}
        <Divider orientation="left">契金資訊</Divider>
        <PaymentReadOnlySection
          paymentData={paymentData}
          watchedWorkTypes={watchedWorkTypes}
        />

        {/* 系統資訊 */}
        <Divider />
        <Descriptions size="small" column={3}>
          <Descriptions.Item label="機關函文號">
            {(() => {
              const agencyDocs = (dispatch.linked_documents || [])
                .filter(
                  (d: DispatchDocumentLink) =>
                    detectLinkType(d.doc_number) === 'agency_incoming'
                )
                .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
                  const dateA = a.doc_date || '9999-12-31';
                  const dateB = b.doc_date || '9999-12-31';
                  return dateA.localeCompare(dateB);
                });
              return agencyDocs.length > 0
                ? agencyDocs[0]?.doc_number || '-'
                : '-';
            })()}
          </Descriptions.Item>
          <Descriptions.Item label="乾坤函文號">
            {(() => {
              const companyDocs = (dispatch.linked_documents || [])
                .filter(
                  (d: DispatchDocumentLink) =>
                    detectLinkType(d.doc_number) === 'company_outgoing'
                )
                .sort((a: DispatchDocumentLink, b: DispatchDocumentLink) => {
                  const dateA = a.doc_date || '9999-12-31';
                  const dateB = b.doc_date || '9999-12-31';
                  return dateA.localeCompare(dateB);
                });
              return companyDocs.length > 0
                ? companyDocs[0]?.doc_number || '-'
                : '-';
            })()}
          </Descriptions.Item>
          <Descriptions.Item label="建立時間">
            {dispatch.created_at
              ? dayjs(dispatch.created_at).format('YYYY-MM-DD HH:mm')
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </div>
    );
  }

  // 編輯模式：使用共用 Form 元件
  return (
    <Form form={form} layout="vertical">
      <DispatchFormFields
        form={form}
        mode="edit"
        availableProjects={availableProjects}
        agencyContacts={agencyContacts}
        projectVendors={projectVendors}
        onProjectSelect={onProjectSelect}
        onCreateProject={onCreateProject}
        creatingProject={creatingProject}
        showPaymentFields={true}
        watchedWorkTypes={watchedWorkTypes}
        showDocLinkFields={false}
        showProjectLinkFields={false}
      />

      {/* 金額彙總（編輯模式專用） */}
      <PaymentEditSummary
        watchedWorkAmounts={watchedWorkAmounts}
        paymentData={paymentData}
      />
    </Form>
  );
};

export default DispatchInfoTab;
