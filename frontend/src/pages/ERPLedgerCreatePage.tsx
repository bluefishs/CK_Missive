/**
 * 統一帳本手動記帳頁面（導航模式，取代 Modal）
 *
 * @version 1.0.0
 */
import React from 'react';
import { Button, Card, Form, Input, Select, DatePicker, Row, Col, Typography, App } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useCreateLedger } from '../hooks';
import { LEDGER_ENTRY_TYPE_LABELS } from '../types/erp';
import { ROUTES } from '../router/types';

const ERPLedgerCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createMutation = useCreateLedger();

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        transaction_date: values.transaction_date
          ? dayjs(values.transaction_date as string).format('YYYY-MM-DD')
          : dayjs().format('YYYY-MM-DD'),
      };
      await createMutation.mutateAsync(payload as never);
      message.success('帳本記錄已建立');
      navigate(ROUTES.ERP_LEDGER);
    } catch {
      message.error('建立失敗');
    }
  };

  return (
    <ResponsiveContent>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.ERP_LEDGER)}>返回</Button>
          <Typography.Title level={4} style={{ margin: 0 }}>手動記帳</Typography.Title>
        </div>
        <Card>
          <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 500 }}
            initialValues={{ entry_type: 'expense' }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="entry_type" label="類型" rules={[{ required: true }]}>
                  <Select options={Object.entries(LEDGER_ENTRY_TYPE_LABELS).map(([value, label]) => ({ value, label }))} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="amount" label="金額" rules={[{ required: true }]}>
                  <Input type="number" min={0} step={0.01} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="category" label="分類">
                  <Input placeholder="例：交通費、材料費" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="transaction_date" label="交易日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="case_code" label="案號 (選填)">
              <Input placeholder="留空 = 一般營運支出" />
            </Form.Item>
            <Form.Item name="description" label="說明">
              <Input.TextArea rows={2} maxLength={500} />
            </Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={createMutation.isPending}>建立</Button>
          </Form>
        </Card>
      </div>
    </ResponsiveContent>
  );
};

export default ERPLedgerCreatePage;
