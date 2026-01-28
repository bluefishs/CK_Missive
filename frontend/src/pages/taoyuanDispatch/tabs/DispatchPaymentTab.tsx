/**
 * 契金維護 Tab 元件
 *
 * 負責派工單的契金紀錄管理，包含：
 * - 各作業類別（7種）的派工日期和金額
 * - 本次派工總金額（自動計算）
 * - 累進派工金額和剩餘金額（統計值，由後端計算）
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import {
  Form,
  Row,
  Col,
  Button,
  Space,
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
import { EditOutlined, CloseOutlined, SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import type {
  DispatchOrder,
  DispatchDocumentLink,
  ContractPayment,
  ContractPaymentCreate,
} from '../../../types/api';

const { Text } = Typography;

// =============================================================================
// Props 介面定義
// =============================================================================

export interface DispatchPaymentTabProps {
  /** 派工單資料 */
  dispatch?: DispatchOrder;
  /** 契金資料 */
  paymentData?: ContractPayment | null;
  /** 是否可編輯 */
  canEdit: boolean;
  /** 是否處於編輯模式 */
  isPaymentEditing: boolean;
  /** 設定編輯模式 */
  setIsPaymentEditing: (editing: boolean) => void;
  /** 契金表單實例 */
  paymentForm: FormInstance;
  /** 儲存中狀態 */
  isSaving: boolean;
  /** 儲存契金處理函數 */
  onSavePayment: (values: ContractPaymentCreate) => void;
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
  paymentForm: FormInstance;
  onCancel: () => void;
  onSave: () => void;
  isSaving: boolean;
}

const PaymentEditForm: React.FC<PaymentEditFormProps> = ({
  paymentForm,
  onCancel,
  onSave,
  isSaving,
}) => (
  <Form form={paymentForm} layout="vertical">
    <Space style={{ marginBottom: 16 }}>
      <Button icon={<CloseOutlined />} onClick={onCancel}>
        取消
      </Button>
      <Button
        type="primary"
        icon={<SaveOutlined />}
        loading={isSaving}
        onClick={onSave}
      >
        儲存
      </Button>
    </Space>

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
  canEdit,
  isPaymentEditing,
  setIsPaymentEditing,
  paymentForm,
  isSaving,
  onSavePayment,
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

  /**
   * 處理開始編輯
   */
  const handleStartEdit = () => {
    if (paymentData) {
      paymentForm.setFieldsValue({
        work_01_date: paymentData.work_01_date
          ? dayjs(paymentData.work_01_date)
          : null,
        work_01_amount: paymentData.work_01_amount,
        work_02_date: paymentData.work_02_date
          ? dayjs(paymentData.work_02_date)
          : null,
        work_02_amount: paymentData.work_02_amount,
        work_03_date: paymentData.work_03_date
          ? dayjs(paymentData.work_03_date)
          : null,
        work_03_amount: paymentData.work_03_amount,
        work_04_date: paymentData.work_04_date
          ? dayjs(paymentData.work_04_date)
          : null,
        work_04_amount: paymentData.work_04_amount,
        work_05_date: paymentData.work_05_date
          ? dayjs(paymentData.work_05_date)
          : null,
        work_05_amount: paymentData.work_05_amount,
        work_06_date: paymentData.work_06_date
          ? dayjs(paymentData.work_06_date)
          : null,
        work_06_amount: paymentData.work_06_amount,
        work_07_date: paymentData.work_07_date
          ? dayjs(paymentData.work_07_date)
          : null,
        work_07_amount: paymentData.work_07_amount,
        cumulative_amount: paymentData.cumulative_amount,
        remaining_amount: paymentData.remaining_amount,
      });
    }
    setIsPaymentEditing(true);
  };

  /**
   * 處理儲存契金
   */
  const handleSave = async () => {
    try {
      const values = await paymentForm.validateFields();

      // 計算本次派工金額（7種作業類別金額總和）
      const currentAmount =
        (values.work_01_amount || 0) +
        (values.work_02_amount || 0) +
        (values.work_03_amount || 0) +
        (values.work_04_amount || 0) +
        (values.work_05_amount || 0) +
        (values.work_06_amount || 0) +
        (values.work_07_amount || 0);

      const data: ContractPaymentCreate = {
        dispatch_order_id: dispatch?.id || 0,
        work_01_date: values.work_01_date?.format('YYYY-MM-DD'),
        work_01_amount: values.work_01_amount,
        work_02_date: values.work_02_date?.format('YYYY-MM-DD'),
        work_02_amount: values.work_02_amount,
        work_03_date: values.work_03_date?.format('YYYY-MM-DD'),
        work_03_amount: values.work_03_amount,
        work_04_date: values.work_04_date?.format('YYYY-MM-DD'),
        work_04_amount: values.work_04_amount,
        work_05_date: values.work_05_date?.format('YYYY-MM-DD'),
        work_05_amount: values.work_05_amount,
        work_06_date: values.work_06_date?.format('YYYY-MM-DD'),
        work_06_amount: values.work_06_amount,
        work_07_date: values.work_07_date?.format('YYYY-MM-DD'),
        work_07_amount: values.work_07_amount,
        current_amount: currentAmount,
        cumulative_amount: values.cumulative_amount,
        remaining_amount: values.remaining_amount,
      };

      onSavePayment(data);
    } catch {
      // form validation error
    }
  };

  // 編輯模式
  if (isPaymentEditing) {
    return (
      <div>
        <DispatchInfoCard dispatch={dispatch} dispatchDate={dispatchDate} />
        <PaymentEditForm
          paymentForm={paymentForm}
          onCancel={() => setIsPaymentEditing(false)}
          onSave={handleSave}
          isSaving={isSaving}
        />
      </div>
    );
  }

  // 唯讀模式
  return (
    <div>
      <DispatchInfoCard dispatch={dispatch} dispatchDate={dispatchDate} />

      <Space style={{ marginBottom: 16 }}>
        {canEdit && (
          <Button type="primary" icon={<EditOutlined />} onClick={handleStartEdit}>
            {paymentData ? '編輯契金' : '新增契金'}
          </Button>
        )}
      </Space>

      {paymentData ? (
        <PaymentReadOnlyView
          paymentData={paymentData}
          dispatchDate={dispatchDate}
        />
      ) : (
        <Empty description="尚無契金紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
    </div>
  );
};

export default DispatchPaymentTab;
