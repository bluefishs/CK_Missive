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
import { LEDGER_ENTRY_TYPE_LABELS, LEDGER_CATEGORY_GROUPS, LEDGER_INCOME_CATEGORIES } from '../types/erp';
import { ROUTES } from '../router/types';

const ERPLedgerCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createMutation = useCreateLedger();
  const [entryType, setEntryType] = React.useState<'income' | 'expense'>('expense');

  // 收支方向與科目必須一致 —— 選了「收款」卻記成支出，帳就反了，
  // 而金額是正的、欄位也都填了，**不會有任何錯誤訊息**。
  const categoryGroups = React.useMemo(
    () => LEDGER_CATEGORY_GROUPS.filter(g =>
      entryType === 'income' ? g.label === '收入' : g.label !== '收入'),
    [entryType],
  );

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
            onValuesChange={(changed: Record<string, unknown>) => {
              const next = changed.entry_type as 'income' | 'expense' | undefined;
              if (!next) return;
              setEntryType(next);
              const cur = form.getFieldValue('category');
              const isIncomeCat = (LEDGER_INCOME_CATEGORIES as readonly string[]).includes(cur);
              // 切換方向時清掉不屬於該方向的科目，避免殘留
              if (cur && isIncomeCat !== (next === "income")) {
                form.setFieldValue('category', undefined);
              }
            }}
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
                {/* 2026-08-16：原本只給 EXPENSE_CATEGORY_OPTIONS（**純支出科目**），
                    而帳本同時記收入 —— 於是「收款」這類收入科目在畫面上根本選不到，
                    庫裡卻有 36 筆收入分錄。改用分組清單（收入／營運／支出科目），
                    與後端 `LEDGER_CATEGORY_VALUES` 對應。 */}
                <Form.Item name="category" label="分類（會計科目）"
                  rules={[{ required: true, message: '請選擇會計科目' }]}>
                  <Select placeholder="選擇科目" allowClear showSearch
                    optionFilterProp="label"
                    options={categoryGroups} />
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
