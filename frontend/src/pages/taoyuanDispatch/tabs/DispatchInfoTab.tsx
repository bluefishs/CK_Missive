/**
 * 派工資訊 Tab 元件
 *
 * 顯示派工單的基本資訊，包含：
 * - 派工單號、工程名稱
 * - 作業類別、分案名稱、履約期限
 * - 案件承辦、查估單位、聯絡備註
 * - 雲端資料夾、專案資料夾
 * - 契金資訊
 * - 系統資訊（唯讀模式）
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import {
  Form,
  Input,
  Select,
  Row,
  Col,
  Descriptions,
  Divider,
  Typography,
  InputNumber,
  Alert,
} from 'antd';
import type { FormInstance } from 'antd';
import dayjs from 'dayjs';

import type {
  DispatchOrder,
  DispatchDocumentLink,
  LinkType,
  ContractPayment,
} from '../../../types/api';
import { TAOYUAN_WORK_TYPES } from '../../../types/api';
import { type ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import { type ProjectVendor } from '../../../api/projectVendorsApi';

const { Option } = Select;
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
 * - 以「乾坤」開頭的公文 → 乾坤發文 (company_outgoing)
 * - 其他 → 機關來函 (agency_incoming)
 */
const detectLinkType = (docNumber?: string): LinkType => {
  if (!docNumber) return 'agency_incoming';
  // 「乾坤」開頭表示公司發文
  if (docNumber.startsWith('乾坤')) {
    return 'company_outgoing';
  }
  // 其他都是機關來函
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
}

// =============================================================================
// 子元件：契金資訊區塊
// =============================================================================

interface PaymentSectionProps {
  isEditing: boolean;
  paymentData?: ContractPayment | null;
  watchedWorkTypes: string[];
  watchedWorkAmounts: DispatchInfoTabProps['watchedWorkAmounts'];
  calculateCurrentAmount: () => number;
}

const PaymentSection: React.FC<PaymentSectionProps> = ({
  isEditing,
  paymentData,
  watchedWorkTypes,
  watchedWorkAmounts,
  calculateCurrentAmount,
}) => {
  // 過濾有效的作業類別
  const validWorkTypes = watchedWorkTypes.filter(
    (wt) => WORK_TYPE_AMOUNT_MAPPING[wt]
  );

  // 計算編輯時的本次派工總金額
  const editCurrentAmount =
    (watchedWorkAmounts.work_01_amount || 0) +
    (watchedWorkAmounts.work_02_amount || 0) +
    (watchedWorkAmounts.work_03_amount || 0) +
    (watchedWorkAmounts.work_04_amount || 0) +
    (watchedWorkAmounts.work_05_amount || 0) +
    (watchedWorkAmounts.work_06_amount || 0) +
    (watchedWorkAmounts.work_07_amount || 0);

  // 計算本次派工金額
  const currentAmount = paymentData?.current_amount ?? calculateCurrentAmount();

  // 累進派工金額和剩餘金額從 API 取得
  const cumulativeAmount = paymentData?.cumulative_amount ?? 0;
  const remainingAmount = paymentData?.remaining_amount ?? 0;

  if (!isEditing) {
    // 唯讀模式：顯示契金摘要
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
        {/* 先顯示各作業類別金額 */}
        {workTypeItems.map(
          (item) =>
            item && (
              <Descriptions.Item key={item.key} label={item.label}>
                {item.value}
              </Descriptions.Item>
            )
        )}
        {/* 再顯示統計數據 */}
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
  }

  // 編輯模式：顯示根據作業類別的金額輸入欄位
  return (
    <>
      {/* 各作業類別金額欄位 */}
      {validWorkTypes.length > 0 ? (
        <Row gutter={16}>
          {validWorkTypes.map((wt) => {
            const mapping = WORK_TYPE_AMOUNT_MAPPING[wt];
            if (!mapping) return null;
            return (
              <Col span={8} key={wt}>
                <Form.Item
                  name={mapping.amountField}
                  label={`${mapping.label} 金額`}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    precision={0}
                    formatter={(value) =>
                      `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                    }
                    parser={(value) =>
                      Number(
                        value?.replace(/\$\s?|(,*)/g, '') || 0
                      ) as unknown as 0
                    }
                    placeholder="輸入金額"
                  />
                </Form.Item>
              </Col>
            );
          })}
        </Row>
      ) : (
        <Alert
          message="請先選擇作業類別"
          description="選擇作業類別後，將顯示對應的金額輸入欄位"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 金額彙總 */}
      <Divider dashed style={{ margin: '12px 0' }} />
      <Row gutter={16}>
        <Col span={8}>
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
        </Col>
        <Col span={8}>
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
        </Col>
        <Col span={8}>
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
        </Col>
      </Row>
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
}) => {
  // 計算本次派工金額總和
  const calculateCurrentAmount = (): number => {
    if (!paymentData) return 0;
    return (
      (paymentData.work_01_amount || 0) +
      (paymentData.work_02_amount || 0) +
      (paymentData.work_03_amount || 0) +
      (paymentData.work_04_amount || 0) +
      (paymentData.work_05_amount || 0) +
      (paymentData.work_06_amount || 0) +
      (paymentData.work_07_amount || 0)
    );
  };

  return (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      {/* 第一行：派工單號 + 工程名稱 */}
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            name="dispatch_no"
            label="派工單號"
            rules={[{ required: true, message: '請輸入派工單號' }]}
          >
            <Input placeholder="例: TY-2026-001" />
          </Form.Item>
        </Col>
        <Col span={16}>
          <Form.Item name="project_name" label="工程名稱/派工事項">
            <Input placeholder="派工事項說明" />
          </Form.Item>
        </Col>
      </Row>

      {/* 第二行：作業類別 + 分案名稱 + 履約期限 */}
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="work_type" label="作業類別">
            <Select
              mode="multiple"
              allowClear
              placeholder="選擇作業類別（可多選）"
              maxTagCount={2}
            >
              {TAOYUAN_WORK_TYPES.map((type) => (
                <Option key={type} value={type}>
                  {type}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="sub_case_name" label="分案名稱/派工備註">
            <Input />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="deadline" label="履約期限">
            <Input placeholder="例: 114/12/31" />
          </Form.Item>
        </Col>
      </Row>

      {/* 第三行：案件承辦 + 查估單位 + 聯絡備註 */}
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            name="case_handler"
            label="案件承辦"
            tooltip="從機關承辦清單選擇（來源：承攬案件機關承辦）"
          >
            <Select
              placeholder="選擇案件承辦"
              allowClear
              showSearch
              optionFilterProp="label"
            >
              {agencyContacts.map((contact) => (
                <Option
                  key={contact.id}
                  value={contact.contact_name}
                  label={contact.contact_name}
                >
                  {contact.contact_name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="survey_unit"
            label="查估單位"
            tooltip="從協力廠商清單選擇（來源：承攬案件協力廠商）"
          >
            <Select
              placeholder="選擇查估單位"
              allowClear
              showSearch
              optionFilterProp="label"
            >
              {projectVendors.map((vendor: ProjectVendor) => (
                <Option
                  key={vendor.vendor_id}
                  value={vendor.vendor_name}
                  label={vendor.vendor_name}
                >
                  {vendor.vendor_name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="contact_note" label="聯絡備註">
            <Input />
          </Form.Item>
        </Col>
      </Row>

      {/* 第四行：雲端資料夾 + 專案資料夾 */}
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="cloud_folder" label="雲端資料夾">
            <Input placeholder="Google Drive 連結" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="project_folder" label="專案資料夾">
            <Input placeholder="本地路徑" />
          </Form.Item>
        </Col>
      </Row>

      {/* 契金資訊 */}
      <Divider orientation="left">契金資訊</Divider>
      <PaymentSection
        isEditing={isEditing}
        paymentData={paymentData}
        watchedWorkTypes={watchedWorkTypes}
        watchedWorkAmounts={watchedWorkAmounts}
        calculateCurrentAmount={calculateCurrentAmount}
      />

      {/* 唯讀模式下顯示系統資訊 */}
      {!isEditing && dispatch && (
        <>
          <Divider />
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="機關函文號">
              {(() => {
                // 從 linked_documents 取得機關來函
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
                // 從 linked_documents 取得乾坤發文
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
        </>
      )}
    </Form>
  );
};

export default DispatchInfoTab;
