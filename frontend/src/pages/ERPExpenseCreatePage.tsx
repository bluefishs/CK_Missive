/**
 * 費用報銷新增頁面（導航模式，取代 Modal）
 *
 * @version 1.0.0
 */
import React from 'react';
import { Button, Card, Form, Input, Select, DatePicker, Row, Col, Typography, App } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useCreateExpense } from '../hooks';
import type { ExpenseInvoiceCreate } from '../types/erp';
import { EXPENSE_CATEGORY_OPTIONS, CURRENCY_OPTIONS } from '../types/erp';
import { ROUTES } from '../router/types';

const ERPExpenseCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createMutation = useCreateExpense();

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        date: values.date ? dayjs(values.date as string).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      } as unknown as ExpenseInvoiceCreate;
      await createMutation.mutateAsync(payload);
      message.success('報銷發票已建立');
      navigate(ROUTES.ERP_EXPENSES);
    } catch {
      message.error('建立失敗');
    }
  };

  return (
    <ResponsiveContent>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.ERP_EXPENSES)}>返回</Button>
          <Typography.Title level={4} style={{ margin: 0 }}>新增費用報銷</Typography.Title>
        </div>
        <Card>
          <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }}>
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
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="currency" label="幣別" initialValue="TWD">
                  <Select options={CURRENCY_OPTIONS} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="notes" label="備註">
              <Input.TextArea rows={2} maxLength={500} />
            </Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={createMutation.isPending}>建立</Button>
          </Form>
        </Card>
      </div>
    </ResponsiveContent>
  );
};

export default ERPExpenseCreatePage;
