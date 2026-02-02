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

const { Text } = Typography;

// =============================================================================
// 作業類別定義
// =============================================================================

/** 作業類別代碼與標籤對照 */
const WORK_TYPE_MAP: Record<string, string> = {
  '01': '地上物查估',
  '02': '土地協議市價查估',
  '03': '土地徵收市價查估',
  '04': '相關計畫書製作',
  '05': '測量作業',
  '06': '樁位測釘作業',
  '07': '辦理教育訓練',
};

/**
 * 從 work_type 字串解析出作業類別代碼列表
 * 例如: "01.地上物查估作業, 03.土地徵收市價查估作業" => ["01", "03"]
 */
export const parseWorkTypeCodes = (workType: string | string[] | undefined): string[] => {
  if (!workType) return [];

  // 如果是陣列（表單中的 Checkbox.Group 值）
  if (Array.isArray(workType)) {
    const result: string[] = [];
    for (const item of workType) {
      if (typeof item === 'string') {
        const match = item.match(/^(\d{2})\./);
        if (match && match[1]) {
          result.push(match[1]);
        }
      }
    }
    return result;
  }

  // 如果是字串
  const matches = workType.match(/(\d{2})\./g);
  return matches ? matches.map(m => m.replace('.', '')) : [];
};

/**
 * 檢查契金金額與作業類別的一致性
 * 返回不一致的欄位列表
 */
export const validatePaymentConsistency = (
  workTypeCodes: string[],
  amounts: Record<string, number | undefined>
): { field: string; code: string; label: string; amount: number }[] => {
  const inconsistencies: { field: string; code: string; label: string; amount: number }[] = [];

  for (let i = 1; i <= 7; i++) {
    const code = i.toString().padStart(2, '0');
    const field = `work_${code}_amount`;
    const amount = amounts[field];

    // 如果有金額但不在作業類別中
    if (amount && amount > 0 && !workTypeCodes.includes(code)) {
      inconsistencies.push({
        field,
        code,
        label: WORK_TYPE_MAP[code] || `作業${code}`,
        amount,
      });
    }
  }

  return inconsistencies;
};

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
const currencyParser = (value: string | undefined) =>
  Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0;

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
// 子元件：唯讀模式契金顯示
// =============================================================================

interface PaymentReadOnlyViewProps {
  paymentData: ContractPayment;
  dispatchDate: string | null;
}

const PaymentReadOnlyView: React.FC<PaymentReadOnlyViewProps> = ({
  paymentData,
  dispatchDate,
}) => (
  <Descriptions bordered column={2} size="small">
    <Descriptions.Item label="01.地上物查估 - 派工日期">
      {paymentData.work_01_date
        ? dayjs(paymentData.work_01_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="01.地上物查估 - 金額">
      {paymentData.work_01_amount
        ? `$${Math.round(paymentData.work_01_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="02.土地協議市價查估 - 派工日期">
      {paymentData.work_02_date
        ? dayjs(paymentData.work_02_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="02.土地協議市價查估 - 金額">
      {paymentData.work_02_amount
        ? `$${Math.round(paymentData.work_02_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="03.土地徵收市價查估 - 派工日期">
      {paymentData.work_03_date
        ? dayjs(paymentData.work_03_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="03.土地徵收市價查估 - 金額">
      {paymentData.work_03_amount
        ? `$${Math.round(paymentData.work_03_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="04.相關計畫書製作 - 派工日期">
      {paymentData.work_04_date
        ? dayjs(paymentData.work_04_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="04.相關計畫書製作 - 金額">
      {paymentData.work_04_amount
        ? `$${Math.round(paymentData.work_04_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="05.測量作業 - 派工日期">
      {paymentData.work_05_date
        ? dayjs(paymentData.work_05_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="05.測量作業 - 金額">
      {paymentData.work_05_amount
        ? `$${Math.round(paymentData.work_05_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="06.樁位測釘作業 - 派工日期">
      {paymentData.work_06_date
        ? dayjs(paymentData.work_06_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="06.樁位測釘作業 - 金額">
      {paymentData.work_06_amount
        ? `$${Math.round(paymentData.work_06_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="07.辦理教育訓練 - 派工日期">
      {paymentData.work_07_date
        ? dayjs(paymentData.work_07_date).format('YYYY-MM-DD')
        : dispatchDate
          ? dayjs(dispatchDate).format('YYYY-MM-DD')
          : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="07.辦理教育訓練 - 金額">
      {paymentData.work_07_amount
        ? `$${Math.round(paymentData.work_07_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="本次派工總金額">
      <Text strong style={{ color: '#1890ff' }}>
        {paymentData.current_amount
          ? `$${Math.round(paymentData.current_amount).toLocaleString()}`
          : '-'}
      </Text>
    </Descriptions.Item>
    <Descriptions.Item label="累進派工金額">
      {paymentData.cumulative_amount
        ? `$${Math.round(paymentData.cumulative_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
    <Descriptions.Item label="剩餘金額" span={2}>
      {paymentData.remaining_amount
        ? `$${Math.round(paymentData.remaining_amount).toLocaleString()}`
        : '-'}
    </Descriptions.Item>
  </Descriptions>
);

// =============================================================================
// 子元件：編輯模式表單
// =============================================================================

interface PaymentEditFormProps {
  form: FormInstance;
}

const PaymentEditForm: React.FC<PaymentEditFormProps> = ({ form }) => (
  <Form form={form} layout="vertical">
    <div style={{ marginBottom: 16 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>
        契金資料由頁面頂部「儲存」按鈕統一保存
      </Text>
    </div>

    <Divider orientation="left">作業類別派工金額</Divider>
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="work_01_date" label="01.地上物查估 - 派工日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_01_amount" label="01.地上物查估 - 金額">
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
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item
          name="work_02_date"
          label="02.土地協議市價查估 - 派工日期"
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_02_amount" label="02.土地協議市價查估 - 金額">
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
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item
          name="work_03_date"
          label="03.土地徵收市價查估 - 派工日期"
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_03_amount" label="03.土地徵收市價查估 - 金額">
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
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="work_04_date" label="04.相關計畫書製作 - 派工日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_04_amount" label="04.相關計畫書製作 - 金額">
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
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="work_05_date" label="05.測量作業 - 派工日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_05_amount" label="05.測量作業 - 金額">
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
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="work_06_date" label="06.樁位測釘作業 - 派工日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_06_amount" label="06.樁位測釘作業 - 金額">
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
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="work_07_date" label="07.辦理教育訓練 - 派工日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="work_07_amount" label="07.辦理教育訓練 - 金額">
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
        // 編輯模式：顯示表單（使用頁面統一的 Form）
        <PaymentEditForm form={form} />
      ) : (
        // 唯讀模式：顯示資料
        paymentData ? (
          <PaymentReadOnlyView
            paymentData={paymentData}
            dispatchDate={dispatchDate}
          />
        ) : (
          <Empty description="尚無契金紀錄，請點擊「編輯」新增" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )
      )}
    </div>
  );
};

export default DispatchPaymentTab;
