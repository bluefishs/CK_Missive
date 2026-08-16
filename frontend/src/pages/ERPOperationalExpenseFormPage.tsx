/**
 * 營運帳目 — 新增費用填報頁
 *
 * 2026-08-16 owner：「erp財務 與其子項目 其表單仍操作非導覽模式」。
 * 原本是 `ERPOperationalDetailPage` 裡的 `<Modal title="新增費用">`。
 */
import React from 'react';
import { Form, Input, Select, DatePicker, InputNumber, App } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { useCreateOperationalExpense, useOperationalAccountDetail } from '../hooks';
import { OPERATIONAL_CATEGORIES } from '../types/erp';
import type { OperationalExpenseCreate } from '../types/erp';

const ERPOperationalExpenseFormPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const accountId = Number(id);
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createExpense = useCreateOperationalExpense();
  const { data: account } = useOperationalAccountDetail(accountId);

  const back = () => navigate(`/erp/operational/${accountId}`);

  const handleSubmit = async () => {
    const v = await form.validateFields();
    const payload: OperationalExpenseCreate = {
      account_id: accountId,
      expense_date: dayjs(v.expense_date).format('YYYY-MM-DD'),
      amount: v.amount,
      description: v.description,
      category: v.category,
      notes: v.notes,
    };
    await createExpense.mutateAsync(payload);
    message.success('費用已新增');
    back();
  };

  return (
    <ErpFormPageShell
      title={account?.name ? `新增費用 — ${account.name}` : '新增費用'}
      onBack={back}
      onSubmit={handleSubmit}
      submitting={createExpense.isPending}
      backText="返回帳目"
    >
      <Form form={form} layout="vertical" initialValues={{ expense_date: dayjs() }}>
        <Form.Item name="expense_date" label="日期" rules={[{ required: true, message: '請選擇日期' }]}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="amount" label="金額" rules={[{ required: true, message: '請輸入金額' }]}>
          <InputNumber<number>
            style={{ width: '100%' }}
            min={0}
            prefix="NT$"
            formatter={v => `${v ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={v => Number((v || '').replace(/,/g, ''))}
          />
        </Form.Item>
        <Form.Item name="description" label="說明" rules={[{ required: true, message: '請填寫說明' }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="category" label="費用類別">
          <Select
            placeholder="選擇類別"
            allowClear
            options={Object.entries(OPERATIONAL_CATEGORIES).map(([value, label]) => ({ value, label }))}
          />
        </Form.Item>
        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={2} maxLength={500} showCount />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default ERPOperationalExpenseFormPage;
