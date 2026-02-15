/**
 * 契金維護 Tab 元件
 *
 * 負責派工單的契金紀錄管理，包含：
 * - 各作業類別（7種）的派工日期和金額
 * - 本次派工總金額（自動計算）
 * - 累進派工金額和剩餘金額（統計值，由後端計算）
 *
 * @version 2.0.0
 * @date 2026-01-30
 * @description 統一使用頁面層級 Form 和 isEditing 狀態，契金由頂部「儲存」按鈕統一保存
 */

import React from 'react';
import {
  Form,
  Row,
  Col,
  Card,
  Empty,
  Descriptions,
  Divider,
  InputNumber,
  DatePicker,
  Tag,
  Typography,
} from 'antd';
import type { FormInstance } from 'antd';
import dayjs from 'dayjs';

import type {
  DispatchOrder,
  DispatchDocumentLink,
  ContractPayment,
} from '../../../types/api';
import { parseWorkTypeCodes } from './paymentUtils';

const { Text } = Typography;

// =============================================================================
// Props 介面定義
// =============================================================================

export interface DispatchPaymentTabProps {
  /** 派工單資料 */
  dispatch?: DispatchOrder;
  /** 契金資料 */
  paymentData?: ContractPayment | null;
  /** 是否處於編輯模式（由頁面統一控制） */
  isEditing: boolean;
  /** 頁面統一的 Form 實例 */
  form: FormInstance;
}

// =============================================================================
// 輔助函數
// =============================================================================

/**
 * 格式化金額（整數，無小數）
 */
const formatCurrency = (val?: number | null): string => {
  if (val === undefined || val === null || val === 0) return '-';
  return `$${Math.round(val).toLocaleString()}`;
};

/**
 * 貨幣格式化器（用於 InputNumber）
 */
const currencyFormatter = (value: number | string | undefined) =>
  `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

/**
 * 貨幣解析器（用於 InputNumber）
 */
const currencyParser = (value: string | undefined) => {
  const cleaned = value?.replace(/\$\s?|(,*)/g, '');
  if (!cleaned || cleaned.trim() === '') return null as unknown as 0;
  return Number(cleaned) as unknown as 0;
};

// =============================================================================
// 子元件：派工基本資訊卡片
// =============================================================================

interface DispatchInfoCardProps {
  dispatch?: DispatchOrder;
  dispatchDate: string | null;
}

const DispatchInfoCard: React.FC<DispatchInfoCardProps> = ({
  dispatch,
  dispatchDate,
}) => (
  <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
    <Row gutter={16}>
      <Col span={8}>
        <Text type="secondary">派工單號：</Text>
        <Text strong>{dispatch?.dispatch_no || '-'}</Text>
      </Col>
      <Col span={8}>
        <Text type="secondary">作業類別：</Text>
        {dispatch?.work_type ? (
          <Tag color="blue">{dispatch.work_type}</Tag>
        ) : (
          '-'
        )}
      </Col>
      <Col span={8}>
        <Text type="secondary">派工日期：</Text>
        <Text strong style={{ color: '#1890ff' }}>
          {dispatchDate
            ? dayjs(dispatchDate).format('YYYY-MM-DD')
            : '(尚無機關來函)'}
        </Text>
      </Col>
    </Row>
  </Card>
);

// =============================================================================
// 作業類別欄位定義（唯讀 + 編輯模式共用）
// =============================================================================

/** 所有作業類別欄位定義 */
const ALL_WORK_TYPE_FIELDS = [
  { code: '01', label: '地上物查估' },
  { code: '02', label: '土地協議市價查估' },
  { code: '03', label: '土地徵收市價查估' },
  { code: '04', label: '相關計畫書製作' },
  { code: '05', label: '測量作業' },
  { code: '06', label: '樁位測釘作業' },
  { code: '07', label: '辦理教育訓練' },
];

// =============================================================================
// 子元件：唯讀模式契金顯示
// =============================================================================

interface PaymentReadOnlyViewProps {
  paymentData: ContractPayment;
  dispatchDate: string | null;
  /** 當前派工單的作業類別（用於過濾顯示欄位） */
  workType?: string;
}

const PaymentReadOnlyView: React.FC<PaymentReadOnlyViewProps> = ({
  paymentData,
  dispatchDate,
  workType,
}) => {
  // 解析作業類別代碼，只顯示對應的欄位
  const activeCodes = parseWorkTypeCodes(workType);
  const activeFields = activeCodes.length > 0
    ? ALL_WORK_TYPE_FIELDS.filter(f => activeCodes.includes(f.code))
    : ALL_WORK_TYPE_FIELDS;

  return (
    <Descriptions bordered column={2} size="small">
      {activeFields.map(({ code, label }) => {
        const dateKey = `work_${code}_date` as keyof ContractPayment;
        const amountKey = `work_${code}_amount` as keyof ContractPayment;
        const dateVal = paymentData[dateKey] as string | undefined;
        const amountVal = paymentData[amountKey] as number | undefined;
        return (
          <React.Fragment key={code}>
            <Descriptions.Item label={`${code}.${label} - 派工日期`}>
              {dateVal
                ? dayjs(dateVal).format('YYYY-MM-DD')
                : dispatchDate
                  ? dayjs(dispatchDate).format('YYYY-MM-DD')
                  : '-'}
            </Descriptions.Item>
            <Descriptions.Item label={`${code}.${label} - 金額`}>
              {amountVal && amountVal > 0
                ? `$${Math.round(amountVal).toLocaleString()}`
                : '-'}
            </Descriptions.Item>
          </React.Fragment>
        );
      })}
      <Descriptions.Item label="本次派工總金額">
        <Text strong style={{ color: '#1890ff' }}>
          {paymentData.current_amount && paymentData.current_amount > 0
            ? `$${Math.round(paymentData.current_amount).toLocaleString()}`
            : '-'}
        </Text>
      </Descriptions.Item>
      <Descriptions.Item label="累進派工金額">
        {paymentData.cumulative_amount && paymentData.cumulative_amount > 0
          ? `$${Math.round(paymentData.cumulative_amount).toLocaleString()}`
          : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="剩餘金額" span={2}>
        {formatCurrency(paymentData.remaining_amount)}
      </Descriptions.Item>
    </Descriptions>
  );
};

// =============================================================================
// 子元件：編輯模式表單
// =============================================================================

interface PaymentEditFormProps {
  form: FormInstance;
  /** 當前派工單的作業類別（用於過濾顯示欄位） */
  workType?: string;
}

const PaymentEditForm: React.FC<PaymentEditFormProps> = ({ form, workType }) => {
  // 解析作業類別代碼，只顯示對應的欄位
  const activeCodes = parseWorkTypeCodes(workType);
  const activeFields = activeCodes.length > 0
    ? ALL_WORK_TYPE_FIELDS.filter(f => activeCodes.includes(f.code))
    : ALL_WORK_TYPE_FIELDS; // 未選作業類別時顯示全部

  return (
    <Form form={form} layout="vertical">
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          契金資料由頁面頂部「儲存」按鈕統一保存。僅顯示作業類別對應的金額欄位。
        </Text>
      </div>

      <Divider orientation="left">作業類別派工金額</Divider>
      {activeFields.map(({ code, label }) => (
        <Row gutter={16} key={code}>
          <Col span={12}>
            <Form.Item name={`work_${code}_date`} label={`${code}.${label} - 派工日期`}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name={`work_${code}_amount`} label={`${code}.${label} - 金額`}>
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                precision={0}
                formatter={currencyFormatter}
                parser={currencyParser}
              />
            </Form.Item>
          </Col>
        </Row>
      ))}

      <Divider orientation="left">金額彙總</Divider>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="cumulative_amount" label="累進派工金額（統計）">
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={currencyFormatter}
              parser={currencyParser}
              disabled
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="remaining_amount" label="剩餘金額（統計）">
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={currencyFormatter}
              parser={currencyParser}
              disabled
            />
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );
};

// =============================================================================
// 主元件
// =============================================================================

export const DispatchPaymentTab: React.FC<DispatchPaymentTabProps> = ({
  dispatch,
  paymentData,
  isEditing,
  form,
}) => {

  /**
   * 計算派工日期（機關第一筆來函日期）
   */
  const getDispatchDate = (): string | null => {
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
  };

  const dispatchDate = getDispatchDate();

  // 根據編輯模式顯示不同內容
  return (
    <div>
      <DispatchInfoCard dispatch={dispatch} dispatchDate={dispatchDate} />

      {isEditing ? (
        // 編輯模式：顯示表單（根據作業類別過濾欄位）
        <PaymentEditForm form={form} workType={dispatch?.work_type} />
      ) : (
        // 唯讀模式：只顯示對應作業類別的欄位
        paymentData ? (
          <PaymentReadOnlyView
            paymentData={paymentData}
            dispatchDate={dispatchDate}
            workType={dispatch?.work_type}
          />
        ) : (
          <Empty description="尚無契金紀錄，請點擊「編輯」新增" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )
      )}
    </div>
  );
};

export default DispatchPaymentTab;
