/**
 * 費用報銷新增 Modal
 */
import React from 'react';
import { Modal, Form, Input, Select, DatePicker, Row, Col } from 'antd';
import type { ExpenseInvoiceCreate } from '../../types/erp';
import { EXPENSE_CATEGORY_OPTIONS, CURRENCY_OPTIONS } from '../../types/erp';
import { useCreateExpense } from '../../hooks';
import { message } from 'antd';
import dayjs from 'dayjs';

interface Props {
  open: boolean;
  onClose: () => void;
  form: ReturnType<typeof Form.useForm<ExpenseInvoiceCreate>>[0];
}

const ExpenseCreateModal: React.FC<Props> = ({ open, onClose, form }) => {
  const createMutation = useCreateExpense();

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      const payload: ExpenseInvoiceCreate = {
        ...values,
        date: values.date ? dayjs(values.date).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      };
      await createMutation.mutateAsync(payload);
      message.success('報銷發票已建立');
      onClose();
      form.resetFields();
    } catch {
      message.error('建立失敗');
    }
  };

  return (
    <Modal
      title="新增費用報銷"
      open={open}
      onOk={handleCreate}
      onCancel={() => { onClose(); form.resetFields(); }}
      confirmLoading={createMutation.isPending}
      width={560}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="inv_num" label="發票號碼" rules={[{ required: true, pattern: /^[A-Z]{2}\d{8}$/, message: '格式: AB12345678' }]}>
          <Input placeholder="AB12345678" maxLength={10} />
        </Form.Item>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="date" label="開立日期" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="amount" label="總金額 (含稅)" rules={[{ required: true }]}>
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="currency" label="幣別" initialValue="TWD">
              <Select options={CURRENCY_OPTIONS} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev.currency !== cur.currency}>
              {({ getFieldValue }) => getFieldValue('currency') && getFieldValue('currency') !== 'TWD' ? (
                <Form.Item name="original_amount" label="原幣金額" rules={[{ required: true, message: '必填' }]}>
                  <Input type="number" min={0} step={0.01} />
                </Form.Item>
              ) : null}
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev.currency !== cur.currency}>
              {({ getFieldValue }) => getFieldValue('currency') && getFieldValue('currency') !== 'TWD' ? (
                <Form.Item name="exchange_rate" label="匯率" rules={[{ required: true, message: '必填' }]}>
                  <Input type="number" min={0} step={0.000001} placeholder="例: 32.15" />
                </Form.Item>
              ) : null}
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="case_code" label="案號 (選填)">
              <Input placeholder="留空 = 一般營運支出" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="category" label="費用分類">
              <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} allowClear />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ExpenseCreateModal;
